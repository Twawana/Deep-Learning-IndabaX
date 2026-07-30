"""
Frontend-facing chat + dashboard routes.

Online: Oryx (Gemini) with agentic tool-calling — model chooses pasture vs weather tools.
Offline: local advisory dataset tools only (no Gemini, no Open-Meteo).
"""

from __future__ import annotations

from typing import Any, Optional, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from services import dataset_service
from services.agent_router import (
    build_intent_answer,
    detect_intents,
    is_greeting,
    needs_farm_tools,
)
from services.dataset_bridge import is_political_region
from services.frontend_bridge import build_chat_response, build_dashboard
from services.gemini_agent import AGENT_NAME, gemini_configured, is_online, run_vision_agent
from tools.grazing_tool import calculate_grazing_pressure
from tools.history_tool import compare_to_prior_year
from tools.pasture_tool import get_pasture_data
from tools.scenario_tool import run_what_if_scenario
from tools.stocking_tool import estimate_safe_stocking
from tools.tenure_tool import compare_tenure_nearby
from tools.weather_tool import get_weather

router = APIRouter(tags=["frontend"])


def _optional_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    location: Optional[str] = None
    nearest_town: Optional[str] = None
    region: Optional[str] = None
    herd_size: Optional[int] = None
    livestock_type: Optional[str] = None
    animal_type: Optional[str] = None
    farmer_name: Optional[str] = None
    farm_name: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    history: list[dict[str, Any]] = Field(default_factory=list)

    phone: Optional[str] = None
    village: Optional[str] = None
    camp_name: Optional[str] = None
    number_of_camps: Optional[int] = None
    farm_size_ha: Optional[float] = None
    land_tenure: Optional[str] = None
    water_source: Optional[str] = None
    farm_notes: Optional[str] = None
    user_tier: Optional[str] = Field(
        default="free",
        description='Subscription tier: "free" or "premium".',
    )
    is_guest: bool = False

    @field_validator("herd_size", "number_of_camps", mode="before")
    @classmethod
    def empty_to_none_int(cls, value: Any) -> Any:
        if value == "" or value is None:
            return None
        return value

    @field_validator("user_tier", mode="before")
    @classmethod
    def normalize_tier(cls, value: Any) -> str:
        if value is None or value == "":
            return "free"
        text = str(value).strip().lower()
        return "premium" if text == "premium" else "free"

    @field_validator("is_guest", mode="before")
    @classmethod
    def normalize_guest(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None or value == "":
            return False
        return str(value).strip().lower() in {"1", "true", "yes"}


def _resolve_location(body: ChatRequest) -> tuple[Optional[str], list[str]]:
    """
    Prefer nearest_town (picker) over free-text location.
    Do NOT use political/ecoregion `region` as a dataset key (aggregates many sites).
    Fall back to GPS nearest research site. Never invent Gobabis.
    """
    notes: list[str] = []

    for candidate, label in (
        (body.nearest_town, "nearest_town"),
        (body.location, "location"),
    ):
        if not candidate or not str(candidate).strip():
            continue
        text = str(candidate).strip()
        matched, matched_on, match_value = dataset_service.filter_by_query(text)
        if not matched.empty:
            # Prefer site-level matches. Allow political regions (synthetic_v2);
            # skip broad Lacuna ecoregion aggregates unless nothing else matches.
            if matched_on == "region" or str(matched_on).endswith("->region"):
                if is_political_region(str(match_value or text)):
                    notes.append(
                        f"Matched political region '{match_value}' "
                        "(synthetic rangeland sites across that region)."
                    )
                    return text, notes
                notes.append(
                    f"Skipped broad ecoregion match '{match_value}' from {label}; "
                    "prefer a town/site, political region, or GPS."
                )
                continue
            if label == "location" and body.nearest_town and _norm_diff(body.nearest_town, text):
                notes.append(
                    f"Used free-text location '{text}' (mapped via {matched_on} to {match_value}); "
                    f"nearest_town was '{body.nearest_town}'"
                )
            return text, notes

    if body.lat is not None and body.lon is not None:
        nearest = dataset_service.nearest_site_by_coordinates(float(body.lat), float(body.lon))
        if nearest:
            site, dist = nearest
            notes.append(
                f"No named place matched; used nearest research site '{site}' "
                f"({dist:.0f} km from provided GPS)."
            )
            return site, notes
        notes.append("GPS provided but no research site within 150 km.")

    return None, notes


def _norm_diff(a: str, b: str) -> bool:
    return " ".join(a.lower().split()) != " ".join(b.lower().split())


def _greeting_response(
    *,
    message: str,
    location: Optional[str],
    farmer_name: Optional[str],
    user_tier: str,
    is_guest: bool,
) -> dict[str, Any]:
    """Friendly Oryx reply for hi/hello — no tools, no decision card."""
    name = (farmer_name or "").strip()
    hello = f"Hi {name}!" if name else "Hi!"
    place = f" for {location}" if location else ""
    text = (
        f"{hello} I'm {AGENT_NAME}, your Namibian veld grazing advisor{place}.\n\n"
        "Ask me about pasture condition, rainfall, stocking, whether to move the herd, "
        "or try a what-if (e.g. “what if I add 20 cattle?”)."
    )
    tier = "free" if is_guest else (
        "premium" if str(user_tier).strip().lower() == "premium" else "free"
    )
    return {
        "response": text,
        "reasoning": f"Greeting detected for message: {message!r} — skipped advisory tools.",
        "recommendations": [],
        "tools_used": [],
        "sources": {"agent": AGENT_NAME, "mode": "greeting", "intents": ["greeting"]},
        "decision": None,
        "limitations": "",
        "confidence": "high",
        "user_tier": tier,
        "agent": AGENT_NAME,
        "mode": "greeting",
    }


@router.post(
    "/chat",
    summary="Oryx farmer chat (agentic Gemini + tools)",
    response_description="Plain-language Oryx answer; online uses agentic tool-calling.",
)
def chat(body: ChatRequest) -> dict[str, Any]:
    """
    Oryx Ask endpoint.

    Online + Gemini: Oryx decides which tools to call (pasture dataset, Open-Meteo, …).
    Offline: local advisory dataset only.
    """
    if is_greeting(body.message):
        location, _ = _resolve_location(body)
        return _greeting_response(
            message=body.message,
            location=location,
            farmer_name=body.farmer_name,
            user_tier=body.user_tier or "free",
            is_guest=bool(body.is_guest),
        )

    location, resolve_notes = _resolve_location(body)
    if not location:
        raise HTTPException(
            status_code=400,
            detail=(
                "No usable location. Choose a supported town/site in your profile "
                "(e.g. Gobabis, Molly, Neudamm, Windhoek, Khomas, Omaheke), "
                "or provide GPS near a research/synthetic site."
            ),
        )

    online = is_online()
    mode = "online" if online else "offline"
    animal = body.livestock_type or body.animal_type
    intents = detect_intents(body.message)
    use_farm_tools = needs_farm_tools(body.message, intents)

    # --- Online: Oryx agentically chooses tools ---
    if online and gemini_configured():
        oryx = run_vision_agent(
            message=body.message,
            location=location,
            user_tier=body.user_tier or "free",
            is_guest=bool(body.is_guest),
            herd_size=body.herd_size,
            livestock_type=animal,
            farmer_name=body.farmer_name,
            farm_name=body.farm_name,
            land_tenure=body.land_tenure,
            farm_size_ha=body.farm_size_ha,
            history=body.history,
            require_online=True,
        )
        if oryx:
            advisor = {
                "intents": intents,
                "mode": mode,
                "limitations": list(resolve_notes),
                "tools_used": oryx.get("tools_used") or [],
            }
            return build_chat_response(
                message=body.message,
                location=location,
                advisor=advisor,
                user_tier=body.user_tier or "free",
                is_guest=bool(body.is_guest),
                herd_size=body.herd_size,
                livestock_type=animal,
                farm_notes=body.farm_notes,
                farmer_name=body.farmer_name,
                farm_name=body.farm_name,
                land_tenure=body.land_tenure,
                farm_size_ha=body.farm_size_ha,
                vision_override=oryx,
            )

        if not use_farm_tools:
            tier = "free" if body.is_guest else (
                "premium"
                if str(body.user_tier or "free").strip().lower() == "premium"
                else "free"
            )
            return {
                "response": (
                    f"{AGENT_NAME} is online but the AI service is temporarily unavailable "
                    "(quota or connection). Please try again in a minute.\n\n"
                    "For farm advice from local data, ask about your pasture, rainfall, "
                    "or stocking — e.g. “How is the pasture?”"
                ),
                "reasoning": f"Online basic question — {AGENT_NAME} unavailable; skipped local farm tools.",
                "recommendations": [],
                "tools_used": [],
                "sources": {"agent": AGENT_NAME, "mode": "online", "intents": intents},
                "decision": None,
                "limitations": f"{AGENT_NAME} AI temporarily unavailable",
                "confidence": "low",
                "user_tier": tier,
                "agent": AGENT_NAME,
                "mode": "online",
            }

    # Offline basic questions: no Gemini, no invented farm card
    if not online and not use_farm_tools:
        tier = "free" if body.is_guest else (
            "premium"
            if str(body.user_tier or "free").strip().lower() == "premium"
            else "free"
        )
        return {
            "response": (
                f"You're offline, so {AGENT_NAME} AI is unavailable for general questions.\n\n"
                "I can still answer from the local rangeland dataset — try asking about "
                "pasture condition, stocking, or whether to move the herd."
            ),
            "reasoning": "Offline basic question — local dataset reserved for farm asks.",
            "recommendations": [],
            "tools_used": [{"name": "local_dataset", "summary": "Offline — farm data only"}],
            "sources": {"agent": "local-offline", "mode": "offline", "intents": intents},
            "decision": None,
            "limitations": f"Offline: general Q&A needs {AGENT_NAME} (online)",
            "confidence": "low",
            "user_tier": tier,
            "agent": "local-offline",
            "mode": "offline",
        }

    # --- Offline farm asks (or online farm asks after Gemini fail): local tools ---
    pasture_data = get_pasture_data(location)
    weather_data = get_weather(location)
    grazing = calculate_grazing_pressure(
        location,
        herd_size=body.herd_size,
        animal_type=animal,
        farm_size_ha=body.farm_size_ha,
        pasture_data=pasture_data,
    )

    stocking = None
    yoy = None
    tenure = None
    scenario = None
    if "scenario" in intents:
        scenario = run_what_if_scenario(
            location,
            body.message,
            current_herd_size=body.herd_size,
            livestock_type=animal,
            land_tenure=body.land_tenure,
            farm_size_ha=body.farm_size_ha,
        )
    if "stocking" in intents or ("general" in intents and "scenario" not in intents):
        stocking = estimate_safe_stocking(
            location,
            herd_size=body.herd_size,
            animal_type=animal,
            farm_size_ha=body.farm_size_ha,
            pasture_data=pasture_data,
        )
    if "yoy" in intents or "bush" in intents:
        yoy = compare_to_prior_year(location)
    if "tenure" in intents:
        tenure = compare_tenure_nearby(
            location,
            land_tenure=body.land_tenure,
            latitude=body.lat,
            longitude=body.lon,
        )

    intent_paragraphs = build_intent_answer(
        intents=intents,
        stocking=stocking,
        yoy=yoy,
        tenure=tenure,
        scenario=scenario,
    )
    if not online:
        intent_paragraphs = [
            f"You appear offline — this answer uses the local rangeland dataset only "
            f"(no live weather, no {AGENT_NAME} AI)."
        ] + list(intent_paragraphs)

    mode_notes: list[str] = []
    if online:
        mode_notes.append(
            f"Online, but {AGENT_NAME}/Gemini was unavailable — using local tools"
        )
    else:
        mode_notes.append(
            f"Offline mode: local advisory dataset only ({AGENT_NAME}/Gemini and live weather skipped)"
        )

    limitations = list(
        dict.fromkeys(
            resolve_notes
            + mode_notes
            + (pasture_data.get("limitations") or [])
            + (weather_data.get("limitations") or [])
            + (grazing.get("limitations") or [])
            + ((stocking or {}).get("limitations") or [])
            + ((yoy or {}).get("limitations") or [])
            + ((tenure or {}).get("limitations") or [])
            + ([scenario["disclaimer"]] if scenario and scenario.get("disclaimer") else [])
        )
    )

    advisor = {
        "pasture_data": pasture_data,
        "weather_data": weather_data,
        "grazing_assessment": grazing,
        "stocking": stocking,
        "year_over_year": yoy,
        "tenure_peers": tenure,
        "scenario": scenario,
        "intents": intents,
        "intent_paragraphs": intent_paragraphs,
        "limitations": limitations,
        "mode": mode,
        "confidence": grazing.get("confidence")
        or pasture_data.get("confidence")
        or weather_data.get("confidence")
        or "low",
    }

    return build_chat_response(
        message=body.message,
        location=location,
        advisor=advisor,
        user_tier=body.user_tier or "free",
        is_guest=bool(body.is_guest),
        herd_size=body.herd_size,
        livestock_type=animal,
        farm_notes=body.farm_notes,
        farmer_name=body.farmer_name,
        farm_name=body.farm_name,
        land_tenure=body.land_tenure,
        farm_size_ha=body.farm_size_ha,
        vision_override=None,
    )


@router.get(
    "/dashboard",
    summary="Home dashboard aggregate",
)
def dashboard(
    location: Optional[str] = Query(default=None),
    nearest_town: Optional[str] = Query(default=None),
    region: Optional[str] = Query(default=None),
    lat: Optional[float] = Query(default=None),
    lon: Optional[float] = Query(default=None),
    herd_size: Optional[Union[int, str]] = Query(default=None),
    livestock_type: Optional[str] = Query(default=None),
    land_tenure: Optional[str] = Query(default=None),
    farm_size_ha: Optional[Union[float, str]] = Query(default=None),
) -> dict[str, Any]:
    """Compose weather + pasture + decision-support cards for the Farmar home screen."""
    herd = _optional_int(herd_size)
    animal = livestock_type or "cattle"
    farm_ha = None
    if farm_size_ha not in (None, ""):
        try:
            farm_ha = float(farm_size_ha)
        except (TypeError, ValueError):
            farm_ha = None

    body = ChatRequest(
        message="dashboard",
        location=location,
        nearest_town=nearest_town,
        region=region,
        lat=lat,
        lon=lon,
        herd_size=herd,
        livestock_type=animal,
        land_tenure=land_tenure,
        farm_size_ha=farm_ha,
    )
    query, resolve_notes = _resolve_location(body)
    if not query:
        return {
            "location": location or nearest_town or region,
            "weather": {"found": False, "message": "Location required"},
            "pasture_status": {"found": False, "message": "Location required"},
            "decision": None,
            "alerts": [
                "Choose a supported town or research site in your profile before loading the dashboard."
            ],
            "recommendations": [],
            "confidence": "low",
        }

    pasture_data = get_pasture_data(query)
    weather_data = get_weather(query)
    # Always assess grazing (soft pasture-only signals when herd is missing)
    grazing = calculate_grazing_pressure(
        query,
        herd_size=herd,
        animal_type=animal,
        farm_size_ha=farm_ha,
        pasture_data=pasture_data,
    )
    result = build_dashboard(
        location=query,
        pasture_data=pasture_data,
        weather_data=weather_data,
        grazing=grazing,
        land_tenure=land_tenure,
        herd_size=herd,
    )
    if resolve_notes:
        result["alerts"] = list(dict.fromkeys(resolve_notes + (result.get("alerts") or [])))
    return result
