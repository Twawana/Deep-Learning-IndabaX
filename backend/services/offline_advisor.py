"""
Offline / no-Gemini advisor.

1) Scan the question for keywords
2) Fetch matching fields from the local advisory database
3) Answer with those facts only — never invent missing numbers
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from agent.context_manager import resolve_context
from agent.tool_executor import execute_tools
from services.agent_router import classify_conversation, conversational_reply, needs_farm_tools
from services.connectivity import is_online
from services.keyword_router import build_grounded_reply, match_keywords

logger = logging.getLogger("vision.offline")


def _tools_for_match(match: dict[str, Any], *, online: bool) -> list[str]:
    tools = list(match.get("tools") or [])
    if online:
        for topic in match.get("matched_topics") or []:
            for t in topic.get("online_tools") or []:
                if t not in tools:
                    tools.append(t)
    else:
        tools = [t for t in tools if t != "get_weather"]

    if match.get("understood") and "get_pasture_data" not in tools:
        tools.insert(0, "get_pasture_data")
    return tools


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
    """Keywords -> tools -> local DB fields -> grounded answer."""
    history = history or []
    resolve_notes = list(resolve_notes or [])
    online = is_online()
    mode = "online" if online else "offline"

    conv = classify_conversation(message)
    if conv in {"greeting", "chitchat", "off_topic"} and not needs_farm_tools(message):
        return {
            "ok": True,
            "response": conversational_reply(
                mode=conv, farmer_name=farmer_name, location=location
            ),
            "reasoning": f"Offline keyword router — conversation mode={conv}",
            "model": None,
            "agent": "Vision",
            "mode": mode,
            "tools_used": [],
            "include_decision": False,
            "advisor_payload": {
                "intents": [conv],
                "mode": mode,
                "limitations": resolve_notes,
            },
        }

    match = match_keywords(message)
    logger.info(
        "offline keywords=%s topics=%s tools=%s",
        match.get("matched_keywords"),
        [t["id"] for t in match.get("matched_topics") or []],
        match.get("tools"),
    )

    if not match.get("understood") and not needs_farm_tools(message):
        return {
            "ok": True,
            "response": (
                "I did not find farm keywords in that question, so I will not invent an answer.\n\n"
                "Try words like: pasture, bush, stocking, overgrazing, rainfall, move herd, "
                "last year, communal/commercial — I will pull those fields from the local database."
            ),
            "reasoning": "Offline keyword router — no farm keywords matched; refused to hallucinate",
            "model": None,
            "agent": "Vision",
            "mode": mode,
            "tools_used": [],
            "include_decision": False,
            "advisor_payload": {
                "intents": ["unclear"],
                "mode": mode,
                "matched_keywords": [],
                "limitations": resolve_notes,
            },
        }

    if not match.get("tools"):
        match = {
            **match,
            "understood": True,
            "tools": ["get_pasture_data"],
            "fields": [
                "vegetation_cover",
                "biomass",
                "bush_encroachment",
                "ndvi",
                "cover_bare_ground_pct",
            ],
            "matched_topics": match.get("matched_topics")
            or [
                {
                    "id": "pasture",
                    "label": "Pasture / veld condition",
                    "matched_keywords": ["(farm ask)"],
                    "fields": [
                        "vegetation_cover",
                        "biomass",
                        "bush_encroachment",
                        "ndvi",
                    ],
                    "tools": ["get_pasture_data"],
                    "online_tools": [],
                }
            ],
            "matched_keywords": match.get("matched_keywords") or ["(farm ask)"],
        }

    tools = _tools_for_match(match, online=online)
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

    tool_bundle = execute_tools(tools, message=message, context=context)
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
            "reason": "Offline — live weather unavailable.",
            "limitations": ["Offline: no live rainfall API."],
        }

    text = build_grounded_reply(
        message=message,
        location=location,
        match=match,
        pasture_data=pasture,
        year_over_year=yoy,
        stocking=stocking,
        grazing=grazing,
        tenure=tenure,
        scenario=scenario,
        comparison=comparison,
        weather_data=weather,
        online=online,
    )

    limitations = list(
        dict.fromkeys(
            resolve_notes
            + [
                "Grounded mode: only database (and live weather when online) — missing fields are listed, not invented."
            ]
            + (pasture.get("limitations") or [])
            + (yoy.get("limitations") or [])
        )
    )

    return {
        "ok": True,
        "response": text,
        "reasoning": (
            f"Keyword topics={[t['id'] for t in match.get('matched_topics') or []]}; "
            f"keywords={match.get('matched_keywords')}; tools={tools}; grounded=true"
        ),
        "model": None,
        "agent": "Vision",
        "mode": mode,
        "tools_used": tool_bundle.get("traces") or [],
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
            "intents": [t["id"] for t in match.get("matched_topics") or []],
            "matched_keywords": match.get("matched_keywords") or [],
            "intent_paragraphs": [],
            "limitations": limitations,
            "mode": mode,
            "confidence": pasture.get("confidence") or "medium",
        },
    }
