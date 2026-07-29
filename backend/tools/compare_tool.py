"""
Comparison tool — compare grazing conditions between two locations.

Compares measured pasture indicators; does not invent rankings beyond available metrics.
"""

from __future__ import annotations

from typing import Any, Optional

from models.schemas import CompareResponse
from services.transparency import confidence_from_limitations, merge_limitations
from tools.pasture_tool import get_pasture_data

TOOL_DESCRIPTION = (
    "Compares grazing conditions between two Namibian locations "
    "using processed pasture metrics (vegetation cover, biomass, bush encroachment)."
)

METRIC_KEYS = ("vegetation_cover", "biomass", "bush_encroachment", "cover_bare_ground_pct")


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return round(float(a) - float(b), 2)


def compare_locations(location_a: str, location_b: str) -> dict[str, Any]:
    """
    Compare pasture indicators between two locations.

    Args:
        location_a: First location query.
        location_b: Second location query.

    Returns:
        CompareResponse-compatible JSON with side-by-side metrics and deltas.
    """
    a = get_pasture_data(location_a)
    b = get_pasture_data(location_b)

    limitations = merge_limitations(
        a.get("limitations") or [],
        b.get("limitations") or [],
    )

    if not a.get("found") and not b.get("found"):
        return CompareResponse(
            found=False,
            location_a=a,
            location_b=b,
            message="Neither location was found",
            limitations=merge_limitations(limitations, ["Neither location was found"]),
            confidence="low",
        ).model_dump()

    if not a.get("found") or not b.get("found"):
        missing = location_a if not a.get("found") else location_b
        limitations.append(f"Location not found: {missing}")
        return CompareResponse(
            found=False,
            location_a=a,
            location_b=b,
            message=f"Location not found: {missing}",
            limitations=limitations,
            confidence="low",
        ).model_dump()

    pa = a.get("pasture") or {}
    pb = b.get("pasture") or {}
    deltas = {key: _delta(pa.get(key), pb.get(key)) for key in METRIC_KEYS}

    # Higher vegetation_cover / biomass generally better for grazing; higher bush / bare often worse
    notes: list[str] = []
    if deltas.get("vegetation_cover") is not None:
        if deltas["vegetation_cover"] > 0:
            notes.append(f"{location_a} has higher mean vegetation cover than {location_b}")
        elif deltas["vegetation_cover"] < 0:
            notes.append(f"{location_b} has higher mean vegetation cover than {location_a}")
        else:
            notes.append("Mean vegetation cover is similar between locations")

    if deltas.get("biomass") is not None:
        if deltas["biomass"] > 0:
            notes.append(f"{location_a} has higher mean biomass than {location_b}")
        elif deltas["biomass"] < 0:
            notes.append(f"{location_b} has higher mean biomass than {location_a}")

    if deltas.get("bush_encroachment") is not None:
        if deltas["bush_encroachment"] > 0:
            notes.append(f"{location_a} has higher bush/woody presence than {location_b}")
        elif deltas["bush_encroachment"] < 0:
            notes.append(f"{location_b} has higher bush/woody presence than {location_a}")

    available_deltas = [v for v in deltas.values() if v is not None]
    if not available_deltas:
        limitations.append("No overlapping numeric pasture metrics available for comparison")

    confidence = confidence_from_limitations(limitations, high_max=1, medium_max=4)
    if confidence == "high":
        confidence = "medium"

    return CompareResponse(
        found=True,
        location_a={
            "location": a.get("location"),
            "sites": a.get("sites"),
            "pasture": pa,
            "observation_date": a.get("observation_date"),
            "confidence": a.get("confidence"),
        },
        location_b={
            "location": b.get("location"),
            "sites": b.get("sites"),
            "pasture": pb,
            "observation_date": b.get("observation_date"),
            "confidence": b.get("confidence"),
        },
        comparison={
            "deltas_a_minus_b": deltas,
            "notes": notes,
            "metric_preference_notes": [
                "Higher vegetation_cover and biomass generally indicate more forage signal",
                "Higher bush_encroachment and bare ground generally indicate more woody/bare pressure",
            ],
        },
        limitations=limitations,
        confidence=confidence,  # type: ignore[arg-type]
    ).model_dump()
