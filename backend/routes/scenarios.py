"""Scenario planner — explore what-if herd/rainfall/location decisions."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from services.decision_service import build_decision, scenario_decision
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import get_pasture_data
from tools.weather_tool import get_weather

router = APIRouter(tags=["scenarios"])


class ScenarioRequest(BaseModel):
    location: str = Field(..., min_length=1)
    land_tenure: Optional[str] = None
    current_herd_size: Optional[int] = None
    scenario_herd_size: Optional[int] = None
    assume_rain_mm: Optional[float] = None
    move_in_days: Optional[int] = None
    alternate_location: Optional[str] = None
    livestock_type: Optional[str] = "cattle"

    @field_validator("current_herd_size", "scenario_herd_size", "move_in_days", mode="before")
    @classmethod
    def empty_int(cls, value: Any) -> Any:
        if value == "" or value is None:
            return None
        return value

    @field_validator("assume_rain_mm", mode="before")
    @classmethod
    def empty_float(cls, value: Any) -> Any:
        if value == "" or value is None:
            return None
        return value


@router.post(
    "/scenarios",
    summary="Scenario planner (what-if grazing decisions)",
)
def run_scenario(body: ScenarioRequest) -> dict[str, Any]:
    """
    Compare current recommendation vs a scenario.

    Does not invent vegetation growth. Assumed rainfall only affects the decision
    narrative as a hypothetical overlay on the forecast window.
    """
    location = body.location.strip()
    pasture = get_pasture_data(location)
    weather = get_weather(location)
    animal = body.livestock_type or "cattle"

    if not pasture.get("found") and not body.alternate_location:
        raise HTTPException(status_code=404, detail=f"Location not found: {location}")

    current_grazing = calculate_grazing_pressure(
        location,
        herd_size=body.current_herd_size,
        animal_type=animal,
        pasture_data=pasture,
    )
    current = build_decision(
        location=location,
        pasture_data=pasture,
        weather_data=weather,
        grazing=current_grazing,
        land_tenure=body.land_tenure,
        herd_size=body.current_herd_size,
    )

    scenario_location = (body.alternate_location or location).strip()
    scenario_pasture = (
        get_pasture_data(scenario_location)
        if body.alternate_location
        else pasture
    )
    scenario_weather = (
        get_weather(scenario_location)
        if body.alternate_location
        else weather
    )
    scenario_herd = (
        body.scenario_herd_size
        if body.scenario_herd_size is not None
        else body.current_herd_size
    )
    scenario_grazing = calculate_grazing_pressure(
        scenario_location,
        herd_size=scenario_herd,
        animal_type=animal,
        pasture_data=scenario_pasture,
    )
    scenario = scenario_decision(
        location=scenario_location,
        pasture_data=scenario_pasture,
        weather_data=scenario_weather,
        grazing=scenario_grazing,
        land_tenure=body.land_tenure,
        herd_size=scenario_herd,
        assume_rain_mm=body.assume_rain_mm,
        move_in_days=body.move_in_days,
        note_prefix=(
            f"Comparing current conditions at {location} with a scenario"
            + (f" at {scenario_location}" if body.alternate_location else "")
            + "."
        ),
    )

    changed = current.get("action_priority") != scenario.get("action_priority")
    what_changed = []
    if changed:
        what_changed.append(
            f"Recommendation shifted from {current.get('headline')} to {scenario.get('headline')}."
        )
    else:
        what_changed.append(
            "Overall recommendation priority stayed the same under this scenario, "
            "though the supporting explanation may differ."
        )
    if body.scenario_herd_size is not None and body.current_herd_size is not None:
        if body.scenario_herd_size < body.current_herd_size:
            what_changed.append(
                "Reducing herd size lowers grazing pressure, which can allow available "
                "forage to last longer under current pasture conditions."
            )
        elif body.scenario_herd_size > body.current_herd_size:
            what_changed.append(
                "Increasing herd size raises grazing pressure and may shorten how long "
                "the camp can support livestock."
            )
    if body.assume_rain_mm is not None:
        what_changed.append(
            f"If about {body.assume_rain_mm} mm of rain occurred, recovery outlook improves "
            "in the scenario — this is not a guaranteed forecast."
        )
    if body.alternate_location:
        what_changed.append(
            f"The scenario uses pasture and weather evidence for {scenario_location} "
            f"instead of {location}."
        )
    if body.move_in_days is not None:
        what_changed.append(
            f"Planning focus is a move window of about {body.move_in_days} days."
        )

    return {
        "location": location,
        "scenario_location": scenario_location,
        "current": current,
        "scenario": scenario,
        "what_changed": what_changed,
        "disclaimer": (
            "Scenario-based guidance only — not a prediction engine. "
            "Rainfall assumptions do not invent vegetation growth."
        ),
    }
