"""
Tool registry for Vision (Gemini agentic tool-calling).

Exposes schemas + Python callables. The LLM / planner decides which tools to invoke;
this module does not call Gemini itself.
"""

from __future__ import annotations

from typing import Any, Callable

from tools.compare_tool import TOOL_DESCRIPTION as COMPARE_DESCRIPTION
from tools.compare_tool import compare_locations
from tools.grazing_tool import TOOL_DESCRIPTION as GRAZING_DESCRIPTION
from tools.grazing_tool import calculate_grazing_pressure
from tools.history_tool import TOOL_DESCRIPTION as HISTORY_DESCRIPTION
from tools.history_tool import compare_to_prior_year
from tools.pasture_tool import TOOL_DESCRIPTION as PASTURE_DESCRIPTION
from tools.pasture_tool import get_pasture_data
from tools.scenario_tool import TOOL_DESCRIPTION as SCENARIO_DESCRIPTION
from tools.scenario_tool import run_what_if_scenario
from tools.stocking_tool import TOOL_DESCRIPTION as STOCKING_DESCRIPTION
from tools.stocking_tool import estimate_safe_stocking
from tools.tenure_tool import TOOL_DESCRIPTION as TENURE_DESCRIPTION
from tools.tenure_tool import compare_tenure_nearby
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
                    "description": "Namibian location, research site, political region, or ecoregion.",
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
                },
                "latitude": {
                    "type": "number",
                    "description": "Optional farm/town latitude for Open-Meteo.",
                },
                "longitude": {
                    "type": "number",
                    "description": "Optional farm/town longitude for Open-Meteo.",
                },
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
                "farm_size_ha": {"type": "number", "description": "Camp/farm size in hectares."},
            },
            "required": ["location"],
        },
        "callable": calculate_grazing_pressure,
    },
    {
        "name": "estimate_safe_stocking",
        "description": STOCKING_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "herd_size": {"type": "integer"},
                "animal_type": {"type": "string"},
                "farm_size_ha": {"type": "number"},
            },
            "required": ["location"],
        },
        "callable": estimate_safe_stocking,
    },
    {
        "name": "compare_to_prior_year",
        "description": HISTORY_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
        "callable": compare_to_prior_year,
    },
    {
        "name": "compare_tenure_nearby",
        "description": TENURE_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "land_tenure": {
                    "type": "string",
                    "description": "communal, commercial, or conservancy",
                },
            },
            "required": ["location"],
        },
        "callable": compare_tenure_nearby,
    },
    {
        "name": "run_what_if_scenario",
        "description": SCENARIO_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "question": {
                    "type": "string",
                    "description": "Free-form what-if question from the farmer.",
                },
                "current_herd_size": {"type": "integer"},
                "animal_type": {"type": "string"},
                "farm_size_ha": {"type": "number"},
                "land_tenure": {"type": "string"},
            },
            "required": ["location", "question"],
        },
        "callable": run_what_if_scenario,
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
