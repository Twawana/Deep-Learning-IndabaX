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
        or pasture.get("carrying_capacity_ha_per_lsu")
        or (pasture.get("pasture") or {}).get("carrying_capacity_ha_per_lsu"),
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
    nested = p.get("pasture") if isinstance(p.get("pasture"), dict) else {}
    cover = (
        p.get("vegetation_cover")
        or p.get("cover_pct")
        or nested.get("vegetation_cover")
    )
    ndvi = p.get("ndvi") if p.get("ndvi") is not None else nested.get("ndvi")
    biomass = (
        p.get("biomass")
        or p.get("grass_biomass")
        or nested.get("biomass")
        or nested.get("grass_biomass_kg_per_ha")
    )
    bush = (
        p.get("bush_encroachment")
        or p.get("bush_cover")
        or nested.get("bush_encroachment")
    )
    capacity = (
        p.get("carrying_capacity_ha_per_lsu")
        or nested.get("carrying_capacity_ha_per_lsu")
    )
    bare = nested.get("cover_bare_ground_pct")
    message = p.get("message") or p.get("summary")
    if not message and p.get("found"):
        bits = []
        if cover is not None:
            bits.append(f"vegetation cover about {float(cover):.0f}%")
        if ndvi is not None:
            bits.append(f"NDVI around {float(ndvi):.2f}")
        if biomass is not None:
            bits.append(f"biomass near {float(biomass):.0f} kg/ha")
        if bush is not None:
            bits.append(f"bush cover about {float(bush):.0f}%")
        if capacity is not None:
            bits.append(f"carrying capacity near {float(capacity):.1f} ha per LSU")
        if bare is not None:
            bits.append(f"bare ground about {float(bare):.0f}%")
        if bits:
            loc = p.get("matched_location") or p.get("location") or "this area"
            message = f"Around {loc}: " + "; ".join(bits) + "."
    return {
        "found": p.get("found"),
        "location": p.get("matched_location") or p.get("location") or p.get("match_value"),
        "cover_pct": cover,
        "ndvi": ndvi,
        "biomass": biomass,
        "bush": bush,
        "carrying_capacity_ha_per_lsu": capacity,
        "bare_ground_pct": bare,
        "confidence": p.get("confidence"),
        "message": message,
        "observation_date": p.get("observation_date"),
        "dataset_source": nested.get("dataset_source") or p.get("dataset_source"),
    }


def _slim_weather(w: dict[str, Any]) -> dict[str, Any]:
    if not w:
        return {}
    recent = w.get("recent_rainfall") if isinstance(w.get("recent_rainfall"), dict) else {}
    forecast = w.get("forecast") if isinstance(w.get("forecast"), dict) else {}
    recent_mm = (
        w.get("recent_rainfall_mm")
        or w.get("rainfall_7d_mm")
        or recent.get("total_precipitation_mm")
    )
    forecast_mm = (
        w.get("forecast_rainfall_mm")
        or w.get("forecast_7d_mm")
        or forecast.get("total_precipitation_mm")
    )
    recent_days = recent.get("days") or 7
    message = w.get("message") or w.get("summary")
    if not message and w.get("found"):
        bits = []
        if recent_mm is not None:
            bits.append(f"about {float(recent_mm):.1f} mm rain over the last {recent_days} days")
        if forecast_mm is not None:
            bits.append(f"forecast total near {float(forecast_mm):.1f} mm")
        if bits:
            loc = w.get("location") or w.get("match_value") or "this area"
            message = f"Weather for {loc}: " + "; ".join(bits) + "."
        elif w.get("source") == "offline-local":
            message = "Live weather unavailable while offline."
    return {
        "found": w.get("found"),
        "recent_rainfall_mm": recent_mm,
        "forecast_rainfall_mm": forecast_mm,
        "recent_days": recent_days,
        "confidence": w.get("confidence"),
        "message": message,
        "location_used": w.get("location_used") or w.get("resolved_location") or w.get("location"),
        "source": w.get("source"),
    }
