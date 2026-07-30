"""
Tool Planner — decide which tools (if any) are required.

Never auto-select every tool. Educational questions get none.
"""

from __future__ import annotations

from typing import Any

from agent.context_manager import missing_for_decision
from agent.intent_classifier import (
    INTENT_CHITCHAT,
    INTENT_COMPARISON,
    INTENT_DECISION,
    INTENT_DEFINITION,
    INTENT_EXPLANATION,
    INTENT_FARM_MGMT,
    INTENT_FOLLOW_UP,
    INTENT_GREETING,
    INTENT_HERD,
    INTENT_OFF_TOPIC,
    INTENT_PASTURE,
    INTENT_RAINFALL,
    INTENT_SCENARIO,
    INTENT_SEASONAL,
    INTENT_TENURE,
    INTENT_WEATHER,
    INTENT_YOY,
)


def plan_tools(
    intent_info: dict[str, Any],
    context: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    """
    Returns:
      tools: list[str]
      ask_clarification: bool
      clarification_focus: list[str]
      allow_recommendation: bool
      strategy: str
    """
    intent = intent_info.get("intent")
    wants_rec = bool(intent_info.get("wants_recommendation"))

    # No tools
    if intent in {
        INTENT_GREETING,
        INTENT_CHITCHAT,
        INTENT_OFF_TOPIC,
        INTENT_DEFINITION,
        INTENT_EXPLANATION,
        INTENT_SEASONAL,
    }:
        return {
            "tools": [],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "educate_or_converse",
        }

    if intent in {INTENT_WEATHER, INTENT_RAINFALL}:
        return {
            "tools": ["get_weather"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "weather_status",
        }

    if intent == INTENT_PASTURE:
        # Offline/heuristic path only — do not auto-attach weather.
        return {
            "tools": ["get_pasture_data"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "pasture_status",
        }

    if intent == INTENT_YOY:
        return {
            "tools": ["compare_to_prior_year", "get_pasture_data"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "trend",
        }

    # Keyword safety net — bush / stocking even if intent was coarse
    text_l = (message or "").lower()
    if any(k in text_l for k in ("bush", "encroach", "woody", "last year", "getting worse")):
        return {
            "tools": ["compare_to_prior_year", "get_pasture_data"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "bush_trend",
        }

    if intent == INTENT_TENURE:
        return {
            "tools": ["compare_tenure_nearby", "get_pasture_data"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "tenure",
        }

    if intent == INTENT_COMPARISON:
        return {
            "tools": ["compare_locations"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": False,
            "strategy": "compare",
        }

    if intent == INTENT_SCENARIO:
        return {
            "tools": ["run_what_if_scenario"],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": True,
            "strategy": "scenario",
        }

    if intent in {INTENT_DECISION, INTENT_HERD} or wants_rec:
        missing = missing_for_decision(context)
        # Heuristic fallback only (online path lets Gemini choose tools).
        # Start with pasture; add weather only if the question mentions rain/forecast.
        text = (message or "").lower()
        tools = ["get_pasture_data"]
        if any(
            k in text
            for k in (
                "rain",
                "rainfall",
                "weather",
                "forecast",
                "drought",
                "wet",
                "dry spell",
            )
        ):
            tools.append("get_weather")
        if "herd_size" not in missing:
            tools.extend(["calculate_grazing_pressure", "estimate_safe_stocking"])
        return {
            "tools": tools,
            "ask_clarification": "herd_size" in missing,
            "clarification_focus": missing,
            "allow_recommendation": "herd_size" not in missing,
            "strategy": "decision" if "herd_size" not in missing else "clarify_then_soft_status",
        }

    if intent in {INTENT_FOLLOW_UP, INTENT_FARM_MGMT}:
        # Light touch — pasture only unless they clearly asked to decide
        return {
            "tools": ["get_pasture_data"] if wants_rec else [],
            "ask_clarification": False,
            "clarification_focus": [],
            "allow_recommendation": wants_rec,
            "strategy": "light_followup",
        }

    return {
        "tools": [],
        "ask_clarification": False,
        "clarification_focus": [],
        "allow_recommendation": False,
        "strategy": "default_no_tools",
    }
