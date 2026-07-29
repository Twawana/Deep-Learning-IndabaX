"""
Grazing assessment — combine farmer herd inputs with available pasture measurements.

Does not invent carrying capacity. When capacity is unavailable, confidence stays low/medium
and limitations are listed explicitly.
"""

from __future__ import annotations

from typing import Any, Optional


def assess_grazing(
    *,
    herd_size: Optional[int] = None,
    animal_type: Optional[str] = None,
    vegetation_cover: Optional[float] = None,
    biomass: Optional[float] = None,
    bush_encroachment: Optional[float] = None,
    recorded_livestock_count: Optional[float] = None,
    carrying_capacity: Optional[float] = None,
) -> dict[str, Any]:
    """
    Evaluate grazing pressure context for Gemini (not a final farmer answer).

    Returns grazing_risk, reason, confidence, limitations, and supporting signals.
    """
    limitations: list[str] = []
    signals: list[str] = []

    if carrying_capacity is None:
        limitations.append("Carrying capacity unavailable in dataset")

    if herd_size is None:
        limitations.append("Herd size not provided")

    if animal_type:
        animal = str(animal_type).strip().lower()
    else:
        animal = None
        limitations.append("Animal type not provided")

    if vegetation_cover is None:
        limitations.append("Vegetation cover measurement unavailable")
    if biomass is None:
        limitations.append("Biomass measurement unavailable")
    if bush_encroachment is None:
        limitations.append("Bush encroachment measurement unavailable")

    # Soft cover / biomass signals (measured values only — qualitative thresholds are transparent)
    if vegetation_cover is not None:
        if vegetation_cover < 15:
            signals.append("Low vegetation cover relative to other sites in this dataset")
        elif vegetation_cover >= 35:
            signals.append("Moderate-to-higher vegetation cover relative to other sites in this dataset")

    if biomass is not None:
        if biomass < 50:
            signals.append("Low biomass reading in available measurements")
        elif biomass >= 150:
            signals.append("Higher biomass reading in available measurements")

    if bush_encroachment is not None and bush_encroachment >= 25:
        signals.append("Elevated woody/bush presence relative to forage cover signals")

    # Compare farmer herd to historically recorded livestock on plots when both exist
    herd_vs_recorded: Optional[str] = None
    if herd_size is not None and recorded_livestock_count is not None:
        if recorded_livestock_count <= 0:
            limitations.append("Historical recorded livestock count is zero or missing detail")
        else:
            ratio = herd_size / float(recorded_livestock_count)
            if ratio >= 1.5:
                herd_vs_recorded = "higher_than_recorded"
                signals.append(
                    "Requested herd size is substantially higher than livestock counts "
                    "recorded at matching survey plots"
                )
            elif ratio <= 0.7:
                herd_vs_recorded = "lower_than_recorded"
                signals.append(
                    "Requested herd size is lower than livestock counts recorded at matching survey plots"
                )
            else:
                herd_vs_recorded = "similar_to_recorded"
                signals.append(
                    "Requested herd size is similar to livestock counts recorded at matching survey plots"
                )
    elif herd_size is not None and recorded_livestock_count is None:
        limitations.append("No historical livestock counts available for comparison")

    # Risk uses only available signals; without capacity, never claim precise overstocking
    grazing_risk = "unknown"
    reason = "Insufficient measured data to assess grazing pressure"

    if carrying_capacity is not None and herd_size is not None and carrying_capacity > 0:
        load = herd_size / float(carrying_capacity)
        if load >= 1.2:
            grazing_risk = "high"
            reason = "Current herd size may exceed available grazing capacity"
        elif load >= 0.85:
            grazing_risk = "medium"
            reason = "Current herd size approaches available grazing capacity"
        else:
            grazing_risk = "low"
            reason = "Current herd size is within available grazing capacity"
    else:
        # Capacity missing: derive a cautious qualitative risk from soft signals only
        pressure_flags = 0
        if vegetation_cover is not None and vegetation_cover < 15:
            pressure_flags += 1
        if biomass is not None and biomass < 50:
            pressure_flags += 1
        if herd_vs_recorded == "higher_than_recorded":
            pressure_flags += 1
        if bush_encroachment is not None and bush_encroachment >= 25 and (
            vegetation_cover is not None and vegetation_cover < 25
        ):
            pressure_flags += 1

        relief_flags = 0
        if vegetation_cover is not None and vegetation_cover >= 35:
            relief_flags += 1
        if biomass is not None and biomass >= 150:
            relief_flags += 1
        if herd_vs_recorded == "lower_than_recorded":
            relief_flags += 1

        if pressure_flags >= 2:
            grazing_risk = "high"
            reason = (
                "Available pasture indicators suggest elevated grazing pressure; "
                "carrying capacity is unavailable so this is an indicator-based estimate only"
            )
        elif relief_flags >= 2 and pressure_flags == 0:
            grazing_risk = "low"
            reason = (
                "Available pasture indicators do not show strong pressure signals; "
                "carrying capacity is unavailable so confidence remains limited"
            )
        elif pressure_flags == 1 or relief_flags == 1:
            grazing_risk = "medium"
            reason = (
                "Mixed or limited pasture indicators; "
                "carrying capacity unavailable - treat as provisional context for the AI advisor"
            )
        else:
            grazing_risk = "unknown"
            reason = "Carrying capacity unavailable and pasture indicators are incomplete"

    # Confidence: capacity missing is always at most medium
    if carrying_capacity is None:
        if len(limitations) >= 4 or grazing_risk == "unknown":
            confidence = "low"
        else:
            confidence = "medium"
    else:
        confidence = "high" if len(limitations) <= 1 else "medium"

    return {
        "grazing_risk": grazing_risk,
        "reason": reason,
        "confidence": confidence,
        "limitations": limitations,
        "signals": signals,
        "inputs": {
            "herd_size": herd_size,
            "animal_type": animal,
            "vegetation_cover": vegetation_cover,
            "biomass": biomass,
            "bush_encroachment": bush_encroachment,
            "recorded_livestock_count": recorded_livestock_count,
            "carrying_capacity": carrying_capacity,
            "herd_vs_recorded": herd_vs_recorded,
        },
    }
