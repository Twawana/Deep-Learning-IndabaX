"""
Decision Engine — should we recommend, educate, clarify, or just report status?
"""

from __future__ import annotations

from typing import Any

from agent.intent_classifier import (
    INTENT_CHITCHAT,
    INTENT_COMPARISON,
    INTENT_DECISION,
    INTENT_DEFINITION,
    INTENT_EXPLANATION,
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
    SHAPE_CLARIFICATION,
    SHAPE_COMPARISON,
    SHAPE_CONVERSATION,
    SHAPE_EDUCATIONAL,
    SHAPE_RECOMMENDATION,
    SHAPE_SCENARIO,
    SHAPE_STATUS,
)


def decide_response_shape(
    *,
    intent_info: dict[str, Any],
    plan: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Internal reasoning object (not shown to the farmer).
    """
    intent = intent_info.get("intent")
    allow_rec = bool(plan.get("allow_recommendation"))
    ask = bool(plan.get("ask_clarification"))

    if intent in {INTENT_GREETING, INTENT_CHITCHAT, INTENT_OFF_TOPIC}:
        shape = SHAPE_CONVERSATION
    elif intent in {INTENT_DEFINITION, INTENT_EXPLANATION, INTENT_SEASONAL}:
        shape = SHAPE_EDUCATIONAL
    elif ask:
        shape = SHAPE_CLARIFICATION
    elif intent == INTENT_COMPARISON:
        shape = SHAPE_COMPARISON
    elif intent == INTENT_SCENARIO:
        shape = SHAPE_SCENARIO
    elif intent in {INTENT_DECISION, INTENT_HERD} and allow_rec:
        shape = SHAPE_RECOMMENDATION
    elif intent in {
        INTENT_PASTURE,
        INTENT_WEATHER,
        INTENT_RAINFALL,
        INTENT_YOY,
        INTENT_TENURE,
    }:
        shape = SHAPE_STATUS
    elif allow_rec and intent_info.get("wants_recommendation"):
        shape = SHAPE_RECOMMENDATION
    else:
        shape = SHAPE_EDUCATIONAL

    reasoning_notes = _notes(intent, shape, evidence, plan)

    return {
        "intent": intent,
        "confidence": intent_info.get("confidence") or "medium",
        "required_tools": list(plan.get("tools") or []),
        "tools_used": [
            t.get("name") for t in (evidence.get("_traces") or []) if t.get("ok")
        ]
        or list((evidence.get("raw_results") or {}).keys()),
        "missing_information": list(plan.get("clarification_focus") or []),
        "known_context": evidence.get("known_context") or {},
        "evidence_snapshot": {
            "pasture": evidence.get("pasture"),
            "rainfall": evidence.get("rainfall"),
            "grazing_pressure": evidence.get("grazing_pressure"),
            "carrying_capacity": evidence.get("carrying_capacity"),
        },
        "reasoning": reasoning_notes,
        "response_shape": shape,
        "include_decision_card": shape in {SHAPE_RECOMMENDATION, SHAPE_SCENARIO},
        "recommended_action": (
            "Provide grazing recommendation"
            if shape == SHAPE_RECOMMENDATION
            else (
                "Ask clarifying question"
                if shape == SHAPE_CLARIFICATION
                else "Answer without forcing a move recommendation"
            )
        ),
        "next_step": (
            "Ask for herd size."
            if shape == SHAPE_CLARIFICATION and "herd_size" in (plan.get("clarification_focus") or [])
            else "Respond in plain farmer language."
        ),
    }


def _notes(
    intent: str,
    shape: str,
    evidence: dict[str, Any],
    plan: dict[str, Any],
) -> list[str]:
    notes = [
        f"Intent classified as {intent}.",
        f"Response shape: {shape}.",
        f"Planner strategy: {plan.get('strategy')}.",
    ]
    pasture = evidence.get("pasture") or {}
    rain = evidence.get("rainfall") or {}
    if pasture.get("found"):
        notes.append("Pasture measurements are available for this area.")
    if rain.get("found"):
        notes.append("Live rainfall / forecast context is available.")
    if plan.get("ask_clarification"):
        notes.append(
            "Important herd/location details are missing — clarify before hard advice."
        )
    if shape != SHAPE_RECOMMENDATION:
        notes.append("Do not append Prepare to Move unless the farmer asked for advice.")
    return notes
