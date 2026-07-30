"""
Grazing pressure tool — evaluate farmer herd inputs against available pasture data.

Evaluates herd pressure against available grazing information.
"""

from __future__ import annotations

from typing import Any, Optional

from services.grazing_service import assess_grazing
from tools.pasture_tool import get_pasture_data

TOOL_DESCRIPTION = (
    "Evaluates herd pressure against available grazing information "
    "(herd size, animal type, and measured pasture indicators). "
    "Does not invent carrying capacity."
)


def calculate_grazing_pressure(
    location: str,
    *,
    herd_size: Optional[int] = None,
    animal_type: Optional[str] = None,
    carrying_capacity: Optional[float] = None,
    pasture_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Calculate grazing pressure context for a location and optional herd details.

    Pass pasture_data to avoid a second dataset lookup when the caller already has it.
    """
    pasture = pasture_data if pasture_data is not None else get_pasture_data(location)
    animal = (animal_type or "").strip().lower() or None

    if not pasture.get("found"):
        result = assess_grazing(
            herd_size=herd_size,
            animal_type=animal,
            carrying_capacity=carrying_capacity,
        )
        result["limitations"] = list(
            dict.fromkeys(
                (result.get("limitations") or [])
                + ["Pasture location not found in processed dataset"]
            )
        )
        result["confidence"] = "low"
        result["grazing_risk"] = "unknown"
        result["reason"] = pasture.get("message") or "Region not found"
        result["location"] = location
        result["pasture_found"] = False
        return result

    metrics = pasture.get("pasture") or {}
    result = assess_grazing(
        herd_size=herd_size,
        animal_type=animal,
        vegetation_cover=metrics.get("vegetation_cover"),
        biomass=metrics.get("biomass"),
        bush_encroachment=metrics.get("bush_encroachment"),
        recorded_livestock_count=metrics.get("grazing_pressure_recorded"),
        carrying_capacity=carrying_capacity,
    )
    extra_limits: list[str] = list(pasture.get("limitations") or [])
    if animal and animal not in {"cattle", "mixed"}:
        extra_limits.append(
            f"Animal type '{animal}' noted, but risk heuristics are forage/cover based "
            "and not species-calibrated (no LSU conversion in dataset)."
        )
    result["limitations"] = list(dict.fromkeys((result.get("limitations") or []) + extra_limits))
    if result["confidence"] == "high" and pasture.get("confidence") != "high":
        result["confidence"] = pasture.get("confidence") or "medium"

    result["location"] = location
    result["pasture_found"] = True
    result["observation_date"] = pasture.get("observation_date")
    return result
