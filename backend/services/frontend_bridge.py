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
) -> dict[str, Any]:
    pasture_status = pasture_status_for_ui(pasture_data)
    weather_status = weather_status_for_ui(weather_data)
    alerts: list[str] = []
    recommendations: list[str] = []

    for item in pasture_status.get("limitations") or []:
        if "old" in item.lower() or "dated" in item.lower():
            alerts.append(item)
    for item in weather_status.get("limitations") or []:
        if "fail" in item.lower() or "unavailable" in item.lower():
            alerts.append(item)

    if grazing:
        risk = grazing.get("grazing_risk")
        if risk in {"high", "medium"}:
            alerts.append(f"Grazing risk signal: {risk} - {grazing.get('reason')}")
        recommendations.extend((grazing.get("signals") or [])[:3])
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
        "alerts": list(dict.fromkeys(alerts)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "confidence": pasture_data.get("confidence") or weather_data.get("confidence") or "low",
    }


def _build_free_response(
    *,
    location: str,
    pasture_data: dict[str, Any],
    weather_data: dict[str, Any],
    grazing: dict[str, Any],
    weather_ui: dict[str, Any],
    is_guest: bool = False,
) -> tuple[str, list[str], str]:
    risk = _risk_phrase(grazing.get("grazing_risk"))
    rain_words = _rainfall_context_words(
        weather_ui.get("recent_rainfall_mm"),
        (weather_data.get("recent_rainfall") or {}).get("days"),
    )

    if not pasture_data.get("found"):
        body = (
            f"I could not find rangeland survey data for {location}. "
            "Please choose a supported town or research site in your profile, "
            "then ask again."
        )
        return body, [], body

    if risk in {"high", "moderate"}:
        body = (
            f"Around {location}, grazing pressure looks {risk} and {rain_words}. "
            "Pasture recovery may be slow. It would be safer to ease pressure "
            "or rotate camps soon."
        )
    elif risk == "low":
        body = (
            f"Around {location}, grazing pressure looks relatively low and {rain_words}. "
            "Conditions look manageable for now, but keep watching the camp closely."
        )
    else:
        body = (
            f"Around {location}, the available pasture and rainfall signals are mixed. "
            "Use caution and check the camp on the ground before deciding."
        )

    cta = GUEST_LOGIN_CTA if is_guest else FREE_UPGRADE_CTA
    response = f"{body}\n\n{cta}"
    reasoning = (
        "Short free-tier guidance from pasture and weather signals, "
        "without detailed numbers."
    )
    return response, [], reasoning


