"""
In Vision reasoning pipeline.

User → Intent → Context → Tool Plan → Execute → Evidence → Decide → Advise

Planner decides tools. Executor returns facts. Advisor writes the farmer reply.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from agent.context_manager import resolve_context
from agent.decision_engine import decide_response_shape
from agent.evidence_builder import build_evidence
from agent.intent_classifier import classify_intent
from agent.response_generator import generate_response
from agent.tool_executor import execute_tools
from agent.tool_planner import plan_tools

logger = logging.getLogger("in_vision.pipeline")


def run_pipeline(
    *,
    message: str,
    location: str,
    tier: str = "free",
    herd_size: Optional[int] = None,
    livestock_type: Optional[str] = None,
    farm_size_ha: Optional[float] = None,
    land_tenure: Optional[str] = None,
    farm_notes: Optional[str] = None,
    farmer_name: Optional[str] = None,
    farm_name: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    history: Optional[list[dict[str, Any]]] = None,
    resolve_notes: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Full Planner → Executor → Advisor pass.

    Returns a payload ready for build_chat_response / UI.
    """
    history = history or []
    resolve_notes = list(resolve_notes or [])

    # 1) Intent Analyzer
    intent_info = classify_intent(message, history=history)
    logger.info("intent=%s wants_rec=%s", intent_info.get("intent"), intent_info.get("wants_recommendation"))

    # 2) Context & Memory Resolver
    context = resolve_context(
        message=message,
        location=location,
        herd_size=herd_size,
        livestock_type=livestock_type,
        farm_size_ha=farm_size_ha,
        land_tenure=land_tenure,
        farm_notes=farm_notes,
        farmer_name=farmer_name,
        farm_name=farm_name,
        lat=lat,
        lon=lon,
        history=history,
    )

    # 3) Tool Planner
    plan = plan_tools(intent_info, context, message)
    logger.info(
        "plan tools=%s strategy=%s clarify=%s",
        plan.get("tools"),
        plan.get("strategy"),
        plan.get("ask_clarification"),
    )

    # 4) Tool Executor (only selected tools)
    tool_bundle = execute_tools(plan.get("tools") or [], message=message, context=context)

    # 5) Evidence Synthesizer
    evidence = build_evidence(
        intent_info=intent_info,
        context=context,
        plan=plan,
        tool_bundle=tool_bundle,
    )
    evidence["_traces"] = tool_bundle.get("traces") or []

    # 6) Decision Engine (internal reasoning object — not shown raw)
    reasoning = decide_response_shape(
        intent_info=intent_info, plan=plan, evidence=evidence
    )
    reasoning["tools_used"] = [
        t["name"] for t in (tool_bundle.get("traces") or []) if t.get("ok")
    ]

    # 7) Natural Response Generator (Advisor)
    advice = generate_response(
        message=message,
        tier=tier,
        intent_info=intent_info,
        reasoning=reasoning,
        evidence=evidence,
        history=history,
    )

    results = evidence.get("raw_results") or {}
    include_decision = bool(reasoning.get("include_decision_card"))

    limitations = list(
        dict.fromkeys(
            resolve_notes
            + list(evidence.get("uncertainties") or [])
        )
    )

    pasture = results.get("get_pasture_data") or {}
    weather = results.get("get_weather") or {}
    grazing = results.get("calculate_grazing_pressure") or {}

    return {
        "ok": bool(advice.get("ok") and advice.get("text")),
        "text": advice.get("text"),
        "model": advice.get("model"),
        "assistant": advice.get("assistant"),
        "error": advice.get("error"),
        "intent": intent_info,
        "plan": plan,
        "reasoning": reasoning,
        "evidence": evidence,
        "tools_used": tool_bundle.get("traces") or [],
        "tool_results": results,
        "include_decision": include_decision,
        "conversation_mode": (
            "farm"
            if intent_info.get("intent")
            not in {"greeting", "chitchat", "off_topic"}
            else intent_info.get("intent")
        ),
        "advisor_payload": {
            "pasture_data": pasture,
            "weather_data": weather,
            "grazing_assessment": grazing,
            "stocking": results.get("estimate_safe_stocking"),
            "year_over_year": results.get("compare_to_prior_year"),
            "tenure_peers": results.get("compare_tenure_nearby"),
            "scenario": results.get("run_what_if_scenario"),
            "comparison": results.get("compare_locations"),
            "intents": [intent_info.get("intent")],
            "intent_paragraphs": [],
            "limitations": limitations,
            "confidence": (
                grazing.get("confidence")
                or pasture.get("confidence")
                or weather.get("confidence")
                or intent_info.get("confidence")
                or "medium"
            ),
        },
        "known_context": context.get("known") or {},
    }
