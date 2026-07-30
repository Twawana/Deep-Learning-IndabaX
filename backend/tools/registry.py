"""
Gemini-ready tool registry (descriptions + callables).

Do NOT call Gemini from this module — only expose interfaces the agent can bind later.
"""

from __future__ import annotations

from typing import Any, Callable

from tools.compare_tool import TOOL_DESCRIPTION as COMPARE_DESCRIPTION
from tools.compare_tool import compare_locations
from tools.grazing_tool import TOOL_DESCRIPTION as GRAZING_DESCRIPTION
from tools.grazing_tool import calculate_grazing_pressure
from tools.pasture_tool import TOOL_DESCRIPTION as PASTURE_DESCRIPTION
from tools.pasture_tool import get_pasture_data
from tools.weather_tool import TOOL_DESCRIPTION as WEATHER_DESCRIPTION
from tools.weather_tool import get_weather

ToolFn = Callable[..., dict[str, Any]]

GEMINI_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_pasture_data",
        "description": PASTURE_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Namibian location, research site, or ecoregion.",
                }
            },
            "required": ["location"],
        },
        "callable": get_pasture_data,
    },
    {
        "name": "get_weather",
        "description": WEATHER_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Namibian location used to resolve dataset coordinates.",
                }
            },
            "required": ["location"],
        },
        "callable": get_weather,
    },
    {
        "name": "calculate_grazing_pressure",
        "description": GRAZING_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "herd_size": {"type": "integer", "description": "Farmer-provided herd size."},
                "animal_type": {"type": "string", "description": "e.g. cattle, goats, sheep."},
            },
            "required": ["location"],
        },
        "callable": calculate_grazing_pressure,
    },
    {
        "name": "compare_locations",
        "description": COMPARE_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location_a": {"type": "string"},
                "location_b": {"type": "string"},
            },
            "required": ["location_a", "location_b"],
        },
        "callable": compare_locations,
    },
]


def list_tool_manifests() -> list[dict[str, Any]]:
    """Return tool schemas without Python callables (safe for API/docs)."""
    return [
        {k: v for k, v in tool.items() if k != "callable"}
        for tool in GEMINI_TOOLS
    ]
