"""
Build farmer-facing chat / dashboard payloads from existing tool outputs.

No Gemini yet — deterministic summaries from measured data + grazing assessment.
Respects FREE vs PREMIUM response depth.
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
        "grazing_pressure": metrics.get("grazing_pressure_recorded"),
        "carrying_capacity": None,
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
            "Treat advice as provisional - carrying capacity is not in the dataset."
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
) -> dict[str, Any]:
    """Shape POST /chat response expected by the Farmar frontend (pre-Gemini)."""
    from services.decision_service import advisor_prose_from_decision, build_decision

    # Guests never get premium depth, even if a bad client sends premium.
    tier = "free" if is_guest else _normalize_tier(user_tier)
    pasture_data = advisor.get("pasture_data") or {}
    weather_data = advisor.get("weather_data") or {}
    grazing = advisor.get("grazing_assessment") or {}
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

    prose = advisor_prose_from_decision(
        decision=decision, location=location, message=message
    )
    explainer = decision.get("explainer") or {}
    recommendations = list(
        dict.fromkeys(
            [decision.get("recommended_action")]
            + list(explainer.get("monitor_next") or [])
            + (grazing.get("signals") or [])[:2]
        )
    )
    recommendations = [r for r in recommendations if r]

    if b2b:
        prose = (
            f"Regional / extension view for {location}:\n\n" + prose + "\n\n"
            "At regional level, prioritize camps with weaker cover and coordinate "
            "rotation advice across neighbouring farms where possible."
        )

    if tier == "free":
        cta = GUEST_LOGIN_CTA if is_guest else FREE_UPGRADE_CTA
        short = (
            f"{decision.get('headline')}: {decision.get('recommended_action')}\n\n"
            f"{(decision.get('grazing_conditions') or {}).get('combined_assessment', '')}\n\n"
            f"{cta}"
        )
        tools_used = [
            {"name": "get_pasture_data", "summary": f"Pasture lookup for {location}"},
            {"name": "get_weather", "summary": f"Weather context for {location}"},
        ]
        sources = None
        # Free still gets a compact decision (action + why checks), not a black box.
        decision_out = {
            "action_priority": decision.get("action_priority"),
            "headline": decision.get("headline"),
            "recommended_action": decision.get("recommended_action"),
            "explainer": {
                "what": explainer.get("what"),
                "why": (explainer.get("why") or [])[:2],
                "checks": explainer.get("checks"),
            },
            "confidence": decision.get("confidence"),
        }
        limitations = [
            "Free plan: short guidance only.",
            "Detailed metrics, timeline, and full evidence are available on Premium.",
        ]
        reasoning = (
            "Short free-tier guidance from pasture and weather signals, "
            "without detailed technical numbers."
        )
        return {
            "response": short,
            "reasoning": reasoning,
            "recommendations": [],
            "tools_used": tools_used,
            "sources": sources,
            "decision": decision_out,
            "limitations": "; ".join(limitations),
            "confidence": advisor.get("confidence") or "low",
            "user_tier": tier,
        }

    # Premium: natural prose + full decision + evidence
    if herd_size is None:
        prose += (
            "\n\nHerd size was not set in your profile — advice is stronger once you add it."
        )

    tools_used = [
        {"name": "get_pasture_data", "summary": f"Pasture lookup for {location}"},
        {"name": "get_weather", "summary": f"Open-Meteo rainfall/forecast for {location}"},
        {
            "name": "calculate_grazing_pressure",
            "summary": f"Grazing assessment risk={grazing.get('grazing_risk')}",
        },
    ]
    sources = {
        "pasture": pasture_ui,
        "weather": weather_ui,
        "grazing_assessment": grazing,
        "decision": decision,
    }
    limitations = list(
        dict.fromkeys(
            (advisor.get("limitations") or [])
            + [
                "Carrying capacity is not available in the dataset.",
                "Always verify conditions on the ground before moving animals.",
            ]
        )
    )
    reasoning = (
        f"Question: {message}\n"
        f"Location: {location}\n"
        f"Action: {decision.get('action_priority')} ({decision.get('headline')})\n"
        f"Herd size: {herd_size if herd_size is not None else 'not provided'}\n"
        f"Land tenure: {land_tenure or 'unknown'}\n"
        f"Pasture found={pasture_data.get('found')}, confidence={pasture_data.get('confidence')}\n"
        f"Weather found={weather_data.get('found')}, confidence={weather_data.get('confidence')}\n"
        f"Grazing risk={grazing.get('grazing_risk')}, confidence={grazing.get('confidence')}\n"
        f"B2B context={'yes' if b2b else 'no'}"
    )

    return {
        "response": prose,
        "reasoning": reasoning,
        "recommendations": recommendations[:5],
        "tools_used": tools_used,
        "sources": sources,
        "decision": decision,
        "limitations": "; ".join(limitations) if isinstance(limitations, list) else str(limitations),
        "confidence": advisor.get("confidence") or "low",
        "user_tier": tier,
    }
