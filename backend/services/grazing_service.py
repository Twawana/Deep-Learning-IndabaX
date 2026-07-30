"""
Grazing assessment — combine farmer herd inputs with available pasture measurements.

Carrying capacity from synthetic_v2 is hectares per LSU (ha/LSU), not max head count.
When capacity is unavailable, confidence stays low/medium and limitations are listed.
"""

from __future__ import annotations

from typing import Any, Optional

LSU_FACTORS = {
    "cattle": 1.0,
    "cow": 1.0,
    "goat": 0.15,
    "goats": 0.15,
    "sheep": 0.15,
    "mixed": 0.7,
    "other": 0.7,
}


def _to_lsu(herd_size: Optional[int], animal_type: Optional[str]) -> Optional[float]:
    if herd_size is None:
        return None
    factor = LSU_FACTORS.get((animal_type or "cattle").strip().lower(), 0.7)
    return float(herd_size) * factor


def _biomass_low(biomass: Optional[float]) -> bool:
    if biomass is None:
        return False
    # Synthetic grass biomass is kg/ha (often 200+); Lacuna field biomass is smaller.
    if biomass >= 200:
        return biomass < 450
    return biomass < 50


def _biomass_high(biomass: Optional[float]) -> bool:
    if biomass is None:
        return False
    if biomass >= 200:
        return biomass >= 900
    return biomass >= 150


