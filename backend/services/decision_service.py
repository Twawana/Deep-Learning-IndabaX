"""
Decision-support layer for Namibian grazing advice.

Builds structured, farmer-facing recommendations from existing pasture,
weather, and grazing tool outputs. Uses NDVI and carrying capacity when
present (synthetic rows); otherwise those stay explicitly unavailable.
"""

from __future__ import annotations

from typing import Any, Optional


PRIORITY_LABELS = {
    "stay": "Continue Grazing",
    "monitor": "Monitor Closely",
    "move_soon": "Prepare to Move",
    "move_now": "Move Herd",
}

PRIORITY_STATUS = {
    "stay": "Suitable",
    "monitor": "Monitor Closely",
    "move_soon": "Prepare to Move",
    "move_now": "Move Recommended",
}

HEALTH_LEVELS = {
    "good": "Good",
    "fair": "Fair",
    "stressed": "Stressed",
    "poor": "Poor",
    "unknown": "Uncertain",
}


def _f(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tenure_tone(land_tenure: Optional[str]) -> str:
    tone = (land_tenure or "unknown").strip().lower()
    if tone in {"communal", "commercial", "conservancy"}:
        return tone
    return "unknown"


def _alt_grazing_phrase(tenure: str) -> str:
    if tenure == "commercial":
        return "another paddock"
    if tenure == "communal":
        return "an alternative communal grazing area"
    if tenure == "conservancy":
        return "another grazing area within the conservancy"
    return "another grazing camp"


def _move_phrase(tenure: str, when: str) -> str:
    alt = _alt_grazing_phrase(tenure)
    if tenure == "communal":
        return (
            f"If {alt} is available, begin planning to move your herd {when}, "
            "coordinating grazing pressure with neighbours where possible."
        )
    if tenure == "commercial":
        return f"Consider rotating to {alt} {when}."
    return f"If {alt} is available, begin planning to move your herd {when}."


def _rain_dry(recent_mm: Optional[float], forecast_mm: Optional[float]) -> bool:
    recent_dry = recent_mm is None or recent_mm <= 5
    forecast_dry = forecast_mm is None or forecast_mm <= 5
    return recent_dry and forecast_dry


def _cover_stressed(cover: Optional[float], biomass: Optional[float]) -> bool:
    if cover is not None and cover < 15:
        return True
    if biomass is not None:
        # Synthetic grass biomass is kg/ha (often 200+); Lacuna field biomass is smaller.
        if biomass >= 200:
            return biomass < 450
        return biomass < 50
    return False


def _biomass_healthy(biomass: Optional[float]) -> bool:
    if biomass is None:
        return False
    if biomass >= 200:
        return biomass >= 900
    return biomass >= 100


def _pasture_health_level(
    cover: Optional[float],
    biomass: Optional[float],
    bush: Optional[float],
    risk: str,
) -> str:
    if cover is None and biomass is None:
        return "unknown"
    if _cover_stressed(cover, biomass) or risk == "high":
        return "poor" if (cover is not None and cover < 10) or risk == "high" else "stressed"
    if cover is not None and cover >= 35 and (biomass is None or _biomass_healthy(biomass)):
        if bush is not None and bush >= 30:
            return "fair"
        return "good"
    return "fair"


def _action_priority(
    risk: str,
    *,
    recent_mm: Optional[float],
    forecast_mm: Optional[float],
    cover: Optional[float],
    biomass: Optional[float],
) -> str:
    dry = _rain_dry(recent_mm, forecast_mm)
    stressed = _cover_stressed(cover, biomass)

    if risk == "high" and dry and stressed:
        return "move_now"
    if risk == "high":
        return "move_soon" if not dry else "move_now"
    if risk == "medium":
        if dry or stressed:
            return "move_soon"
        return "monitor"
    if risk == "low":
        if dry:
            return "monitor"
        if forecast_mm is not None and forecast_mm > 5:
            return "stay"
        return "monitor"
    # unknown
    if dry and stressed:
        return "move_soon"
    return "monitor"


def _rainfall_outlook(
    recent_mm: Optional[float],
    forecast_mm: Optional[float],
    recent_days: Any,
) -> dict[str, Any]:
    days = recent_days or 7
    dry = _rain_dry(recent_mm, forecast_mm)

    if recent_mm is None and forecast_mm is None:
        outlook = (
            "Rainfall information could not be confirmed for this area. "
            "Treat grass-recovery expectations cautiously and check conditions on the ground."
        )
        bullets = [
            "Weather data was unavailable for this location.",
            "Walk the camp before deciding how long livestock can stay.",
        ]
        level = "unknown"
    elif dry:
        outlook = (
            "Dry conditions are expected. "
            f"There has been little or no meaningful rainfall during the last {days} days "
            "and very little is expected over the coming days. "
            "This means grass recovery is likely to remain slow."
        )
        bullets = [
            "Grass is unlikely to recover quickly.",
            "Continued grazing will increase pressure on available forage.",
            "Consider monitoring pasture closely.",
        ]
        level = "dry"
    elif (forecast_mm or 0) > 10 or (recent_mm or 0) > 15:
        outlook = (
            "Some useful rainfall has occurred or is expected. "
            "This should help support pasture recovery, though recovery still depends on "
            "how hard the camp is currently grazed."
        )
        bullets = [
            "Rainfall should support some grass recovery.",
            "Grazing pressure still needs watching while cover rebuilds.",
            "Re-check the camp after rain before increasing stocking.",
        ]
        level = "helpful"
    else:
        outlook = (
            "Rainfall has been limited. "
            "A little rain may help, but grass recovery is likely to stay slow "
            "if grazing pressure remains high."
        )
        bullets = [
            "Grass recovery may stay limited.",
            "Avoid concentrating animals in the weakest camps.",
            "Monitor cover and bare patches over the coming week.",
        ]
        level = "limited"

    return {
        "level": level,
        "outlook": outlook,
        "impact_bullets": bullets,
        "details": {
            "recent_mm": recent_mm,
            "forecast_mm": forecast_mm,
            "recent_days": days,
        },
    }


def _pasture_summary(
    level: str,
    cover: Optional[float],
    biomass: Optional[float],
    bush: Optional[float],
) -> str:
    if level == "unknown":
        return (
            "Pasture measurements for this location are limited. "
            "Based on available data, treat grazing decisions carefully and verify on the ground."
        )
    if level == "poor":
        return (
            "Vegetation is under clear stress. "
            "Available grazing looks limited, and recovery may be slow if dry conditions continue."
        )
    if level == "stressed":
        return (
            "Vegetation is showing signs of stress under current grazing pressure. "
            "The grass can still support livestock for a short time, but recovery may slow "
            "if dry conditions continue."
        )
    if level == "fair":
        return (
            "Grass is still available, but signs of grazing pressure are increasing. "
            "Recovery may be slower if dry conditions continue."
        )
    bush_note = ""
    if bush is not None and bush >= 25:
        bush_note = " Bush/woody cover is relatively elevated, so keep cattle where grass access remains open."
    cover_note = f" Vegetation cover is around {cover:.0f}%." if cover is not None else ""
    bio_note = f" Available grazing (biomass) reading is about {biomass:.0f}." if biomass is not None else ""
    return (
        f"Pasture currently looks relatively healthy for continued grazing.{cover_note}{bio_note}{bush_note}"
    )


def _technical_metrics(
    pasture_ui: dict[str, Any],
    grazing: dict[str, Any],
) -> list[dict[str, Any]]:
    carrying = pasture_ui.get("carrying_capacity")
    ndvi = pasture_ui.get("ndvi")
    return [
        {
            "key": "vegetation_cover",
            "label": "Vegetation Health",
            "technical_name": "Vegetation cover",
            "value": pasture_ui.get("vegetation_cover"),
            "unit": "%",
            "plain_language": "Shows how much living plant cover is present in the surveyed plots.",
        },
        {
            "key": "biomass",
            "label": "Available Grazing",
            "technical_name": "Biomass",
            "value": pasture_ui.get("biomass"),
            "unit": None,
            "plain_language": "An estimate of plant material available as forage from field measurements.",
        },
        {
            "key": "bush_encroachment",
            "label": "Bush / Woody Cover",
            "technical_name": "Bush encroachment",
            "value": pasture_ui.get("bush_encroachment"),
            "unit": "%",
            "plain_language": "How much woody plants (bush/trees) are present, which can limit grass access.",
        },
        {
            "key": "grazing_pressure",
            "label": "Current Grazing Pressure",
            "technical_name": "Grazing pressure (recorded / assessed)",
            "value": pasture_ui.get("grazing_pressure") or grazing.get("grazing_risk"),
            "unit": None,
            "plain_language": "Combines herd context and pasture readings to indicate how hard the camp is being used.",
        },
        {
            "key": "carrying_capacity",
            "label": "Recommended Grazing Capacity",
            "technical_name": "Carrying capacity",
            "value": carrying,
            "unit": "ha/LSU" if carrying is not None else None,
            "plain_language": (
                f"Estimated land needed per livestock unit: about {carrying:.1f} ha/LSU."
                if carrying is not None
                else "Not available for this location. Stocking advice stays qualitative and should be checked on the ground."
            ),
        },
        {
            "key": "ndvi",
            "label": "Vegetation Health (satellite)",
            "technical_name": "NDVI",
            "value": ndvi,
            "unit": None,
            "plain_language": (
                f"Satellite greenness index about {ndvi:.2f} (higher usually means greener vegetation)."
                if ndvi is not None
                else "A satellite greenness index. Not provided for this location."
            ),
        },
    ]


def _timeline(
    priority: str,
    *,
    dry: bool,
    tenure: str,
) -> list[dict[str, Any]]:
    alt = _alt_grazing_phrase(tenure)

    if priority == "stay":
        return [
            {
                "when": "today",
                "status": "stay",
                "label": "Suitable",
                "note": "Based on current conditions, pasture can still support grazing.",
            },
            {
                "when": "3_days",
                "status": "stay",
                "label": "Continue Monitoring",
                "note": "Current evidence suggests conditions should remain acceptable if rainfall holds.",
            },
            {
                "when": "7_days",
                "status": "monitor",
                "label": "Re-check Camp",
                "note": "Walk the camp again and confirm cover has not declined.",
            },
            {
                "when": "10_14_days",
                "status": "monitor",
                "label": "Review Plan",
                "note": f"If dry conditions return, prepare {alt} as a backup.",
            },
        ]

    if priority == "monitor":
        return [
            {
                "when": "today",
                "status": "monitor",
                "label": "Monitor Closely",
                "note": "Pasture can still support grazing, but recovery signals need watching.",
            },
            {
                "when": "3_days",
                "status": "monitor",
                "label": "Continue Monitoring",
                "note": "Check forage height, bare patches, and water points.",
            },
            {
                "when": "7_days",
                "status": "move_soon",
                "label": "Prepare to Move",
                "note": (
                    "If rainfall remains low, grass recovery may become limited. "
                    f"Start planning {alt}."
                ),
            },
            {
                "when": "10_14_days",
                "status": "move_soon",
                "label": "Likely Move Window",
                "note": (
                    "Current evidence suggests moving livestock may be needed "
                    "if grazing pressure stays similar and rain stays limited."
                ),
            },
        ]

    if priority == "move_soon":
        return [
            {
                "when": "today",
                "status": "monitor",
                "label": "Still Grazing — Carefully",
                "note": "Livestock can stay for now, but stress signals are rising.",
            },
            {
                "when": "3_days",
                "status": "move_soon",
                "label": "Prepare to Move",
                "note": f"Identify {alt} and reduce concentration in the weakest areas.",
            },
            {
                "when": "7_days",
                "status": "move_soon",
                "label": "Plan Move",
                "note": _move_phrase(tenure, "within about one week"),
            },
            {
                "when": "10_14_days",
                "status": "move_now",
                "label": "Move Herd",
                "note": (
                    "If rainfall remains low and grazing pressure continues, "
                    "moving livestock is recommended based on current evidence."
                ),
            },
        ]

    # move_now
    return [
        {
            "when": "today",
            "status": "move_now",
            "label": "Move Recommended",
            "note": (
                "Based on available data, grazing pressure appears unsustainable "
                "under current dry conditions."
            ),
        },
        {
            "when": "3_days",
            "status": "move_now",
            "label": "Complete Move",
            "note": f"If possible, finish moving animals to {alt} within a few days.",
        },
        {
            "when": "7_days",
            "status": "monitor",
            "label": "Rest Camp",
            "note": "Allow the rested camp time to recover; re-check cover after any rainfall.",
        },
        {
            "when": "10_14_days",
            "status": "monitor",
            "label": "Review Recovery",
            "note": "Current evidence suggests reviewing whether the camp has begun to recover before returning livestock.",
        },
    ]


def _recommended_action(priority: str, tenure: str, dry: bool) -> str:
    if priority == "stay":
        return (
            "Based on available data, current conditions appear suitable for continued grazing. "
            "Keep watching the camp and rainfall over the coming week."
        )
    if priority == "monitor":
        return (
            "Current conditions suggest continued grazing with close monitoring. "
            "Re-check pasture and rainfall within several days"
            + (" while dry weather continues." if dry else ".")
        )
    if priority == "move_soon":
        return _move_phrase(tenure, "within about one week")
    return _move_phrase(tenure, "as soon as practical — preferably within a few days")


def _what_if_not(priority: str) -> str:
    if priority == "stay":
        return (
            "If you ignore monitoring, you may miss early signs of declining cover "
            "before the next rainfall window."
        )
    if priority == "monitor":
        return (
            "If grazing continues without checking the camp, forage may decline further "
            "before recovery can begin."
        )
    if priority == "move_soon":
        return (
            "If the herd stays put under current dry conditions, pasture degradation may increase "
            "and forage availability may fall further."
        )
    return (
        "Continued heavy grazing under these conditions may further reduce forage "
        "and make recovery slower once rain returns."
    )


def _pasture_ui_lite(pasture_data: dict[str, Any]) -> dict[str, Any]:
    if not pasture_data.get("found"):
        return {
            "found": False,
            "vegetation_cover": None,
            "biomass": None,
            "bush_encroachment": None,
            "grazing_pressure": None,
            "carrying_capacity": None,
            "ndvi": None,
            "observation_date": None,
            "sites": [],
            "dataset_source": None,
        }
    metrics = pasture_data.get("pasture") or {}
    nearby = pasture_data.get("nearby_synthetic") or {}
    carrying = metrics.get("carrying_capacity_ha_per_lsu")
    if carrying is None and nearby.get("found"):
        carrying = nearby.get("carrying_capacity_ha_per_lsu")
    ndvi = metrics.get("ndvi")
    if ndvi is None and nearby.get("found"):
        ndvi = nearby.get("ndvi")
    return {
        "found": True,
        "vegetation_cover": metrics.get("vegetation_cover"),
        "biomass": metrics.get("biomass"),
        "bush_encroachment": metrics.get("bush_encroachment"),
        "grazing_pressure": metrics.get("grazing_pressure_recorded")
        or metrics.get("grazing_pressure_label"),
        "carrying_capacity": carrying,
        "ndvi": ndvi,
        "livestock_density_lsu_per_ha": metrics.get("livestock_density_lsu_per_ha")
        or nearby.get("livestock_density_lsu_per_ha"),
        "observation_date": pasture_data.get("observation_date"),
        "sites": pasture_data.get("sites") or [],
        "dataset_source": metrics.get("dataset_source"),
    }


def _weather_ui_lite(weather_data: dict[str, Any]) -> dict[str, Any]:
    if not weather_data.get("found"):
        return {
            "found": False,
            "recent_rainfall_mm": None,
            "forecast_total_mm": None,
            "temperature": None,
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
    return {
        "found": True,
        "recent_rainfall_mm": recent.get("total_precipitation_mm"),
        "forecast_total_mm": forecast.get("total_precipitation_mm"),
        "temperature": temperature,
    }


def build_decision(
    *,
    location: str,
    pasture_data: dict[str, Any],
    weather_data: dict[str, Any],
    grazing: Optional[dict[str, Any]] = None,
    land_tenure: Optional[str] = None,
    herd_size: Optional[int] = None,
) -> dict[str, Any]:
    """
    Build the structured decision block for dashboard/chat/advisor/scenarios.
    """
    grazing = grazing or {}
    tenure = _tenure_tone(land_tenure)
    pasture_ui = _pasture_ui_lite(pasture_data)
    weather_ui = _weather_ui_lite(weather_data)

    cover = _f(pasture_ui.get("vegetation_cover"))
    biomass = _f(pasture_ui.get("biomass"))
    bush = _f(pasture_ui.get("bush_encroachment"))
    recent_mm = _f(weather_ui.get("recent_rainfall_mm"))
    forecast_mm = _f(weather_ui.get("forecast_total_mm"))
    recent_days = (weather_data.get("recent_rainfall") or {}).get("days") or 7
    risk = (grazing.get("grazing_risk") or "unknown").lower()
    dry = _rain_dry(recent_mm, forecast_mm)

    if not pasture_data.get("found") and not weather_data.get("found"):
        priority = "monitor"
        health = "unknown"
    else:
        priority = _action_priority(
            risk,
            recent_mm=recent_mm,
            forecast_mm=forecast_mm,
            cover=cover,
            biomass=biomass,
        )
        health = _pasture_health_level(cover, biomass, bush, risk)

    rain = _rainfall_outlook(recent_mm, forecast_mm, recent_days)
    pasture_text = _pasture_summary(health, cover, biomass, bush)
    action = _recommended_action(priority, tenure, dry)

    rainfall_summary = rain["outlook"].split(".")[0] + "."
    combined = (
        "Without meaningful rainfall, pasture recovery will likely remain slow."
        if dry
        else (
            "Rainfall should help support recovery, but grazing pressure still needs watching."
            if rain["level"] == "helpful"
            else "Limited rainfall means recovery may stay slow if grazing continues at the same intensity."
        )
    )
    if not pasture_data.get("found"):
        pasture_text = (
            f"I could not find pasture survey data for '{location}'. "
            "Recommendation confidence is limited until a supported site is selected."
        )
        combined = "Pasture evidence is missing, so advice stays cautious."

    conf_level = (
        grazing.get("confidence")
        or pasture_data.get("confidence")
        or weather_data.get("confidence")
        or "low"
    )
    conf_explanation = (
        f"Data quality is {conf_level}. "
        "Pasture readings come from the latest available field observations for nearby research sites. "
        "Weather information comes from Open-Meteo using the nearest available coordinates to your "
        "selected grazing area. Conditions on your specific farm may differ slightly, especially over "
        "large distances or different terrain."
    )

    checks = [
        {
            "id": "pasture",
            "label": "Pasture condition checked",
            "done": bool(pasture_data.get("found")),
        },
        {
            "id": "rainfall",
            "label": "Rainfall analysed",
            "done": bool(weather_data.get("found")),
        },
        {
            "id": "herd",
            "label": "Herd size considered" if herd_size is not None else "Herd size not provided",
            "done": herd_size is not None,
        },
        {
            "id": "grazing",
            "label": "Grazing pressure evaluated",
            "done": bool(grazing.get("grazing_risk")),
        },
        {
            "id": "combined",
            "label": "Recommendation generated from combined evidence",
            "done": True,
        },
    ]

    why = [
        pasture_text,
        rainfall_summary,
    ]
    if herd_size is not None:
        why.append(f"Herd size of about {herd_size} animals was included in the pressure assessment.")
    if grazing.get("reason"):
        why.append(str(grazing["reason"]))
    for signal in (grazing.get("signals") or [])[:2]:
        if isinstance(signal, str):
            why.append(signal)

    monitor_next = [
        "Monitor rainfall over the coming week.",
        "Check grass cover and bare ground in the camp.",
        "Watch livestock condition and water points.",
    ]
    if dry:
        monitor_next.append("Watch for further drying or dustier patches.")

    temperature = weather_ui.get("temperature")
    rain["details"]["temperature"] = temperature

    return {
        "action_priority": priority,
        "headline": PRIORITY_LABELS.get(priority, "Monitor Closely"),
        "overall_status_label": PRIORITY_STATUS.get(priority, "Monitor Closely"),
        "recommended_action": action,
        "grazing_conditions": {
            "overall_status": PRIORITY_STATUS.get(priority, "Monitor Closely"),
            "action_priority": priority,
            "pasture_summary": pasture_text,
            "rainfall_summary": rainfall_summary,
            "combined_assessment": combined,
            "recommended_action": action,
        },
        "rainfall_impact": rain,
        "pasture_health": {
            "level": health,
            "label": HEALTH_LEVELS.get(health, "Uncertain"),
            "summary": pasture_text,
            "observation_date": pasture_ui.get("observation_date"),
            "sites": pasture_ui.get("sites") or [],
            "technical": _technical_metrics(pasture_ui, grazing),
        },
        "timeline": _timeline(priority, dry=dry, tenure=tenure),
        "explainer": {
            "what": action,
            "why": why,
            "what_if_not": _what_if_not(priority),
            "monitor_next": monitor_next,
            "checks": checks,
        },
        "confidence": {
            "level": conf_level,
            "explanation": conf_explanation,
        },
        "tenure_tone": tenure,
        "location": location,
        "grazing_risk": risk,
        "herd_size": herd_size,
    }


def advisor_prose_from_decision(
    *,
    decision: dict[str, Any],
    location: str,
    message: str = "",
) -> str:
    """Natural extension-officer style paragraph from a decision block."""
    # Prefer question-shaped answers when the farmer asked something specific.
    aware = question_aware_local_reply(
        message=message,
        location=location,
        decision=decision,
        pasture_data={"found": bool((decision.get("pasture_health") or {}).get("summary")), "pasture": {}},
        weather_data={"found": True},
        grazing={"grazing_risk": decision.get("grazing_risk")},
        stocking=None,
        herd_size=decision.get("herd_size"),
    )
    # If we have a strong rainfall/dwell/stocking answer, use it.
    msg = (message or "").lower()
    if any(
        k in msg
        for k in (
            "how long",
            "rainfall",
            "rain",
            "stock",
            "overgraz",
            "move",
            "when",
            "bush",
            "carrying",
        )
    ):
        return aware

    pasture = (decision.get("pasture_health") or {}).get("summary") or ""
    rain_block = decision.get("rainfall_impact") or {}
    rain = rain_block.get("outlook") or ""
    rain_level = (rain_block.get("level") or "").lower()
    action = decision.get("recommended_action") or ""
    combined = (decision.get("grazing_conditions") or {}).get("combined_assessment") or ""
    weather_available = rain_level not in {"", "unknown"}

    opener = (
        f"Based on the pasture condition and recent rainfall around {location}, "
        if weather_available
        else f"Based on the local pasture data for {location}, "
    )
    closer = (
        "This is guidance from available field and weather data — always verify conditions on the ground."
        if weather_available
        else "This is guidance from the local advisory dataset — always verify conditions on the ground."
    )

    parts = [
        f"{opener}{action[0].lower() + action[1:] if action else 'keep monitoring the camp.'}",
        pasture,
        rain.split("Impact")[0].strip() if rain and weather_available else "",
        combined,
        closer,
    ]
    seen: set[str] = set()
    lines: list[str] = []
    for part in parts:
        text = " ".join(str(part).split()).strip()
        if not text:
            continue
        key = text.lower()[:80]
        if key in seen:
            continue
        seen.add(key)
        lines.append(text)
    if message and "compare" in message.lower():
        lines.insert(0, "Here is a grazing-focused reading of your question.")
    return "\n\n".join(lines) if lines else aware


def question_aware_local_reply(
    *,
    message: str,
    location: str,
    decision: Optional[dict[str, Any]] = None,
    pasture_data: Optional[dict[str, Any]] = None,
    weather_data: Optional[dict[str, Any]] = None,
    grazing: Optional[dict[str, Any]] = None,
    stocking: Optional[dict[str, Any]] = None,
    year_over_year: Optional[dict[str, Any]] = None,
    herd_size: Optional[int] = None,
) -> str:
    """
    Local (non-Gemini) answer shaped to the farmer's question.

    Used when Gemini is unavailable/quota-limited so every ask does not collapse
    into the same "Monitor Closely" template.
    """
    decision = decision or {}
    pasture_data = pasture_data or {}
    weather_data = weather_data or {}
    grazing = grazing or {}
    stocking = stocking or {}
    year_over_year = year_over_year or {}
    text = (message or "").lower()

    # Pure off-topic / non-farm
    farm_markers = (
        "bush",
        "encroach",
        "pasture",
        "graz",
        "herd",
        "rain",
        "stock",
        "camp",
        "farm",
        "cattle",
        "move",
        "veld",
        "cover",
        "biomass",
        "ndvi",
        "tenure",
    )
    if not any(k in text for k in farm_markers) and any(
        k in text for k in ("gay", "joke", "meme", "who are you", "hate", "stupid")
    ):
        return (
            "I'm Vision — I only help with Namibian rangeland and herd decisions "
            "(pasture, rainfall, stocking, bush, when to move). Ask me about your camps."
        )

    pasture_ui = _pasture_ui_lite(pasture_data) if pasture_data else {}
    weather_ui = _weather_ui_lite(weather_data) if weather_data else {}
    cover = _f(pasture_ui.get("vegetation_cover"))
    biomass = _f(pasture_ui.get("biomass"))
    bush = _f(pasture_ui.get("bush_encroachment"))
    # Pull metrics from decision technical block when pasture_data was empty
    if cover is None and decision.get("pasture_health"):
        tech = (decision.get("pasture_health") or {}).get("technical")
        if isinstance(tech, dict):
            cover = _f(tech.get("vegetation_cover"))
            biomass = _f(tech.get("biomass")) if biomass is None else biomass
            bush = _f(tech.get("bush_encroachment")) if bush is None else bush
        elif isinstance(tech, list):
            for row in tech:
                if not isinstance(row, dict):
                    continue
                key = str(row.get("id") or row.get("key") or row.get("label") or "").lower()
                val = row.get("value")
                if cover is None and "cover" in key:
                    cover = _f(val)
                if biomass is None and "biomass" in key:
                    biomass = _f(val)
                if bush is None and "bush" in key:
                    bush = _f(val)
    rain_block = decision.get("rainfall_impact") or {}
    recent_mm = _f(
        weather_ui.get("recent_rainfall_mm")
        if weather_ui
        else rain_block.get("recent_rainfall_mm")
    )
    forecast_mm = _f(
        weather_ui.get("forecast_total_mm")
        if weather_ui
        else rain_block.get("forecast_total_mm")
    )
    recent_days = (weather_data.get("recent_rainfall") or {}).get("days") or 7
    priority = (decision.get("action_priority") or "monitor").lower()
    risk = (grazing.get("grazing_risk") or decision.get("grazing_risk") or "unknown").lower()

    def _fmt_mm(v: Optional[float]) -> str:
        if v is None:
            return "not confirmed in the weather feed"
        return f"about {v:.1f} mm"

    def _dwell_window() -> str:
        if priority == "stay":
            return "roughly 2–3 weeks of continued grazing looks plausible if you keep checking the camp"
        if priority == "monitor":
            return "likely only several more days to about 1–2 weeks before you should plan a move"
        if priority == "move_soon":
            return "plan to move within about one week"
        return "move as soon as practical — preferably within a few days"

    rain_line = (
        f"Recent rainfall near {location}: {_fmt_mm(recent_mm)} over the last {recent_days} days"
        + (
            f"; forecast total around {_fmt_mm(forecast_mm)}."
            if forecast_mm is not None
            else "."
        )
    )
    pasture_bits = []
    if cover is not None:
        pasture_bits.append(f"vegetation cover ~{cover:.0f}%")
    if biomass is not None:
        pasture_bits.append(f"biomass ~{biomass:.0f}")
    if bush is not None:
        pasture_bits.append(f"bush ~{bush:.0f}%")
    pasture_line = (
        f"Pasture readings: {', '.join(pasture_bits)}."
        if pasture_bits
        else (
            f"I have pasture survey context for {location}."
            if pasture_data.get("found") or decision.get("pasture_health")
            else f"I could not lock strong pasture measurements for {location}."
        )
    )
    pressure_line = (
        f"Grazing pressure risk is currently marked {risk}"
        + (f" with a herd of about {herd_size}." if herd_size is not None else ".")
    )

    # --- Rainfall + how long can herd stay ---
    if any(
        k in text
        for k in (
            "how long",
            "how many days",
            "how many weeks",
            "before i need to move",
            "before i move",
            "stay on this",
            "dwell",
        )
    ) or (
        "rain" in text
        and any(k in text for k in ("move", "stay", "herd", "pasture", "camp"))
    ):
        dry = _rain_dry(recent_mm, forecast_mm)
        rain_note = (
            "That is little useful rain for recovery, so forage will not bounce back quickly."
            if dry
            else "There has been some useful moisture, which helps a bit, but pressure still matters."
        )
        return "\n\n".join(
            [
                f"For {location}, here is a direct read on how long the herd can stay.",
                rain_line + " " + rain_note,
                pasture_line,
                pressure_line,
                f"Stay window: {_dwell_window()}. Re-check the camp after any new rain, and sooner if cover keeps falling.",
                "This is an estimate from local pasture records and weather data — walk the camp before you decide.",
            ]
        )

    # --- Overgrazed? ---
    if "overgraz" in text or "over graz" in text:
        stressed = _cover_stressed(cover, biomass) or risk in {"high", "medium"}
        verdict = (
            "Yes — current readings suggest this camp is under too much pressure / stressed."
            if stressed
            else "Not clearly overgrazed from the numbers on file, but keep watching."
        )
        return "\n\n".join(
            [
                f"Overgrazing check for {location}:",
                verdict,
                pasture_line,
                pressure_line,
                rain_line,
                "If animals stay on a stressed camp through a dry spell, recovery gets slower.",
            ]
        )

    # --- Stocking / carrying ---
    if any(k in text for k in ("stocking", "carrying capacity", "how many animal", "safe herd", "ha/lsu", "lsu")):
        stock_bits = []
        if stocking.get("found"):
            if stocking.get("status"):
                stock_bits.append(str(stocking["status"]))
            if stocking.get("message"):
                stock_bits.append(str(stocking["message"]))
            if stocking.get("safe_herd_size") is not None:
                stock_bits.append(f"Safe herd estimate ~{stocking['safe_herd_size']}.")
            if stocking.get("recommended_ha_per_lsu") is not None:
                stock_bits.append(
                    f"Rough carrying guidance ~{stocking['recommended_ha_per_lsu']} ha/LSU."
                )
        cap = pasture_ui.get("carrying_capacity")
        if cap is not None and not stock_bits:
            stock_bits.append(f"Carrying capacity on file is about {cap:.1f} ha/LSU.")
        body = " ".join(stock_bits) if stock_bits else (
            "I need herd size and camp hectares in Profile to turn carrying capacity into a head-count."
        )
        return "\n\n".join(
            [
                f"Stocking / carrying capacity for {location}:",
                body,
                pasture_line,
                rain_line,
            ]
        )

    # --- Move when? ---
    if any(k in text for k in ("should i move", "when to move", "prepare to move", "move my herd", "move the herd")):
        return "\n\n".join(
            [
                f"Move timing for {location}:",
                f"Suggested action band: {(decision.get('headline') or priority)}.",
                f"Practical timing: {_dwell_window()}.",
                pasture_line,
                rain_line,
                pressure_line,
            ]
        )

    # --- Rainfall only ---
    if any(k in text for k in ("rainfall", "rain", "forecast", "drought", "dry spell")):
        return "\n\n".join(
            [
                f"Rainfall context for {location}:",
                rain_line,
                (
                    "Dry conditions mean pasture recovery will stay slow if grazing continues at the same intensity."
                    if _rain_dry(recent_mm, forecast_mm)
                    else "Moisture looks more helpful than a dry spell — still watch how the grass responds."
                ),
                pasture_line,
            ]
        )

    # --- Bush encroachment (answer the question directly) ---
    if any(k in text for k in ("bush", "encroach", "woody")):
        yoy = year_over_year if year_over_year.get("found") else {}
        deltas = (yoy.get("deltas") or {}) if yoy else {}
        bush_delta = _f(deltas.get("bush_encroachment"))
        current_bush = bush
        if current_bush is None and yoy.get("current"):
            current_bush = _f((yoy.get("current") or {}).get("bush_encroachment"))

        if bush_delta is not None and bush_delta >= 5:
            trend = (
                f"Yes — bush/woody signal looks worse than last year "
                f"(about +{bush_delta:.0f} points)."
            )
        elif bush_delta is not None and bush_delta <= -5:
            trend = (
                f"No — bush/woody signal is not getting worse; it looks better than last year "
                f"(about {bush_delta:.0f} points)."
            )
        elif bush_delta is not None:
            trend = (
                "Bush/woody signal is roughly stable versus last year — not a clear worsening trend."
            )
        elif current_bush is not None and current_bush >= 25:
            trend = (
                f"I do not have a firm year-to-year bush trend, but current bush/woody cover "
                f"is elevated (~{current_bush:.0f}%). Treat encroachment as an active issue."
            )
        elif current_bush is not None:
            trend = (
                f"I do not have a firm year-to-year bush trend. Current bush/woody cover is "
                f"about {current_bush:.0f}% — watch it, but it is not extreme from this reading alone."
            )
        else:
            trend = (
                "I could not confirm a clear bush trend for this farm from the on-file survey rows. "
                "Walk the camps and compare woody thickening on rested vs heavily used areas."
            )

        actions = [
            "What to do:",
            "1) Rest the worst bushy camps this season if you can rotate.",
            "2) Keep grazing pressure off recovering grass — do not park the whole herd on thinning veld.",
            "3) Where bush is already dense, plan mechanical thinning / targeted browsing (goats) only with local extension advice for your tenure rules.",
            "4) Re-check the same camps after the next rainy season — rising bush % year-on-year means act sooner.",
        ]
        return "\n\n".join(
            [
                f"Bush encroachment on/near {location}:",
                trend,
                pasture_line,
                "\n".join(actions),
            ]
        )

    # --- Pasture / cover (non-bush) ---
    if any(k in text for k in ("pasture", "ndvi", "cover", "veld", "camp condition")):
        return "\n\n".join(
            [
                f"Pasture condition around {location}:",
                pasture_line,
                (decision.get("pasture_health") or {}).get("summary")
                or "Use the cover/biomass readings above as your baseline.",
                rain_line,
                pressure_line,
            ]
        )

    # Default — still include numbers so answers are not identical shells
    action = decision.get("recommended_action") or _dwell_window()
    return "\n\n".join(
        [
            f"About {location}:",
            pasture_line,
            rain_line,
            pressure_line,
            action,
            "Ask a more specific question (rainfall stay-time, stocking, overgrazing, or which camp to rest) for a sharper answer.",
        ]
    )


def scenario_decision(
    *,
    location: str,
    pasture_data: dict[str, Any],
    weather_data: dict[str, Any],
    grazing: Optional[dict[str, Any]] = None,
    land_tenure: Optional[str] = None,
    herd_size: Optional[int] = None,
    assume_rain_mm: Optional[float] = None,
    move_in_days: Optional[int] = None,
    note_prefix: str = "",
) -> dict[str, Any]:
    """
    Build a scenario decision. Rain assumptions only change narrative/priority
    inputs — they do not fabricate vegetation growth.
    """
    weather = dict(weather_data or {})
    if assume_rain_mm is not None and weather.get("found"):
        # Hypothetical overlay on forecast total only (transparent)
        forecast = dict(weather.get("forecast") or {})
        forecast = {
            **forecast,
            "total_precipitation_mm": float(assume_rain_mm),
            "days": forecast.get("days") or 7,
            "scenario_note": f"Scenario assumes about {assume_rain_mm} mm of rain in the coming window.",
        }
        weather = {**weather, "forecast": forecast}

    decision = build_decision(
        location=location,
        pasture_data=pasture_data,
        weather_data=weather,
        grazing=grazing,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )

    notes: list[str] = []
    if note_prefix:
        notes.append(note_prefix)
    if assume_rain_mm is not None:
        notes.append(
            f"If about {assume_rain_mm} mm of rainfall occurred in the coming week, "
            "the recommendation below reflects that scenario — not a guaranteed forecast."
        )
    if move_in_days is not None:
        notes.append(
            f"This scenario focuses on a move planning window of about {move_in_days} days. "
            "It does not invent future pasture growth."
        )
    if herd_size is not None:
        notes.append(f"Scenario herd size used: {herd_size}.")

    decision["scenario_notes"] = notes
    return decision
