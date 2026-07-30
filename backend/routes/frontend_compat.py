"""
Frontend-facing chat + dashboard routes.

Reuse existing pasture/weather/grazing tools. Chat is pre-Gemini (deterministic summary).
"""

from __future__ import annotations

from typing import Any, Optional, Union

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from services import dataset_service
from services.frontend_bridge import build_chat_response, build_dashboard
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import get_pasture_data
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
            # Prefer site-level matches; skip if this only hit a broad ecoregion name
            if matched_on == "region" or str(matched_on).endswith("->region"):
                notes.append(
                    f"Skipped broad region match '{match_value}' from {label}; "
                    "prefer a town/site or GPS."
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


@router.post(
    "/chat",
    summary="Farmer chat (tool-backed, pre-Gemini)",
    response_description="Plain-language summary + reasoning from backend tools.",
)
def chat(body: ChatRequest) -> dict[str, Any]:
    """
    Farmar Ask-tab endpoint.

    Uses pasture, weather, and grazing tools to build a response shaped for the frontend.
    Does **not** call Gemini yet — replace internals later with real agent reasoning.
    """
    location, resolve_notes = _resolve_location(body)
    if not location:
        raise HTTPException(
            status_code=400,
            detail=(
                "No usable location. Choose a supported town/site in your profile "
                "(e.g. Gobabis, Molly, Neudamm, Windhoek), or provide GPS near a research site."
            ),
        )

    animal = body.livestock_type or body.animal_type
    pasture_data = get_pasture_data(location)
    weather_data = get_weather(location)
    grazing = calculate_grazing_pressure(
        location,
        herd_size=body.herd_size,
        animal_type=animal,
        pasture_data=pasture_data,
    )

    limitations = list(
        dict.fromkeys(
            resolve_notes
            + (pasture_data.get("limitations") or [])
            + (weather_data.get("limitations") or [])
            + (grazing.get("limitations") or [])
        )
    )
    if body.history:
        limitations.append(
            f"Conversation history ({len(body.history)} messages) was received but not used yet "
            "(pre-Gemini)."
        )

    advisor = {
        "pasture_data": pasture_data,
        "weather_data": weather_data,
        "grazing_assessment": grazing,
        "limitations": limitations,
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
) -> dict[str, Any]:
    """Compose weather + pasture cards for the Farmar home screen."""
    herd = _optional_int(herd_size)
    animal = livestock_type or "cattle"

    body = ChatRequest(
        message="dashboard",
        location=location,
        nearest_town=nearest_town,
        region=region,
        lat=lat,
        lon=lon,
        herd_size=herd,
        livestock_type=animal,
    )
    query, resolve_notes = _resolve_location(body)
    if not query:
        return {
            "location": location or nearest_town or region,
            "weather": {"found": False, "message": "Location required"},
            "pasture_status": {"found": False, "message": "Location required"},
            "alerts": [
                "Choose a supported town or research site in your profile before loading the dashboard."
            ],
            "recommendations": [],
            "confidence": "low",
        }

    pasture_data = get_pasture_data(query)
    weather_data = get_weather(query)
    grazing = None
    if herd is not None:
        grazing = calculate_grazing_pressure(
            query,
            herd_size=herd,
            animal_type=animal,
            pasture_data=pasture_data,
        )
    result = build_dashboard(
        location=query,
        pasture_data=pasture_data,
        weather_data=weather_data,
        grazing=grazing,
    )
    if resolve_notes:
        result["alerts"] = list(dict.fromkeys(resolve_notes + (result.get("alerts") or [])))
    return result
