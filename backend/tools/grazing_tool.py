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
) -> dict[str, Any]:
    """
    Calculate grazing pressure context for a location and optional herd details.

    Args:
        location: Namibian place / site / region.
        herd_size: Farmer-provided herd size.
        animal_type: e.g. cattle, goats, sheep.
        carrying_capacity: Only if known from an external source — never fabricated.

    Returns:
        JSON with grazing_risk, reason, confidence, limitations, and signals.
    """
    pasture = get_pasture_data(location)
    if not pasture.get("found"):
        result = assess_grazing(
            herd_size=herd_size,
            animal_type=animal_type,
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
        animal_type=animal_type,
        vegetation_cover=metrics.get("vegetation_cover"),
        biomass=metrics.get("biomass"),
        bush_encroachment=metrics.get("bush_encroachment"),
        recorded_livestock_count=metrics.get("grazing_pressure_recorded"),
        carrying_capacity=carrying_capacity,
    )
    result["limitations"] = list(
        dict.fromkeys((result.get("limitations") or []) + (pasture.get("limitations") or []))
    )
    if result["confidence"] == "high" and pasture.get("confidence") != "high":
        result["confidence"] = pasture.get("confidence") or "medium"

    result["location"] = location
    result["pasture_found"] = True
    result["observation_date"] = pasture.get("observation_date")
    return result
