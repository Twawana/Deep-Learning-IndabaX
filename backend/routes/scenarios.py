"""Scenario planner — explore what-if herd/rainfall/location decisions."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from services.scenario_service import execute_scenario

router = APIRouter(tags=["scenarios"])


class ScenarioRequest(BaseModel):
    location: str = Field(..., min_length=1)
    question: Optional[str] = Field(
        default=None,
        description="Free-form what-if question. Parsed when structured fields are omitted.",
    )
    land_tenure: Optional[str] = None
    current_herd_size: Optional[int] = None
    scenario_herd_size: Optional[int] = None
    assume_rain_mm: Optional[float] = None
    move_in_days: Optional[int] = None
    alternate_location: Optional[str] = None
    livestock_type: Optional[str] = "cattle"
    farm_size_ha: Optional[float] = None

    @field_validator("current_herd_size", "scenario_herd_size", "move_in_days", mode="before")
    @classmethod
    def empty_int(cls, value: Any) -> Any:
        if value == "" or value is None:
            return None
        return value

    @field_validator("assume_rain_mm", "farm_size_ha", mode="before")
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

    Prefer `question` for free-form farmer language. Structured fields still work
    for advanced clients. Does not invent vegetation growth.
    """
    location = body.location.strip()
    if not location:
        raise HTTPException(status_code=400, detail="Location is required")

    result = execute_scenario(
        location=location,
        question=body.question,
        land_tenure=body.land_tenure,
        current_herd_size=body.current_herd_size,
        scenario_herd_size=body.scenario_herd_size,
        assume_rain_mm=body.assume_rain_mm,
        move_in_days=body.move_in_days,
        alternate_location=body.alternate_location,
        livestock_type=body.livestock_type or "cattle",
        farm_size_ha=body.farm_size_ha,
    )
    if not result.get("current") and not body.alternate_location:
        # Soft check — execute_scenario still returns decisions even if pasture weak
        pass
    return result
