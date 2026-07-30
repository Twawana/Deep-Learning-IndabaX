"""
Tool Executor — run only tools selected by the planner.

Tools return facts. Never recommendations.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from tools.compare_tool import compare_locations
from tools.grazing_tool import calculate_grazing_pressure
from tools.history_tool import compare_to_prior_year
from tools.pasture_tool import get_pasture_data
from tools.scenario_tool import run_what_if_scenario
from tools.stocking_tool import estimate_safe_stocking
from tools.tenure_tool import compare_tenure_nearby
from tools.weather_tool import get_weather

logger = logging.getLogger("in_vision.tools")


def execute_tools(
    tool_names: list[str],
    *,
    message: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Execute selected tools; return map name -> result + timing metadata."""
    known = context.get("known") or {}
    location = known.get("location") or "Gobabis"
    herd = known.get("herd_size")
    animal = known.get("livestock_type") or "cattle"
    farm_ha = known.get("farm_size_ha")
    tenure = known.get("land_tenure")
    lat = known.get("lat")
    lon = known.get("lon")

    results: dict[str, Any] = {}
    traces: list[dict[str, Any]] = []

    for name in tool_names:
        t0 = time.perf_counter()
        try:
            data = _run_one(
                name,
                message=message,
                location=location,
                herd=herd,
                animal=animal,
                farm_ha=farm_ha,
                tenure=tenure,
                lat=lat,
                lon=lon,
                pasture=results.get("get_pasture_data"),
            )
            ms = int((time.perf_counter() - t0) * 1000)
            results[name] = data
            traces.append(
                {
                    "name": name,
                    "summary": _summary(name, data),
                    "ms": ms,
                    "ok": True,
                }
            )
            logger.info("tool %s ok in %sms", name, ms)
        except Exception as exc:  # noqa: BLE001 — surface soft failure to advisor
            ms = int((time.perf_counter() - t0) * 1000)
            results[name] = {"found": False, "error": str(exc)}
            traces.append(
                {
                    "name": name,
                    "summary": f"failed: {exc}",
                    "ms": ms,
                    "ok": False,
                }
            )
            logger.warning("tool %s failed: %s", name, exc)

    return {"results": results, "traces": traces}


def _run_one(
    name: str,
    *,
    message: str,
    location: str,
    herd: Optional[int],
    animal: str,
    farm_ha: Optional[float],
    tenure: Optional[str],
    lat: Optional[float],
    lon: Optional[float],
    pasture: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if name == "get_pasture_data":
        return get_pasture_data(location)
    if name == "get_weather":
        return get_weather(location, latitude=lat, longitude=lon)
    if name == "calculate_grazing_pressure":
        return calculate_grazing_pressure(
            location,
            herd_size=herd,
            animal_type=animal,
            farm_size_ha=farm_ha,
            pasture_data=pasture,
        )
    if name == "estimate_safe_stocking":
        return estimate_safe_stocking(
            location,
            herd_size=herd,
            animal_type=animal,
            farm_size_ha=farm_ha,
            pasture_data=pasture,
        )
    if name == "compare_to_prior_year":
        return compare_to_prior_year(location)
    if name == "compare_tenure_nearby":
        return compare_tenure_nearby(
            location, land_tenure=tenure, latitude=lat, longitude=lon
        )
    if name == "run_what_if_scenario":
        return run_what_if_scenario(
            location,
            message,
            current_herd_size=herd,
            livestock_type=animal,
            land_tenure=tenure,
            farm_size_ha=farm_ha,
        )
    if name == "compare_locations":
        # Best-effort: parse "A and B" / "A vs B"
        a, b = _split_compare(message, location)
        return compare_locations(a, b)
    raise ValueError(f"Unknown tool: {name}")


def _split_compare(message: str, default_location: str) -> tuple[str, str]:
    import re

    text = message or ""
    m = re.search(
        r"compare\s+([A-Za-z][\w\s\-]+?)\s+(?:and|vs\.?|versus|with)\s+([A-Za-z][\w\s\-]+)",
        text,
        re.I,
    )
    if m:
        return m.group(1).strip(" ?.!"), m.group(2).strip(" ?.!")
    m2 = re.search(
        r"([A-Za-z][\w\s\-]+?)\s+(?:vs\.?|versus)\s+([A-Za-z][\w\s\-]+)",
        text,
        re.I,
    )
    if m2:
        return m2.group(1).strip(" ?.!"), m2.group(2).strip(" ?.!")
    return default_location, "Outjo"


def _summary(name: str, data: dict[str, Any]) -> str:
    if not data:
        return name
    if data.get("error"):
        return f"{name}: error"
    if name == "get_pasture_data":
        return f"pasture found={data.get('found')}"
    if name == "get_weather":
        return f"weather found={data.get('found')}"
    if name == "calculate_grazing_pressure":
        return f"risk={data.get('grazing_risk')}"
    if name == "estimate_safe_stocking":
        return f"stocking={data.get('status')}"
    if name == "run_what_if_scenario":
        return f"scenario found={data.get('found')}"
    if name == "compare_locations":
        return "compare camps"
    return name
