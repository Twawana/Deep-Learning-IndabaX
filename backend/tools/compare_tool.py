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


def compare_locations(
    location_a: str,
    location_b: str,
    *,
    land_tenure: Optional[str] = None,
    herd_size: Optional[int] = None,
) -> dict[str, Any]:
    """
    Compare pasture indicators between two locations.

    Args:
        location_a: First location query.
        location_b: Second location query.

    Returns:
        CompareResponse-compatible JSON with side-by-side metrics, deltas,
        rainfall outlook, decision snippets, and a farmer-facing summary.
    """
    from services.decision_service import build_decision
    from tools.grazing_tool import calculate_grazing_pressure
    from tools.weather_tool import get_weather

    a = get_pasture_data(location_a)
    b = get_pasture_data(location_b)
    wa = get_weather(location_a)
    wb = get_weather(location_b)
    ga = calculate_grazing_pressure(
        location_a, herd_size=herd_size, pasture_data=a
    )
    gb = calculate_grazing_pressure(
        location_b, herd_size=herd_size, pasture_data=b
    )
    da = build_decision(
        location=location_a,
        pasture_data=a,
        weather_data=wa,
        grazing=ga,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )
    db = build_decision(
        location=location_b,
        pasture_data=b,
        weather_data=wb,
        grazing=gb,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )

    limitations = merge_limitations(
        a.get("limitations") or [],
        b.get("limitations") or [],
        wa.get("limitations") or [],
        wb.get("limitations") or [],
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

    # Farmer-facing summary (not a ranking invention — based on measured deltas + decisions)
    cover_delta = deltas.get("vegetation_cover") or 0
    bush_delta = deltas.get("bush_encroachment") or 0
    prefer_a = 0
    prefer_b = 0
    if cover_delta > 2:
        prefer_a += 1
    elif cover_delta < -2:
        prefer_b += 1
    if bush_delta < -2:
        prefer_a += 1
    elif bush_delta > 2:
        prefer_b += 1
    if da.get("action_priority") in {"stay", "monitor"} and db.get("action_priority") in {
        "move_soon",
        "move_now",
    }:
        prefer_a += 1
    if db.get("action_priority") in {"stay", "monitor"} and da.get("action_priority") in {
        "move_soon",
        "move_now",
    }:
        prefer_b += 1

    if prefer_a > prefer_b:
        farmer_summary = (
            f"Based on current conditions, {location_a} appears to offer healthier grazing "
            f"signals than {location_b}, with better vegetation cover and/or lower bush pressure. "
            f"{location_b} may benefit from a longer recovery period."
        )
    elif prefer_b > prefer_a:
        farmer_summary = (
            f"Based on current conditions, {location_b} appears to offer healthier grazing "
            f"signals than {location_a}. {location_a} is currently under greater grazing pressure "
            "and would likely benefit from more rest."
        )
    else:
        farmer_summary = (
            f"Based on available data, {location_a} and {location_b} look broadly similar. "
            "Walk both camps and weigh local water, access, and neighbour grazing pressure."
        )

    confidence = confidence_from_limitations(limitations, high_max=1, medium_max=4)
    if confidence == "high":
        confidence = "medium"

    payload = CompareResponse(
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
            "farmer_summary": farmer_summary,
            "decision_a": {
                "action_priority": da.get("action_priority"),
                "headline": da.get("headline"),
                "recommended_action": da.get("recommended_action"),
                "pasture_health": (da.get("pasture_health") or {}).get("label"),
                "rainfall_outlook": ((da.get("rainfall_impact") or {}).get("outlook") or "")[:180],
            },
            "decision_b": {
                "action_priority": db.get("action_priority"),
                "headline": db.get("headline"),
                "recommended_action": db.get("recommended_action"),
                "pasture_health": (db.get("pasture_health") or {}).get("label"),
                "rainfall_outlook": ((db.get("rainfall_impact") or {}).get("outlook") or "")[:180],
            },
        },
        limitations=limitations,
        confidence=confidence,  # type: ignore[arg-type]
    ).model_dump()
    payload["farmer_summary"] = farmer_summary
    payload["decision_a"] = da
    payload["decision_b"] = db
    return payload
