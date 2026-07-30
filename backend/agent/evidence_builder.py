"""
Evidence Synthesizer — one structured evidence object for the Advisor.
"""

from __future__ import annotations

from typing import Any


def build_evidence(
    *,
    intent_info: dict[str, Any],
    context: dict[str, Any],
    plan: dict[str, Any],
    tool_bundle: dict[str, Any],
) -> dict[str, Any]:
    results = tool_bundle.get("results") or {}
    known = context.get("known") or {}
    pasture = results.get("get_pasture_data") or {}
    weather = results.get("get_weather") or {}
    grazing = results.get("calculate_grazing_pressure") or {}
    stocking = results.get("estimate_safe_stocking") or {}
    yoy = results.get("compare_to_prior_year") or {}
    tenure = results.get("compare_tenure_nearby") or {}
    scenario = results.get("run_what_if_scenario") or {}
    compare = results.get("compare_locations") or {}

    uncertainties: list[str] = []
    for blob in (pasture, weather, grazing, stocking, yoy, tenure):
        for note in blob.get("limitations") or []:
            if note and note not in uncertainties:
                uncertainties.append(note)
    if scenario.get("disclaimer"):
        uncertainties.append(scenario["disclaimer"])

    evidence = {
        "intent": intent_info.get("intent"),
        "wants_recommendation": intent_info.get("wants_recommendation"),
        "plan_strategy": plan.get("strategy"),
        "known_context": {
            "region": known.get("location"),
            "herd_size": known.get("herd_size"),
            "livestock": known.get("livestock_type"),
            "farm_size_ha": known.get("farm_size_ha"),
            "land_tenure": known.get("land_tenure"),
        },
        "pasture": _slim_pasture(pasture),
        "rainfall": _slim_weather(weather),
        "grazing_pressure": grazing.get("grazing_risk") or grazing.get("summary"),
        "grazing": grazing or None,
        "carrying_capacity": stocking.get("carrying_capacity_ha_per_lsu")
        or pasture.get("carrying_capacity_ha_per_lsu"),
        "stocking": stocking or None,
        "year_over_year": yoy or None,
        "tenure_peers": tenure or None,
        "scenario": scenario or None,
        "comparison": compare or None,
        "uncertainties": uncertainties,
        "raw_results": results,
    }
    return evidence


def _slim_pasture(p: dict[str, Any]) -> dict[str, Any]:
    if not p:
        return {}
    return {
        "found": p.get("found"),
        "location": p.get("matched_location") or p.get("location"),
        "cover_pct": p.get("vegetation_cover") or p.get("cover_pct"),
        "ndvi": p.get("ndvi"),
        "biomass": p.get("biomass") or p.get("grass_biomass"),
        "bush": p.get("bush_encroachment") or p.get("bush_cover"),
        "confidence": p.get("confidence"),
        "message": p.get("message") or p.get("summary"),
    }


def _slim_weather(w: dict[str, Any]) -> dict[str, Any]:
    if not w:
        return {}
    return {
        "found": w.get("found"),
        "recent_rainfall_mm": w.get("recent_rainfall_mm") or w.get("rainfall_7d_mm"),
        "forecast_rainfall_mm": w.get("forecast_rainfall_mm") or w.get("forecast_7d_mm"),
        "confidence": w.get("confidence"),
        "message": w.get("message") or w.get("summary"),
        "location_used": w.get("location_used") or w.get("resolved_location"),
    }
