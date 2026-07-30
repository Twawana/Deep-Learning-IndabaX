"""Shared what-if scenario execution used by /scenarios and the chat agent."""

from __future__ import annotations

from typing import Any, Optional

from services.decision_service import build_decision, scenario_decision
from services.scenario_parser import parse_scenario_question
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import get_pasture_data
from tools.weather_tool import get_weather


def execute_scenario(
    *,
    location: str,
    land_tenure: Optional[str] = None,
    current_herd_size: Optional[int] = None,
    scenario_herd_size: Optional[int] = None,
    assume_rain_mm: Optional[float] = None,
    move_in_days: Optional[int] = None,
    alternate_location: Optional[str] = None,
    livestock_type: Optional[str] = "cattle",
    farm_size_ha: Optional[float] = None,
    question: Optional[str] = None,
) -> dict[str, Any]:
    """
    Compare current recommendation vs a scenario.

    If `question` is provided, free-text knobs are parsed and merged
    (explicit numeric args still win when set).
    """
    parsed = None
    if question:
        parsed = parse_scenario_question(
            question,
            current_herd_size=current_herd_size,
            current_location=location,
        )
        if scenario_herd_size is None:
            scenario_herd_size = parsed.get("scenario_herd_size")
        if assume_rain_mm is None:
            assume_rain_mm = parsed.get("assume_rain_mm")
        if move_in_days is None:
            move_in_days = parsed.get("move_in_days")
        if not alternate_location:
            alternate_location = parsed.get("alternate_location")

    location = location.strip()
    pasture = get_pasture_data(location)
    weather = get_weather(location)
    animal = livestock_type or "cattle"

    current_grazing = calculate_grazing_pressure(
        location,
        herd_size=current_herd_size,
        animal_type=animal,
        farm_size_ha=farm_size_ha,
        pasture_data=pasture,
    )
    current = build_decision(
        location=location,
        pasture_data=pasture,
        weather_data=weather,
        grazing=current_grazing,
        land_tenure=land_tenure,
        herd_size=current_herd_size,
    )

    scenario_location = (alternate_location or location).strip()
    scenario_pasture = (
        get_pasture_data(scenario_location) if alternate_location else pasture
    )
    scenario_weather = (
        get_weather(scenario_location) if alternate_location else weather
    )
    scenario_herd = (
        scenario_herd_size if scenario_herd_size is not None else current_herd_size
    )
    scenario_grazing = calculate_grazing_pressure(
        scenario_location,
        herd_size=scenario_herd,
        animal_type=animal,
        farm_size_ha=farm_size_ha,
        pasture_data=scenario_pasture,
    )
    scenario = scenario_decision(
        location=scenario_location,
        pasture_data=scenario_pasture,
        weather_data=scenario_weather,
        grazing=scenario_grazing,
        land_tenure=land_tenure,
        herd_size=scenario_herd,
        assume_rain_mm=assume_rain_mm,
        move_in_days=move_in_days,
        note_prefix=(
            f"Comparing current conditions at {location} with a scenario"
            + (f" at {scenario_location}" if alternate_location else "")
            + "."
        ),
    )

    changed = current.get("action_priority") != scenario.get("action_priority")
    what_changed: list[str] = []
    if changed:
        what_changed.append(
            f"Recommendation shifted from {current.get('headline')} to {scenario.get('headline')}."
        )
    else:
        what_changed.append(
            "Overall recommendation priority stayed the same under this scenario, "
            "though the supporting explanation may differ."
        )
    if scenario_herd_size is not None and current_herd_size is not None:
        if scenario_herd_size < current_herd_size:
            what_changed.append(
                "Reducing herd size lowers grazing pressure, which can allow available "
                "forage to last longer under current pasture conditions."
            )
        elif scenario_herd_size > current_herd_size:
            what_changed.append(
                "Increasing herd size raises grazing pressure and may shorten how long "
                "the camp can support livestock."
            )
    if assume_rain_mm is not None:
        what_changed.append(
            f"If about {assume_rain_mm} mm of rain occurred, recovery outlook improves "
            "in the scenario — this is not a guaranteed forecast."
        )
    if alternate_location:
        what_changed.append(
            f"The scenario uses pasture and weather evidence for {scenario_location} "
            f"instead of {location}."
        )
    if move_in_days is not None:
        what_changed.append(
            f"Planning focus is a move window of about {move_in_days} days."
        )

    farmer_summary = _farmer_summary(
        question=question,
        parsed=parsed,
        current=current,
        scenario=scenario,
        what_changed=what_changed,
        location=location,
        scenario_location=scenario_location,
    )

    return {
        "found": True,
        "location": location,
        "scenario_location": scenario_location,
        "current": current,
        "scenario": scenario,
        "what_changed": what_changed,
        "parsed": parsed,
        "farmer_summary": farmer_summary,
        "disclaimer": (
            "Scenario-based guidance only — not a prediction engine. "
            "Rainfall assumptions do not invent vegetation growth. "
            "I explain what I assumed from your question so you can correct me."
        ),
    }


def _farmer_summary(
    *,
    question: Optional[str],
    parsed: Optional[dict[str, Any]],
    current: dict[str, Any],
    scenario: dict[str, Any],
    what_changed: list[str],
    location: str,
    scenario_location: str,
) -> str:
    parts: list[str] = []
    if parsed and parsed.get("understood"):
        parts.append(f"What I understood: {parsed['understood']}")
    parts.append(
        f"Today at {location}: {current.get('headline')} — "
        f"{current.get('recommended_action')}"
    )
    parts.append(
        f"Under your what-if"
        + (f" at {scenario_location}" if scenario_location != location else "")
        + f": {scenario.get('headline')} — {scenario.get('recommended_action')}"
    )
    if what_changed:
        parts.append("What changes: " + " ".join(what_changed[:3]))
    why = (scenario.get("explainer") or {}).get("why") or []
    if why:
        parts.append("Why: " + " ".join(str(w) for w in why[:2]))
    parts.append(
        "This is planning support from pasture + rainfall evidence — "
        "not a guaranteed forecast. Ask another way if I misunderstood."
    )
    return "\n\n".join(parts)
