"""
Offline / no-Gemini advisor.

Understands the farmer's question with local intent rules, fetches the right
rows from the local advisory dataset (and related tools), then answers in
plain language — no LLM required.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from agent.context_manager import resolve_context
from agent.intent_classifier import classify_intent
from agent.tool_executor import execute_tools
from agent.tool_planner import plan_tools
from services.agent_router import detect_intents, needs_farm_tools
from services.connectivity import is_online
from services.decision_service import build_decision, question_aware_local_reply

logger = logging.getLogger("vision.offline")


def _enrich_plan_for_message(plan: dict[str, Any], message: str) -> dict[str, Any]:
    """Make sure bush / stocking / move questions pull the right local tools."""
    text = (message or "").lower()
    tools = list(plan.get("tools") or [])

    def add(name: str) -> None:
        if name not in tools:
            tools.append(name)

    # Always ground farm asks in pasture dataset when offline
    if needs_farm_tools(message) or tools:
        add("get_pasture_data")

    if any(k in text for k in ("bush", "encroach", "woody", "last year", "worse", "year ago")):
        add("compare_to_prior_year")
        add("get_pasture_data")

    if any(k in text for k in ("stocking", "carrying", "how many animal", "safe herd", "ha/lsu", "lsu")):
        add("estimate_safe_stocking")
        add("get_pasture_data")

    if any(
        k in text
        for k in (
            "overgraz",
            "grazing pressure",
            "should i move",
            "how long",
            "move my herd",
            "move the herd",
        )
    ):
        add("calculate_grazing_pressure")
        add("get_pasture_data")

    if any(k in text for k in ("communal", "commercial", "conservanc", "tenure")):
        add("compare_tenure_nearby")
        add("get_pasture_data")

    if any(k in text for k in ("compare", " versus ", " vs ", "which camp")):
        add("compare_locations")

    if any(k in text for k in ("what if", "suppose", "if i add", "if i reduce")):
        add("run_what_if_scenario")

    # Live weather only when online — offline we stay on the local dataset
    if is_online() and any(
        k in text for k in ("rain", "rainfall", "weather", "forecast", "drought", "how long", "dry")
    ):
        add("get_weather")
    else:
        tools = [t for t in tools if t != "get_weather"]

    plan = dict(plan)
    plan["tools"] = tools
    plan["strategy"] = plan.get("strategy") or "offline_local_nlu"
    return plan


def run_offline_advisor(
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
    Local NLU → tool plan → dataset tools → question-aware answer.

    Returns a payload compatible with build_chat_response(vision_override=...).
    """
    history = history or []
    resolve_notes = list(resolve_notes or [])
    online = is_online()
    mode = "online" if online else "offline"

    intent_info = classify_intent(message, history=history)
    intents = detect_intents(message)
    logger.info(
        "offline NLU intent=%s secondary=%s keywords=%s",
        intent_info.get("intent"),
        intent_info.get("secondary"),
        intents,
    )

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

    plan = plan_tools(intent_info, context, message)
    plan = _enrich_plan_for_message(plan, message)

    # Educational / off-topic with no tools
    if not plan.get("tools") and not needs_farm_tools(message, intents):
        from services.agent_router import conversational_reply, classify_conversation
        from agent.prompts import educational_fallback

        mode_c = classify_conversation(message)
        if mode_c in {"greeting", "chitchat", "off_topic"}:
            text = conversational_reply(
                mode=mode_c, farmer_name=farmer_name, location=location
            )
        else:
            text = educational_fallback(message, intent_info.get("intent") or "")
        return {
            "ok": True,
            "response": text,
            "reasoning": f"Offline NLU ({mode_c or intent_info.get('intent')}) — no dataset tools needed.",
            "model": None,
            "agent": "Vision",
            "mode": mode,
            "tools_used": [],
            "include_decision": False,
            "advisor_payload": {
                "intents": intents or [intent_info.get("intent")],
                "mode": mode,
                "limitations": resolve_notes
                + (["Offline: answering without live Gemini."] if not online else []),
            },
        }

    tool_bundle = execute_tools(plan.get("tools") or [], message=message, context=context)
    results = tool_bundle.get("results") or {}
    pasture = results.get("get_pasture_data") or {}
    weather = results.get("get_weather") or {}
    grazing = results.get("calculate_grazing_pressure") or {}
    stocking = results.get("estimate_safe_stocking") or {}
    yoy = results.get("compare_to_prior_year") or {}
    tenure = results.get("compare_tenure_nearby") or {}
    scenario = results.get("run_what_if_scenario") or {}
    comparison = results.get("compare_locations") or {}

    if not weather.get("found") and not online:
        weather = {
            "found": False,
            "skipped": True,
            "reason": "Offline — live weather API unavailable; using local dataset only.",
            "limitations": ["Offline: live rainfall/forecast not available."],
        }

    decision = build_decision(
        location=location,
        pasture_data=pasture,
        weather_data=weather if weather.get("found") else {"found": False},
        grazing=grazing,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )

    text = question_aware_local_reply(
        message=message,
        location=location,
        decision=decision,
        pasture_data=pasture,
        weather_data=weather,
        grazing=grazing,
        stocking=stocking,
        year_over_year=yoy,
        herd_size=herd_size,
    )

    # Append structured extras when the question needs them
    extras: list[str] = []
    if scenario.get("found") and scenario.get("farmer_summary"):
        extras.append(str(scenario["farmer_summary"]))
    if comparison.get("found") and (comparison.get("summary") or comparison.get("farmer_summary")):
        extras.append(str(comparison.get("summary") or comparison.get("farmer_summary")))
    if tenure.get("found") and tenure.get("summary"):
        extras.append(str(tenure["summary"]))
    if extras:
        for block in extras:
            if block and block not in text:
                text = f"{text}\n\n{block}"

    if not online:
        text = (
            f"{text}\n\n"
            "(Offline mode: I understood your question and used the local rangeland database. "
            "Live weather / Vision AI reconnect when you're back online.)"
        )

    limitations = list(
        dict.fromkeys(
            resolve_notes
            + (["Offline: local advisory dataset — no live Gemini or Open-Meteo."] if not online else [])
            + (pasture.get("limitations") or [])
            + (weather.get("limitations") or [])
            + (yoy.get("limitations") or [])
        )
    )

    traces = tool_bundle.get("traces") or []
    return {
        "ok": True,
        "response": text,
        "reasoning": (
            f"Offline NLU intent={intent_info.get('intent')}; "
            f"tools={[t.get('name') for t in traces if t.get('ok')]}"
        ),
        "model": None,
        "agent": "Vision",
        "mode": mode,
        "tools_used": traces,
        "include_decision": False,
        "advisor_payload": {
            "pasture_data": pasture,
            "weather_data": weather,
            "grazing_assessment": grazing,
            "stocking": stocking,
            "year_over_year": yoy,
            "tenure_peers": tenure,
            "scenario": scenario,
            "comparison": comparison,
            "intents": intents or [intent_info.get("intent")],
            "intent_paragraphs": [],
            "limitations": limitations,
            "mode": mode,
            "confidence": (
                grazing.get("confidence")
                or pasture.get("confidence")
                or yoy.get("confidence")
                or "medium"
            ),
        },
    }
