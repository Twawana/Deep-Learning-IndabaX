"""
Grazing pressure tool — evaluate farmer herd inputs against available pasture data.
"""

from __future__ import annotations

from typing import Any, Optional

from services.grazing_service import assess_grazing
from tools.pasture_tool import get_pasture_data

TOOL_DESCRIPTION = (
    "Evaluates herd pressure against pasture indicators and carrying capacity "
    "(ha per LSU from the synthetic dataset when available)."
)


def calculate_grazing_pressure(
    location: str,
    *,
    herd_size: Optional[int] = None,
    animal_type: Optional[str] = None,
    carrying_capacity: Optional[float] = None,
    farm_size_ha: Optional[float] = None,
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
            farm_size_ha=farm_size_ha,
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
    nearby = pasture.get("nearby_synthetic") or {}

    ha_per_lsu = metrics.get("carrying_capacity_ha_per_lsu")
    density = metrics.get("livestock_density_lsu_per_ha")
    grazing_label = metrics.get("grazing_pressure_label")
    browsing_label = metrics.get("browsing_pressure_label")

    # Fuse Lacuna field hit with nearby synthetic capacity/NDVI/tenure metrics
    if ha_per_lsu is None and nearby.get("found"):
        ha_per_lsu = nearby.get("carrying_capacity_ha_per_lsu")
    if density is None and nearby.get("found"):
        density = nearby.get("livestock_density_lsu_per_ha")
    if not grazing_label and nearby.get("found"):
        grazing_label = nearby.get("grazing_pressure_label")
    if not browsing_label and nearby.get("found"):
        browsing_label = nearby.get("browsing_pressure_label")

    result = assess_grazing(
        herd_size=herd_size,
        animal_type=animal,
        vegetation_cover=metrics.get("vegetation_cover"),
        biomass=metrics.get("biomass"),
        bush_encroachment=metrics.get("bush_encroachment"),
        recorded_livestock_count=metrics.get("grazing_pressure_recorded"),
        carrying_capacity=carrying_capacity,
        carrying_capacity_ha_per_lsu=ha_per_lsu,
        farm_size_ha=farm_size_ha,
        livestock_density_lsu_per_ha=density,
        grazing_pressure_label=grazing_label,
        browsing_pressure_label=browsing_label,
    )
    extra_limits: list[str] = list(pasture.get("limitations") or [])
    if nearby.get("found") and metrics.get("carrying_capacity_ha_per_lsu") is None:
        extra_limits.append(
            nearby.get("note")
            or "Carrying capacity drawn from nearby synthetic sites (not the Lacuna field plot itself)."
        )
    if animal and animal not in {"cattle", "mixed"}:
        extra_limits.append(
            f"Animal type '{animal}' noted; LSU conversion is approximate "
            "(cattle≈1.0, goats/sheep≈0.15)."
        )
    result["limitations"] = list(dict.fromkeys((result.get("limitations") or []) + extra_limits))
    if result["confidence"] == "high" and pasture.get("confidence") != "high":
        result["confidence"] = pasture.get("confidence") or "medium"

    result["location"] = location
    result["pasture_found"] = True
    result["observation_date"] = pasture.get("observation_date")
    result["nearby_synthetic"] = nearby if nearby.get("found") else None
    return result