def _build_premium_response(
    *,
    message: str,
    location: str,
    herd_size: Optional[int],
    livestock_type: Optional[str],
    pasture_data: dict[str, Any],
    weather_data: dict[str, Any],
    grazing: dict[str, Any],
    pasture_ui: dict[str, Any],
    weather_ui: dict[str, Any],
    b2b: bool,
) -> tuple[str, list[str], str]:
    lines: list[str] = []
    recommendations: list[str] = []
    risk = _risk_phrase(grazing.get("grazing_risk"))
    rain_words = _rainfall_context_words(
        weather_ui.get("recent_rainfall_mm"),
        (weather_data.get("recent_rainfall") or {}).get("days"),
    )
    animal = livestock_type or "livestock"

    if b2b:
        lines.append(
            f"Regional view for {location}: combining local rangeland observations "
            "with recent weather to support extension-style advice."
        )

    if herd_size is None:
        lines.append(
            "Herd size was not provided. Advice is more useful once you set herd size "
            "in your profile."
        )

    if pasture_data.get("found"):
        obs = pasture_ui.get("observation_date") or "an unknown date"
        lines.append(
            f"Based on {risk} grazing pressure signals and {rain_words}, "
            f"pasture recovery around {location} needs careful management."
        )
        lines.append(
            f"Latest survey reading (around {obs}) shows vegetation cover about "
            f"{_fmt(pasture_ui.get('vegetation_cover'), '%')}, bush/woody presence about "
            f"{_fmt(pasture_ui.get('bush_encroachment'), '%')}, and biomass about "
            f"{_fmt(pasture_ui.get('biomass'))}. These are measured values — not guesses."
        )
        if pasture_ui.get("cover_bare_ground_pct") is not None:
            lines.append(
                f"Bare ground is around {_fmt(pasture_ui.get('cover_bare_ground_pct'), '%')}, "
                "which helps judge how much rest the camp may need."
            )
    else:
        lines.append(
            f"I could not find pasture survey data for '{location}' in the processed "
            "Namibia dataset. Without that, stocking advice stays limited."
        )

    if weather_data.get("found"):
        lines.append(
            f"Rainfall context: about {_fmt(weather_ui.get('recent_rainfall_mm'), ' mm')} "
            f"in the recent window, with about {_fmt(weather_ui.get('forecast_total_mm'), ' mm')} "
            f"in the near-term forecast. Near-term temperature: "
            f"{_fmt(weather_ui.get('temperature'))}."
        )
    else:
        lines.append("Weather could not be resolved for this location.")

    # Carrying capacity is not in the dataset — say so clearly.
    lines.append(
        "Exact carrying capacity is not available in this dataset, so stocking advice "
        "stays qualitative and should be checked against what you see in the camp."
    )

    if grazing.get("reason"):
        lines.append(f"Grazing assessment: {grazing.get('reason')}")

    confidence = grazing.get("confidence") or pasture_data.get("confidence") or "low"
    if confidence == "low":
        lines.append(
            "Confidence is limited because some signals are missing or dated — "
            "treat this as guidance, not a guarantee."
        )

    # Actionable next steps
    if risk == "high":
        recommendations.extend(
            [
                f"Move {animal} out of the hardest-hit camp within the next few days if possible.",
                "Rest the paddock and reduce stocking pressure until cover improves.",
                "Check water points daily while rainfall stays limited.",
            ]
        )
    elif risk == "moderate":
        recommendations.extend(
            [
                "Rotate within the week if animals are concentrated in one camp.",
                "Watch forage height and bare patches over the next 7–10 days.",
                "Plan a lighter stocking rate until rainfall improves recovery.",
            ]
        )
    else:
        recommendations.extend(
            [
                "Continue current grazing if the camp still looks good on the ground.",
                "Keep a light rotation plan ready in case dry weather continues.",
            ]
        )

    if pasture_ui.get("bush_encroachment") is not None and pasture_ui["bush_encroachment"] >= 25:
        recommendations.append(
            "Bush is relatively high — keep cattle where grass access is still open."
        )

    if weather_ui.get("forecast_total_mm") is not None and weather_ui["forecast_total_mm"] == 0:
        recommendations.append(
            "Little/no rain in the forecast window — plan water and forage carefully."
        )

    for signal in (grazing.get("signals") or [])[:2]:
        if isinstance(signal, str) and signal not in recommendations:
            recommendations.append(signal)

    if b2b:
        recommendations.append(
            "At regional level, prioritize camps with weaker cover and coordinate "
            "rotation advice across neighbouring farms where possible."
        )

    if not recommendations:
        recommendations.append(
            "Walk the camp and compare what you see with the pasture and rainfall signals above."
        )

    action_block = "Clear next actions:\n" + "\n".join(
        f"- {item}" for item in recommendations[:5]
    )
    response = "\n\n".join(lines + [action_block])

    reasoning = (
        f"Question: {message}\n"
        f"Location: {location}\n"
        f"Herd size: {herd_size if herd_size is not None else 'not provided'}\n"
        f"Pasture found={pasture_data.get('found')}, confidence={pasture_data.get('confidence')}\n"
        f"Weather found={weather_data.get('found')}, confidence={weather_data.get('confidence')}\n"
        f"Grazing risk={grazing.get('grazing_risk')}, confidence={grazing.get('confidence')}\n"
        f"B2B context={'yes' if b2b else 'no'}"
    )
    return response, recommendations[:5], reasoning


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
) -> dict[str, Any]:
    """Shape POST /chat response expected by the Farmar frontend (pre-Gemini)."""
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

    if tier == "free":
        response, recommendations, reasoning = _build_free_response(
            location=location,
            pasture_data=pasture_data,
            weather_data=weather_data,
            grazing=grazing,
            weather_ui=weather_ui,
            is_guest=is_guest,
        )
        tools_used = [
            {"name": "get_pasture_data", "summary": f"Pasture lookup for {location}"},
            {"name": "get_weather", "summary": f"Weather context for {location}"},
        ]
        sources = None
        limitations = [
            "Free plan: short guidance only.",
            "Detailed metrics and forecasts are available on Premium.",
        ]
    else:
        response, recommendations, reasoning = _build_premium_response(
            message=message,
            location=location,
            herd_size=herd_size,
            livestock_type=livestock_type,
            pasture_data=pasture_data,
            weather_data=weather_data,
            grazing=grazing,
            pasture_ui=pasture_ui,
            weather_ui=weather_ui,
            b2b=b2b,
        )
        tools_used = [
            {
                "name": "get_pasture_data",
                "summary": f"Pasture lookup for {location}",
            },
            {
                "name": "get_weather",
                "summary": f"Open-Meteo rainfall/forecast for {location}",
            },
            {
                "name": "calculate_grazing_pressure",
                "summary": f"Grazing assessment risk={grazing.get('grazing_risk')}",
            },
        ]
        sources = {
            "pasture": pasture_ui,
            "weather": weather_ui,
            "grazing_assessment": grazing,
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

    return {
        "response": response,
        "reasoning": reasoning,
        "recommendations": recommendations,
        "tools_used": tools_used,
        "sources": sources,
        "limitations": "; ".join(limitations) if isinstance(limitations, list) else str(limitations),
        "confidence": advisor.get("confidence") or "low",
        "user_tier": tier,
    }
