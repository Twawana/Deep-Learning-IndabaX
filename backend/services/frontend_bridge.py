"""
Build farmer-facing chat / dashboard payloads from existing tool outputs.

Vision (Gemini) may supply farmer-facing prose; otherwise deterministic summaries
from measured data + grazing assessment. Respects FREE vs PREMIUM response depth.
"""

from __future__ import annotations

from typing import Any, Optional

FREE_UPGRADE_CTA = (
    "Upgrade to Premium to get detailed grazing insights, rainfall analysis, "
    "and stocking recommendations."
)

GUEST_LOGIN_CTA = (
    "Log in on Profile for unlimited free answers, or upgrade to Premium for "
    "detailed grazing insights."
)

_MARKETING_LINES = (
    FREE_UPGRADE_CTA,
    GUEST_LOGIN_CTA,
    "Upgrade to Premium to get detailed grazing insights, rainfall analysis, and stocking recommendations.",
    "Log in on Profile for unlimited free answers, or upgrade to Premium for detailed grazing insights.",
    "One Premium upgrade nudge",
)


def strip_marketing_copy(text: str) -> str:
    """Remove login/Premium marketing lines from farmer-facing answers."""
    if not text:
        return text
    cleaned = text
    for phrase in _MARKETING_LINES:
        cleaned = cleaned.replace(phrase, "")
    # Drop leftover empty lines
    lines = [ln.rstrip() for ln in cleaned.splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    return "\n".join(lines).strip()

B2B_KEYWORDS = (
    "ngo",
    "government",
    "ministry",
    "extension",
    "official",
    "council",
    "municipality",
    "cooperative",
    "co-op",
    "regional",
    "district",
)


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


def _normalize_tier(tier: Optional[str]) -> str:
    value = (tier or "free").strip().lower()
    return "premium" if value == "premium" else "free"


def _is_b2b_context(
    message: str,
    *,
    farm_notes: Optional[str] = None,
    farmer_name: Optional[str] = None,
    farm_name: Optional[str] = None,
) -> bool:
    blob = " ".join(
        part for part in (message, farm_notes, farmer_name, farm_name) if part
    ).lower()
    return any(keyword in blob for keyword in B2B_KEYWORDS)


def _risk_phrase(risk: Optional[str]) -> str:
    mapping = {
        "high": "high",
        "medium": "moderate",
        "low": "low",
        "unknown": "uncertain",
    }
    return mapping.get((risk or "unknown").lower(), "uncertain")


def _tool_names(tools: Any) -> list[str]:
    names: list[str] = []
    for item in tools or []:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
        elif isinstance(item, str):
            names.append(item)
    return names


def build_data_source(
    *,
    mode: str,
    vision_model: Optional[str] = None,
    vision_text: Optional[str] = None,
    vision_tools: Optional[list[Any]] = None,
    pasture_data: Optional[dict[str, Any]] = None,
    weather_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Farmer-facing provenance: local dataset vs online AI / live weather.

    kind: local | online | mixed
    """
    pasture_data = pasture_data or {}
    weather_data = weather_data or {}
    names = _tool_names(vision_tools)
    used: list[str] = []

    used_ai = bool(vision_model or vision_text)
    used_pasture = (
        "get_pasture_data" in names
        or "local_dataset" in names
        or bool(pasture_data.get("found"))
        or any(
            n in names
            for n in (
                "calculate_grazing_pressure",
                "estimate_safe_stocking",
                "compare_to_prior_year",
                "compare_tenure_nearby",
                "run_what_if_scenario",
                "compare_locations",
            )
        )
    )
    weather_skipped = bool(weather_data.get("skipped"))
    used_weather = (
        "get_weather" in names
        or (
            bool(weather_data.get("found"))
            and not weather_skipped
            and mode == "online"
        )
    )

    if used_ai:
        used.append("vision_ai")
    if used_pasture:
        used.append("local_dataset")
    if used_weather:
        used.append("live_weather")

    if mode == "offline" or (not used_ai and not used_weather):
        kind = "local"
        label = "Local data"
        if used_pasture:
            detail = "Using the local rangeland dataset (no live weather / online AI)."
        else:
            detail = "Answered without live network data."
    elif used_ai and used_pasture and not used_weather:
        kind = "mixed"
        label = "Online AI + local data"
        detail = "Vision AI online, pasture numbers from the local dataset."
    elif used_ai and used_weather and used_pasture:
        kind = "mixed"
        label = "Online + local data"
        detail = "Vision AI + local pasture dataset + live Open-Meteo weather."
    elif used_ai and used_weather:
        kind = "online"
        label = "Online data"
        detail = "Vision AI + live Open-Meteo weather."
    elif used_weather and used_pasture:
        kind = "mixed"
        label = "Online weather + local data"
        detail = "Local pasture dataset + live Open-Meteo weather."
    elif used_weather:
        kind = "online"
        label = "Online data"
        detail = "Live Open-Meteo weather."
    elif used_ai:
        kind = "online"
        label = "Online data"
        detail = "Vision AI (online) — no dataset or weather tools called."
    else:
        kind = "online"
        label = "Online data"
        detail = "Online session."

    return {
        "kind": kind,
        "mode": mode,
        "label": label,
        "detail": detail,
        "used": used,
    }


def _rainfall_context_words(recent_mm: Any, recent_days: Any) -> str:
    if recent_mm is None:
        return "rainfall over recent days could not be confirmed from weather data"
    try:
        amount = float(recent_mm)
    except (TypeError, ValueError):
        return "rainfall over recent days could not be confirmed from weather data"
    days = recent_days or "recent"
    if amount <= 2:
        level = "very little rain"
    elif amount <= 10:
        level = "low rainfall"
    elif amount <= 30:
        level = "moderate rainfall"
    else:
        level = "useful rainfall"
    return f"{level} over the past {days} days"


def pasture_status_for_ui(pasture_data: dict[str, Any]) -> dict[str, Any]:
    """Flatten backend pasture tool JSON into dashboard/pasture card fields."""
    if not pasture_data.get("found"):
        return {
            "found": False,
            "message": pasture_data.get("message") or "Region not found",
            "location": pasture_data.get("location"),
        }

    metrics = pasture_data.get("pasture") or {}
    return {
        "found": True,
        "location": pasture_data.get("location"),
        "sites": pasture_data.get("sites") or [],
        "matched_on": pasture_data.get("matched_on"),
        "match_value": pasture_data.get("match_value"),
        "observation_date": pasture_data.get("observation_date"),
        "vegetation_cover": metrics.get("vegetation_cover"),
        "bush_encroachment": metrics.get("bush_encroachment"),
        "biomass": metrics.get("biomass"),
        "grass_biomass": metrics.get("biomass"),
        "cover_perennial_grass_pct": metrics.get("cover_perennial_grass_pct"),
        "cover_annual_grass_pct": metrics.get("cover_annual_grass_pct"),
        "cover_bare_ground_pct": metrics.get("cover_bare_ground_pct"),
        "grazing_pressure": metrics.get("grazing_pressure_recorded")
        or metrics.get("grazing_pressure_label"),
        "carrying_capacity": metrics.get("carrying_capacity_ha_per_lsu"),
        "ndvi": metrics.get("ndvi"),
        "livestock_density_lsu_per_ha": metrics.get("livestock_density_lsu_per_ha"),
        "dataset_source": metrics.get("dataset_source"),
        "condition": None,
        "soil_quality": None,
        "grass_type": None,
        "confidence": pasture_data.get("confidence"),
        "limitations": pasture_data.get("limitations") or [],
        "latitude": pasture_data.get("latitude"),
        "longitude": pasture_data.get("longitude"),
        "dominant_herbaceous": pasture_data.get("dominant_herbaceous"),
        "dominant_woody": pasture_data.get("dominant_woody"),
    }


def weather_status_for_ui(weather_data: dict[str, Any]) -> dict[str, Any]:
    """Flatten backend weather tool JSON into dashboard/weather card fields."""
    if not weather_data.get("found"):
        return {
            "found": False,
            "message": weather_data.get("message") or "Region not found",
            "location": weather_data.get("location"),
        }

    recent = weather_data.get("recent_rainfall") or {}
    forecast = weather_data.get("forecast") or {}
    forecast_daily = forecast.get("daily") or []
    today = forecast_daily[0] if forecast_daily else {}

    temp_max = today.get("temperature_max_c")
    temp_min = today.get("temperature_min_c")
    temperature = None
    if temp_max is not None and temp_min is not None:
        temperature = f"{temp_min:.0f}-{temp_max:.0f}C"
    elif temp_max is not None:
        temperature = f"{temp_max:.0f}C"

    precip_today = today.get("precipitation_mm")
    rainfall = None if precip_today is None else f"{precip_today} mm (today/next)"

    recent_total = recent.get("total_precipitation_mm")
    recent_days = recent.get("days")
    forecast_total = forecast.get("total_precipitation_mm")
    recent_label = (
        None
        if recent_total is None
        else f"{recent_total} mm (last {recent_days or '?'} days)"
    )

    return {
        "found": True,
        "location": weather_data.get("location"),
        "site": weather_data.get("site"),
        "region": weather_data.get("region"),
        "latitude": weather_data.get("latitude"),
        "longitude": weather_data.get("longitude"),
        "temperature": temperature,
        "rainfall": rainfall,
        "humidity": None,
        "recent_rainfall_mm": recent_total,
        "rainfall_recent": recent_label,
        "rainfall_last_7_days": recent_label,
        "forecast_total_mm": forecast_total,
        "drought_indicator": None,
        "source": weather_data.get("source"),
        "forecast": forecast_daily,
        "recent_rainfall": recent,
        "confidence": weather_data.get("confidence"),
        "limitations": weather_data.get("limitations") or [],
    }


def build_dashboard(
    *,
    location: str,
    pasture_data: dict[str, Any],
    weather_data: dict[str, Any],
    grazing: Optional[dict[str, Any]] = None,
    land_tenure: Optional[str] = None,
    herd_size: Optional[int] = None,
) -> dict[str, Any]:
    from services.decision_service import build_decision

    pasture_status = pasture_status_for_ui(pasture_data)
    weather_status = weather_status_for_ui(weather_data)
    grazing = grazing or {}
    alerts: list[str] = []
    recommendations: list[str] = []

    decision = build_decision(
        location=location,
        pasture_data=pasture_data,
        weather_data=weather_data,
        grazing=grazing,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )

    for item in pasture_status.get("limitations") or []:
        if "old" in item.lower() or "dated" in item.lower():
            alerts.append(item)
    for item in weather_status.get("limitations") or []:
        if "fail" in item.lower() or "unavailable" in item.lower():
            alerts.append(item)

    risk = grazing.get("grazing_risk")
    if risk in {"high", "medium"}:
        alerts.append(f"Grazing risk signal: {risk} - {grazing.get('reason')}")
    recommendations.extend((grazing.get("signals") or [])[:3])
    if decision.get("recommended_action"):
        recommendations.insert(0, decision["recommended_action"])
    if grazing.get("confidence") == "low":
        recommendations.append(
            "Treat advice as provisional - confidence is low for this assessment."
        )
    if pasture_status.get("carrying_capacity") is None:
        recommendations.append(
            "Carrying capacity is not available for this location; stocking advice stays qualitative."
        )

    if not pasture_data.get("found"):
        alerts.append(pasture_data.get("message") or "Pasture location not found in dataset")
    if not weather_data.get("found"):
        alerts.append(weather_data.get("message") or "Weather location not resolved")

    return {
        "location": location,
        "weather": weather_status,
        "pasture_status": pasture_status,
        "grazing_assessment": grazing,
        "decision": decision,
        "alerts": list(dict.fromkeys(alerts)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "confidence": pasture_data.get("confidence") or weather_data.get("confidence") or "low",
    }


def build_chat_response(
    *,
    message: str,
    location: str,
    advisor: dict[str, Any],
    user_tier: str = "free",
    is_guest: bool = False,
    herd_size: Optional[int] = None,
    livestock_type: Optional[str] = None,
    farm_notes: Optional[str] = None,
    farmer_name: Optional[str] = None,
    farm_name: Optional[str] = None,
    land_tenure: Optional[str] = None,
    farm_size_ha: Optional[float] = None,
    vision_override: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Shape POST /chat response expected by the Farmar frontend (Vision / tool-backed)."""
    from services.decision_service import (
        advisor_prose_from_decision,
        build_decision,
        question_aware_local_reply,
    )

    # Guests never get premium depth, even if a bad client sends premium.
    tier = "free" if is_guest else _normalize_tier(user_tier)
    pasture_data = advisor.get("pasture_data") or {}
    weather_data = advisor.get("weather_data") or {}
    grazing = advisor.get("grazing_assessment") or {}
    stocking = advisor.get("stocking") or {}
    yoy = advisor.get("year_over_year") or {}
    tenure = advisor.get("tenure_peers") or {}
    scenario = advisor.get("scenario") or {}
    intent_paragraphs = advisor.get("intent_paragraphs") or []
    intents = advisor.get("intents") or []
    pasture_ui = pasture_status_for_ui(pasture_data)
    weather_ui = weather_status_for_ui(weather_data)
    b2b = _is_b2b_context(
        message,
        farm_notes=farm_notes,
        farmer_name=farmer_name,
        farm_name=farm_name,
    )

    decision = build_decision(
        location=location,
        pasture_data=pasture_data,
        weather_data=weather_data,
        grazing=grazing,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )
    # For what-if questions, surface the scenario decision as the primary card
    if scenario.get("found") and scenario.get("scenario"):
        decision = dict(scenario["scenario"])
        if scenario.get("what_changed"):
            decision["what_changed"] = scenario["what_changed"]
        if scenario.get("parsed"):
            decision["parsed_assumptions"] = scenario["parsed"].get("assumptions")

    vision_text = (vision_override or {}).get("response")
    vision_reasoning = (vision_override or {}).get("reasoning")
    vision_model = (vision_override or {}).get("model")
    vision_tools = (vision_override or {}).get("tools_used") or []
    data_mode = (vision_override or {}).get("mode") or advisor.get("mode") or "online"
    agent_label = (
        (vision_override or {}).get("agent")
        or ("Vision" if vision_text else ("local-offline" if data_mode == "offline" else "tools"))
    )

    if vision_text:
        prose = vision_text
        # Gemini answers are chat replies — skip the Monitor Closely decision card.
        decision = None
        recommendations = []
        explainer = {}
    elif scenario.get("found") and scenario.get("farmer_summary"):
        prose = scenario["farmer_summary"]
        explainer = decision.get("explainer") or {}
        recommendations = list(
            dict.fromkeys(
                [decision.get("recommended_action")]
                + list(explainer.get("monitor_next") or [])
                + (grazing.get("signals") or [])[:2]
            )
        )
        recommendations = [r for r in recommendations if r]
    else:
        prose = question_aware_local_reply(
            message=message,
            location=location,
            decision=decision or {},
            pasture_data=pasture_data,
            weather_data=weather_data,
            grazing=grazing,
            stocking=stocking,
            year_over_year=yoy,
            herd_size=herd_size,
        )
        if intent_paragraphs:
            prose = prose + "\n\n" + "\n\n".join(intent_paragraphs)
        explainer = decision.get("explainer") or {}
        recommendations = list(
            dict.fromkeys(
                [decision.get("recommended_action")]
                + list(explainer.get("monitor_next") or [])
                + (grazing.get("signals") or [])[:2]
            )
        )
        recommendations = [r for r in recommendations if r]
        # Prefer chat prose over the stock decision card for varied questions
        msg_l = (message or "").lower()
        if any(
            k in msg_l
            for k in (
                "how long",
                "rainfall",
                "rain",
                "stock",
                "overgraz",
                "bush",
                "carrying",
            )
        ):
            decision = None
            recommendations = []
            explainer = {}

    if b2b and not vision_text:
        prose = (
            f"Regional / extension view for {location}:\n\n" + prose + "\n\n"
            "At regional level, prioritize camps with weaker cover and coordinate "
            "rotation advice across neighbouring farms where possible."
        )

    if tier == "free":
        # Short free answers shaped to the question — never the identical Monitor Closely card.
        if vision_text:
            short = strip_marketing_copy(vision_text)
        elif scenario.get("found") and scenario.get("farmer_summary"):
            short = strip_marketing_copy(scenario["farmer_summary"])
        else:
            short = question_aware_local_reply(
                message=message,
                location=location,
                decision=decision or {},
                pasture_data=pasture_data,
                weather_data=weather_data,
                grazing=grazing,
                stocking=stocking,
                year_over_year=yoy,
                herd_size=herd_size,
            )
            # Keep any bush/YoY intent facts that answer the question directly
            if intent_paragraphs and any(
                k in (message or "").lower() for k in ("bush", "encroach", "last year", "worse")
            ):
                # Prefer question_aware; only append unique YoY lines not already present
                for para in intent_paragraphs:
                    if para and para not in short:
                        short = f"{short}\n\n{para}"
        short = strip_marketing_copy(short)
        tools_used = []
        if vision_model:
            tools_used.append(
                {"name": "Vision", "summary": f"Gemini agentic ({vision_model})"}
            )
        for t in vision_tools:
            if isinstance(t, dict) and t.get("name"):
                tools_used.append(t)
        if not vision_text and pasture_data:
            tools_used.append(
                {
                    "name": "get_pasture_data",
                    "summary": f"Local pasture lookup for {location}",
                }
            )
        if not vision_text and weather_data and data_mode == "online":
            tools_used.append(
                {"name": "get_weather", "summary": f"Weather context for {location}"}
            )
        elif data_mode == "offline" and not vision_text:
            tools_used.append(
                {
                    "name": "local_dataset",
                    "summary": "Offline — local advisory dataset only (no live weather)",
                }
            )
        if scenario.get("found"):
            tools_used.append(
                {"name": "run_what_if_scenario", "summary": "Compared current vs what-if"}
            )
        if stocking.get("found") and "scenario" not in intents:
            tools_used.append(
                {"name": "estimate_safe_stocking", "summary": stocking.get("status")}
            )
        # Free tier: chat prose only — do not attach the same Monitor Closely card every time.
        limitations: list[str] = []
        if data_mode == "offline":
            limitations.append(
                "Offline: local dataset only — live AI weather may be unavailable."
            )
        if not vision_model and data_mode == "online":
            limitations.append(
                "Vision AI temporarily unavailable — answer uses local pasture data and weather tools."
            )
        reasoning = vision_reasoning or (
            "Offline local-dataset guidance."
            if data_mode == "offline"
            else "Question-aware local guidance from pasture, weather, and grazing tools."
        )
        data_source = build_data_source(
            mode=data_mode,
            vision_model=vision_model,
            vision_text=vision_text,
            vision_tools=vision_tools,
            pasture_data=pasture_data,
            weather_data=weather_data,
        )
        sources = {
            "scenario": scenario or None,
            "intents": intents,
            "agent": agent_label,
            "mode": data_mode,
            "data_source": data_source,
        } if scenario.get("found") or vision_text or data_mode == "offline" else {
            "mode": data_mode,
            "data_source": data_source,
            "agent": agent_label,
        }
        return {
            "response": short,
            "reasoning": reasoning,
            "recommendations": [],
            "tools_used": tools_used,
            "sources": sources,
            "decision": None,
            "limitations": "; ".join(limitations),
            "confidence": advisor.get("confidence") or "low",
            "user_tier": tier,
            "agent": agent_label,
            "mode": data_mode,
            "data_source": data_source,
            "assistant": {
                "name": agent_label if agent_label != "tools" else "Vision",
                "powered_by": "gemini" if vision_model else "local",
                "mode": "agentic_tool_calling" if vision_model else "local_tools",
                "data_source": data_source,
            },
        }

    # Premium: natural prose + optional decision card (not for bush/status Qs)
    if not vision_text:
        if herd_size is None:
            prose += (
                "\n\nHerd size was not set in your profile — advice is stronger once you add it."
            )
        if farm_size_ha is None and pasture_ui.get("carrying_capacity") is not None:
            prose += (
                "\n\nAdd farm/camp size (hectares) in Profile to turn carrying capacity "
                "into a safe head-count for your herd."
            )

    tools_used = []
    if vision_model:
        tools_used.append(
            {"name": "Vision", "summary": f"Gemini agentic ({vision_model})"}
        )
    for t in vision_tools:
        if isinstance(t, dict) and t.get("name"):
            tools_used.append(t)
    if not vision_text and pasture_data:
        tools_used.append(
            {"name": "get_pasture_data", "summary": f"Local pasture lookup for {location}"}
        )
        if grazing:
            tools_used.append(
                {
                    "name": "calculate_grazing_pressure",
                    "summary": f"Grazing assessment risk={grazing.get('grazing_risk')}",
                }
            )
    if not vision_text and weather_data and data_mode == "online" and pasture_data:
        tools_used.append(
            {
                "name": "get_weather",
                "summary": f"Open-Meteo rainfall/forecast for {location}",
            }
        )
    elif data_mode == "offline" and not vision_text:
        tools_used.append(
            {
                "name": "local_dataset",
                "summary": "Offline — local advisory dataset only (no live weather)",
            }
        )
    if scenario.get("found"):
        tools_used.append(
            {
                "name": "run_what_if_scenario",
                "summary": f"what-if → {scenario.get('scenario', {}).get('headline')}",
            }
        )
    if stocking.get("found"):
        tools_used.append(
            {
                "name": "estimate_safe_stocking",
                "summary": f"status={stocking.get('status')} ha/LSU={stocking.get('carrying_capacity_ha_per_lsu')}",
            }
        )
    if yoy.get("found"):
        tools_used.append({"name": "compare_to_prior_year", "summary": "Year-over-year pasture"})
    if tenure.get("found"):
        tools_used.append({"name": "compare_tenure_nearby", "summary": "Tenure peer compare"})

    sources = {
        "pasture": pasture_ui if pasture_data else None,
        "weather": weather_ui if weather_data else None,
        "grazing_assessment": grazing or None,
        "stocking": stocking or None,
        "year_over_year": yoy or None,
        "tenure_peers": tenure or None,
        "scenario": scenario or None,
        "decision": decision,
        "intents": intents,
        "agent": agent_label,
        "mode": data_mode,
    }
    capacity_note = (
        "Carrying capacity (ha/LSU) used from synthetic / nearby sites."
        if pasture_ui.get("carrying_capacity") is not None
        else "Carrying capacity (ha/LSU) not available for this location."
    )
    limitations = list(
        dict.fromkeys(
            (advisor.get("limitations") or [])
            + (
                [
                    capacity_note,
                    "Always verify conditions on the ground before moving animals.",
                ]
                if not vision_text
                else []
            )
        )
    )
    if decision:
        reasoning = vision_reasoning or (
            f"Question: {message}\n"
            f"Mode: {data_mode}\n"
            f"Intents: {', '.join(intents) if intents else 'general'}\n"
            f"Location: {location}\n"
            f"Action: {decision.get('action_priority')} ({decision.get('headline')})\n"
            f"Herd size: {herd_size if herd_size is not None else 'not provided'}\n"
            f"Farm size ha: {farm_size_ha if farm_size_ha is not None else 'not provided'}\n"
            f"Land tenure: {land_tenure or 'unknown'}\n"
            f"Pasture found={pasture_data.get('found')}, confidence={pasture_data.get('confidence')}\n"
            f"Weather found={weather_data.get('found')}, confidence={weather_data.get('confidence')}\n"
            f"Grazing risk={grazing.get('grazing_risk')}, confidence={grazing.get('confidence')}\n"
            f"Capacity ha/LSU={pasture_ui.get('carrying_capacity')}\n"
            f"B2B context={'yes' if b2b else 'no'}"
        )
    else:
        reasoning = vision_reasoning or f"Vision reply for: {message}"

    data_source = build_data_source(
        mode=data_mode,
        vision_model=vision_model,
        vision_text=vision_text,
        vision_tools=vision_tools,
        pasture_data=pasture_data,
        weather_data=weather_data,
    )
    if isinstance(sources, dict):
        sources = {**sources, "data_source": data_source}

    return {
        "response": strip_marketing_copy(prose),
        "reasoning": reasoning,
        "recommendations": recommendations[:5] if recommendations else [],
        "tools_used": tools_used,
        "sources": sources,
        "decision": decision,
        "limitations": "; ".join(limitations) if isinstance(limitations, list) else str(limitations),
        "confidence": advisor.get("confidence") or ("medium" if vision_text else "low"),
        "user_tier": tier,
        "agent": agent_label,
        "mode": data_mode,
        "data_source": data_source,
        "assistant": {
            "name": agent_label if agent_label not in {"tools", "local-offline"} else "Vision",
            "powered_by": "gemini" if vision_model else "local",
            "mode": "agentic_tool_calling" if vision_model else "local_tools",
            "data_source": data_source,
        },
    }
