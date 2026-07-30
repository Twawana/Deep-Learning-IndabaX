"""
Stocking / carrying-capacity tool using synthetic ha-per-LSU estimates.

Carrying capacity in synthetic_v2 is hectares needed per livestock unit (ha/LSU),
NOT a maximum head count.
"""

from __future__ import annotations

from typing import Any, Optional

from tools.pasture_tool import get_pasture_data

TOOL_DESCRIPTION = (
    "Estimates a safe stocking rate using carrying capacity (ha per LSU) from the "
    "rangeland dataset, optional farm size, and herd size. Explains overstocking clearly."
)

# Rough LSU factors for advisory language only (not species-calibrated science).
LSU_FACTORS = {
    "cattle": 1.0,
    "cow": 1.0,
    "ox": 1.0,
    "goat": 0.15,
    "goats": 0.15,
    "sheep": 0.15,
    "mixed": 0.7,
    "other": 0.7,
}


def _lsu(herd_size: Optional[int], animal_type: Optional[str]) -> Optional[float]:
    if herd_size is None:
        return None
    factor = LSU_FACTORS.get((animal_type or "cattle").strip().lower(), 0.7)
    return round(float(herd_size) * factor, 2)


def estimate_safe_stocking(
    location: str,
    *,
    herd_size: Optional[int] = None,
    animal_type: Optional[str] = None,
    farm_size_ha: Optional[float] = None,
    pasture_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    pasture = pasture_data if pasture_data is not None else get_pasture_data(location)
    if not pasture.get("found"):
        return {
            "found": False,
            "location": location,
            "message": pasture.get("message") or "Location not found",
            "limitations": ["Pasture lookup failed"],
        }

    metrics = pasture.get("pasture") or {}
    nearby = pasture.get("nearby_synthetic") or {}
    ha_per_lsu = metrics.get("carrying_capacity_ha_per_lsu")
    density = metrics.get("livestock_density_lsu_per_ha")
    source_note = metrics.get("dataset_source")

    if ha_per_lsu is None and nearby.get("found"):
        ha_per_lsu = nearby.get("carrying_capacity_ha_per_lsu")
        density = density if density is not None else nearby.get("livestock_density_lsu_per_ha")
        source_note = "nearby_synthetic"

    limitations: list[str] = []
    if ha_per_lsu is None:
        limitations.append(
            "No carrying capacity (ha/LSU) for this location — Lacuna field plots lack this field."
        )
    if farm_size_ha is None:
        limitations.append("Farm/camp size (ha) not provided — reporting rate only, not absolute head count.")

    herd_lsu = _lsu(herd_size, animal_type)
    recommended_density = round(1.0 / float(ha_per_lsu), 4) if ha_per_lsu and ha_per_lsu > 0 else None
    safe_head_on_farm = None
    required_ha = None
    load_ratio = None
    status = "unknown"
    advice = "Carrying capacity unavailable for a numeric stocking rate."

    if ha_per_lsu and ha_per_lsu > 0:
        advice = (
            f"Estimated land need is about {ha_per_lsu:.1f} hectares per livestock unit (LSU). "
            f"That is roughly {recommended_density:.3f} LSU per hectare "
            f"(~{recommended_density * 100:.1f} LSU per 100 ha)."
        )
        if farm_size_ha and farm_size_ha > 0 and recommended_density is not None:
            safe_lsu = farm_size_ha * recommended_density
            # Convert LSU back to cattle-equivalent head for farmer language
            factor = LSU_FACTORS.get((animal_type or "cattle").strip().lower(), 1.0) or 1.0
            safe_head_on_farm = int(max(0, round(safe_lsu / factor)))
            advice += (
                f" On a {farm_size_ha:.0f} ha camp, a cautious ceiling is about "
                f"{safe_head_on_farm} {(animal_type or 'cattle')} (approx.)."
            )

        if herd_lsu is not None and ha_per_lsu > 0:
            required_ha = round(herd_lsu * float(ha_per_lsu), 1)
            if farm_size_ha and farm_size_ha > 0:
                load_ratio = round(required_ha / float(farm_size_ha), 2)
                if load_ratio >= 1.2:
                    status = "overstocked"
                    advice += (
                        f" Your herd (~{herd_lsu} LSU) needs about {required_ha:.0f} ha "
                        f"but the camp is {farm_size_ha:.0f} ha — likely overstocked."
                    )
                elif load_ratio >= 0.85:
                    status = "near_capacity"
                    advice += (
                        f" Your herd (~{herd_lsu} LSU) is near capacity for {farm_size_ha:.0f} ha."
                    )
                else:
                    status = "within_capacity"
                    advice += (
                        f" Your herd (~{herd_lsu} LSU) looks within capacity for {farm_size_ha:.0f} ha "
                        f"(needs ~{required_ha:.0f} ha)."
                    )
            else:
                status = "rate_only"
                advice += f" Your herd (~{herd_lsu} LSU) would need about {required_ha:.0f} ha at this rate."

        if density is not None and recommended_density is not None:
            if density > recommended_density * 1.2:
                limitations.append(
                    f"Dataset livestock density ({density:.3f} LSU/ha) is above the "
                    f"recommended ~{recommended_density:.3f} LSU/ha for this area."
                )

    label = metrics.get("grazing_pressure_label") or nearby.get("grazing_pressure_label")
    if label:
        advice += f" Survey grazing pressure label nearby: {label}."

    return {
        "found": True,
        "location": location,
        "status": status,
        "carrying_capacity_ha_per_lsu": ha_per_lsu,
        "recommended_lsu_per_ha": recommended_density,
        "safe_head_on_farm": safe_head_on_farm,
        "required_ha_for_herd": required_ha,
        "load_ratio": load_ratio,
        "herd_lsu": herd_lsu,
        "farm_size_ha": farm_size_ha,
        "herd_size": herd_size,
        "animal_type": animal_type,
        "dataset_livestock_density_lsu_per_ha": density,
        "capacity_source": source_note,
        "advice": advice,
        "limitations": limitations
        + [
            "LSU conversion is approximate (cattle≈1.0, goats/sheep≈0.15).",
            "Always confirm stocking with local extension advice and veld condition on foot.",
        ],
    }
