"""
Build farmer-facing chat / dashboard payloads from existing tool outputs.

No Gemini yet — deterministic summaries from measured data + grazing assessment.
"""

from __future__ import annotations

from typing import Any, Optional


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.1f}{suffix}"
    return f"{value}{suffix}"


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
    forecast_total = forecast.get("total_precipitation_mm")

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
        "rainfall_last_7_days": None if recent_total is None else f"{recent_total} mm",
        "rainfall_last_30_days": None,
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
                "Treat advice as provisional — carrying capacity is not in the dataset."
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


def build_chat_response(
    *,
    message: str,
    location: str,
    advisor: dict[str, Any],
) -> dict[str, Any]:
    """Shape POST /chat response expected by the Farmar frontend (pre-Gemini)."""
    pasture_data = advisor.get("pasture_data") or {}
    weather_data = advisor.get("weather_data") or {}
    grazing = advisor.get("grazing_assessment") or {}
    pasture_ui = pasture_status_for_ui(pasture_data)
    weather_ui = weather_status_for_ui(weather_data)

    lines: list[str] = []
    if pasture_data.get("found"):
        sites = ", ".join(pasture_data.get("sites") or []) or "matched research sites"
        lines.append(
            f"For {location} (mapped to {sites}), latest field observations "
            f"({pasture_ui.get('observation_date') or 'date unknown'}) show "
            f"vegetation cover around {_fmt(pasture_ui.get('vegetation_cover'), '%')}, "
            f"bush/woody presence around {_fmt(pasture_ui.get('bush_encroachment'), '%')}, "
            f"and biomass around {_fmt(pasture_ui.get('biomass'))}."
        )
    else:
        lines.append(
            f"I could not find pasture survey data for '{location}' in the processed Namibia dataset."
        )

    if weather_data.get("found"):
        lines.append(
            f"Open-Meteo at the nearest dataset coordinates shows about "
            f"{_fmt(weather_ui.get('recent_rainfall_mm'), ' mm')} recent rainfall "
            f"and about {_fmt(weather_ui.get('forecast_total_mm'), ' mm')} in the forecast window. "
            f"Today/near-term temperature: {_fmt(weather_ui.get('temperature'))}."
        )
    else:
        lines.append("Weather could not be resolved for this location.")

    if grazing.get("grazing_risk"):
        lines.append(
            f"Grazing pressure context: risk={grazing.get('grazing_risk')} "
            f"(confidence={grazing.get('confidence')}). {grazing.get('reason')}"
        )

    lines.append(
        "This is a data summary from backend tools — not yet a Gemini LLM recommendation. "
        "Always verify conditions on the ground."
    )

    recommendations: list[str] = []
    if grazing.get("grazing_risk") == "high":
        recommendations.append(
            "Consider reducing grazing pressure or rotating camps if animals are concentrated."
        )
    if pasture_ui.get("bush_encroachment") is not None and pasture_ui["bush_encroachment"] >= 25:
        recommendations.append(
            "Bush/woody presence is relatively elevated — watch forage access for cattle."
        )
    if weather_ui.get("forecast_total_mm") is not None and weather_ui["forecast_total_mm"] == 0:
        recommendations.append(
            "Little/no rain in the forecast window — plan water and forage carefully."
        )
    for signal in (grazing.get("signals") or [])[:2]:
        recommendations.append(signal)
    if not recommendations:
        recommendations.append(
            "Review the pasture and weather numbers above with your local camp conditions."
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

    limitations = advisor.get("limitations") or []
    limitations = list(
        dict.fromkeys(
            limitations
            + [
                "Response is tool-generated context, not a live Gemini reasoning answer yet.",
                "Carrying capacity is not available in the dataset.",
            ]
        )
    )

    reasoning_parts = [
        f"Question received: {message}",
        f"Location used: {location}",
        f"Pasture found={pasture_data.get('found')}, confidence={pasture_data.get('confidence')}",
        f"Weather found={weather_data.get('found')}, confidence={weather_data.get('confidence')}",
        f"Grazing risk={grazing.get('grazing_risk')}, confidence={grazing.get('confidence')}",
    ]

    return {
        "response": "\n\n".join(lines),
        "reasoning": "\n".join(reasoning_parts),
        "recommendations": recommendations,
        "tools_used": tools_used,
        "sources": {
            "pasture": pasture_ui,
            "weather": weather_ui,
            "grazing_assessment": grazing,
        },
        "limitations": "; ".join(limitations) if isinstance(limitations, list) else str(limitations),
        "confidence": advisor.get("confidence") or "low",
    }