def assess_grazing(
    *,
    herd_size: Optional[int] = None,
    animal_type: Optional[str] = None,
    vegetation_cover: Optional[float] = None,
    biomass: Optional[float] = None,
    bush_encroachment: Optional[float] = None,
    recorded_livestock_count: Optional[float] = None,
    carrying_capacity: Optional[float] = None,
    carrying_capacity_ha_per_lsu: Optional[float] = None,
    farm_size_ha: Optional[float] = None,
    livestock_density_lsu_per_ha: Optional[float] = None,
    grazing_pressure_label: Optional[str] = None,
    browsing_pressure_label: Optional[str] = None,
) -> dict[str, Any]:
    """
    Evaluate grazing pressure context for the advisor.

    Prefer carrying_capacity_ha_per_lsu (+ optional farm_size_ha / herd LSU).
    Legacy carrying_capacity (max head) is only used if ha/LSU is missing.
    """
    limitations: list[str] = []
    signals: list[str] = []

    ha_per_lsu = carrying_capacity_ha_per_lsu
    if ha_per_lsu is None and carrying_capacity is not None and farm_size_ha:
        # Interpret legacy value cautiously only when it looks like ha/LSU (small number)
        if 0 < float(carrying_capacity) < 50:
            ha_per_lsu = float(carrying_capacity)

    if ha_per_lsu is None and carrying_capacity is None:
        limitations.append("Carrying capacity (ha/LSU) unavailable in dataset")

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

    if vegetation_cover is not None:
        if vegetation_cover < 15:
            signals.append("Low vegetation cover relative to other sites in this dataset")
        elif vegetation_cover >= 35:
            signals.append("Moderate-to-higher vegetation cover relative to other sites in this dataset")

    if _biomass_low(biomass):
        signals.append("Low biomass reading in available measurements")
    elif _biomass_high(biomass):
        signals.append("Higher biomass reading in available measurements")

    if bush_encroachment is not None and bush_encroachment >= 25:
        signals.append("Elevated woody/bush presence relative to forage cover signals")

    label = (grazing_pressure_label or "").strip().lower()
    if label == "high":
        signals.append("Dataset grazing-pressure label is High")
    elif label == "moderate":
        signals.append("Dataset grazing-pressure label is Moderate")
    elif label == "low":
        signals.append("Dataset grazing-pressure label is Low")

    browse = (browsing_pressure_label or "").strip().lower()
    if browse in {"high", "severe"}:
        signals.append("Dataset browsing-pressure label is elevated (woody browse pressure)")

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

    grazing_risk = "unknown"
    reason = "Insufficient measured data to assess grazing pressure"
    stocking: dict[str, Any] = {}

    herd_lsu = _to_lsu(herd_size, animal)
    recommended_density = (1.0 / float(ha_per_lsu)) if ha_per_lsu and ha_per_lsu > 0 else None

    if ha_per_lsu and ha_per_lsu > 0:
        stocking["carrying_capacity_ha_per_lsu"] = round(float(ha_per_lsu), 2)
        stocking["recommended_lsu_per_ha"] = (
            round(recommended_density, 4) if recommended_density else None
        )
        if herd_lsu is not None:
            required_ha = herd_lsu * float(ha_per_lsu)
            stocking["herd_lsu"] = round(herd_lsu, 2)
            stocking["required_ha_for_herd"] = round(required_ha, 1)
            if farm_size_ha and farm_size_ha > 0:
                load = required_ha / float(farm_size_ha)
                stocking["farm_size_ha"] = float(farm_size_ha)
                stocking["load_ratio"] = round(load, 2)
                if load >= 1.2:
                    grazing_risk = "high"
                    reason = (
                        f"Herd (~{herd_lsu:.0f} LSU) needs about {required_ha:.0f} ha at "
                        f"{ha_per_lsu:.1f} ha/LSU, but camp size is {farm_size_ha:.0f} ha"
                    )
                elif load >= 0.85:
                    grazing_risk = "medium"
                    reason = (
                        f"Herd (~{herd_lsu:.0f} LSU) is near capacity for a {farm_size_ha:.0f} ha camp "
                        f"at {ha_per_lsu:.1f} ha/LSU"
                    )
                else:
                    grazing_risk = "low"
                    reason = (
                        f"Herd (~{herd_lsu:.0f} LSU) fits within ~{farm_size_ha:.0f} ha "
                        f"at {ha_per_lsu:.1f} ha/LSU"
                    )
            else:
                grazing_risk = "medium" if label == "high" else "low" if label == "low" else "medium"
                reason = (
                    f"Safe rate about {ha_per_lsu:.1f} ha/LSU "
                    f"(~{(recommended_density or 0) * 100:.1f} LSU/100 ha); "
                    "add farm size for a head-count check"
                )
                limitations.append("Farm/camp size missing — capacity given as a rate only")

        elif livestock_density_lsu_per_ha is not None and recommended_density is not None:
            dens = float(livestock_density_lsu_per_ha)
            stocking["dataset_livestock_density_lsu_per_ha"] = dens
            if dens >= recommended_density * 1.2:
                grazing_risk = "high"
                reason = (
                    f"Dataset livestock density ({dens:.3f} LSU/ha) exceeds recommended "
                    f"~{recommended_density:.3f} LSU/ha for this carrying capacity"
                )
            elif dens >= recommended_density * 0.85:
                grazing_risk = "medium"
                reason = "Dataset livestock density approaches the recommended carrying rate"
            else:
                grazing_risk = "low"
                reason = "Dataset livestock density is within the recommended carrying rate"

        elif label:
            grazing_risk = {"high": "high", "moderate": "medium", "low": "low"}.get(label, "medium")
            reason = f"Using survey grazing-pressure label ({grazing_pressure_label}) with ha/LSU context"

    elif carrying_capacity is not None and herd_size is not None and carrying_capacity > 0:
        # Legacy path: treat as max head count only when ha/LSU unavailable
        load = herd_size / float(carrying_capacity)
        stocking["legacy_max_head"] = float(carrying_capacity)
        if load >= 1.2:
            grazing_risk = "high"
            reason = "Current herd size may exceed available grazing capacity"
        elif load >= 0.85:
            grazing_risk = "medium"
            reason = "Current herd size approaches available grazing capacity"
        else:
            grazing_risk = "low"
            reason = "Current herd size is within available grazing capacity"
        limitations.append(
            "Used legacy carrying_capacity as max head — prefer ha/LSU when available"
        )
    else:
        pressure_flags = 0
        if vegetation_cover is not None and vegetation_cover < 15:
            pressure_flags += 1
        if _biomass_low(biomass):
            pressure_flags += 1
        if herd_vs_recorded == "higher_than_recorded":
            pressure_flags += 1
        if bush_encroachment is not None and bush_encroachment >= 25 and (
            vegetation_cover is not None and vegetation_cover < 25
        ):
            pressure_flags += 1
        if label == "high":
            pressure_flags += 1

        relief_flags = 0
        if vegetation_cover is not None and vegetation_cover >= 35:
            relief_flags += 1
        if _biomass_high(biomass):
            relief_flags += 1
        if herd_vs_recorded == "lower_than_recorded":
            relief_flags += 1
        if label == "low":
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

    if ha_per_lsu is None and carrying_capacity is None:
        if len(limitations) >= 4 or grazing_risk == "unknown":
            confidence = "low"
        else:
            confidence = "medium"
    else:
        confidence = "high" if len(limitations) <= 2 else "medium"

    return {
        "grazing_risk": grazing_risk,
        "reason": reason,
        "confidence": confidence,
        "limitations": limitations,
        "signals": signals,
        "stocking": stocking,
        "inputs": {
            "herd_size": herd_size,
            "animal_type": animal,
            "vegetation_cover": vegetation_cover,
            "biomass": biomass,
            "bush_encroachment": bush_encroachment,
            "recorded_livestock_count": recorded_livestock_count,
            "carrying_capacity": carrying_capacity,
            "carrying_capacity_ha_per_lsu": ha_per_lsu,
            "farm_size_ha": farm_size_ha,
            "livestock_density_lsu_per_ha": livestock_density_lsu_per_ha,
            "grazing_pressure_label": grazing_pressure_label,
            "browsing_pressure_label": browsing_pressure_label,
            "herd_vs_recorded": herd_vs_recorded,
        },
    }
