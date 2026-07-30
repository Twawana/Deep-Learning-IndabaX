"""
Lightweight intent router for Farmar chat (pre-Gemini).

Chooses which dataset tools to run based on the farmer's question so both
Lacuna and synthetic fields are used for the right hackathon questions.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from services.scenario_parser import is_scenario_question


def detect_intents(message: str) -> list[str]:
    text = (message or "").strip().lower()
    intents: list[str] = []

    def has(*patterns: str) -> bool:
        return any(re.search(p, text) for p in patterns)

    if is_scenario_question(text) or has(
        r"\bwhat\s*if\b",
        r"\bsuppose\b",
        r"\bscenario\b",
        r"\bif\s+i\s+(had|have|add|reduce|move|double|halve)\b",
    ):
        intents.append("scenario")

    if has(
        r"carrying\s*capacit",
        r"stocking",
        r"how many\s+(cattle|animals|goats|sheep)",
        r"safe\s+(herd|stock)",
        r"over\s*graz",
        r"overstock",
        r"lsu",
        r"ha\s*per",
    ):
        intents.append("stocking")

    if has(
        r"last\s+year",
        r"same\s+time",
        r"year\s+ago",
        r"compared?\s+to\s+last",
        r"worse\s+than",
        r"better\s+than\s+last",
        r"recovering",
        r"trend",
    ):
        intents.append("yoy")

    if has(
        r"bush\s+encroach",
        r"woody",
        r"bush\s+(getting|worse|better)",
        r"encroachment",
    ):
        intents.append("bush")
        if "yoy" not in intents:
            intents.append("yoy")

    if has(
        r"communal",
        r"commercial",
        r"conservanc",
        r"land\s+tenure",
        r"nearby\s+(farms?|camps?)",
        r"similar\s+(land|tenure|farms?)",
    ):
        intents.append("tenure")

    if has(
        r"compare",
        r"\bvs\.?\b",
        r"versus",
        r"which\s+camp",
        r"rest\s+(this|the)?\s*camp",
        r"which\s+.+\s+rest",
    ):
        intents.append("compare")

    if has(
        r"\bmove\b",
        r"how\s+long",
        r"another\s+week",
        r"stay\s+on",
        r"when\s+should\s+i\s+move",
        r"rainfall",
        r"rain\b",
    ):
        intents.append("move")

    if not intents:
        intents.append("general")
    return intents


def build_intent_answer(
    *,
    intents: list[str],
    stocking: Optional[dict[str, Any]] = None,
    yoy: Optional[dict[str, Any]] = None,
    tenure: Optional[dict[str, Any]] = None,
    scenario: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Extra plain-language paragraphs for the chat response."""
    parts: list[str] = []
    if scenario and scenario.get("found") and "scenario" in intents:
        parts.append(scenario.get("farmer_summary") or "")
        if scenario.get("disclaimer"):
            parts.append(scenario["disclaimer"])
    if stocking and stocking.get("found") and "stocking" in intents and "scenario" not in intents:
        parts.append(stocking.get("advice") or "")
    if yoy and yoy.get("found") and ("yoy" in intents or "bush" in intents):
        parts.append(yoy.get("summary") or "")
    if tenure and tenure.get("found") and "tenure" in intents:
        parts.append(tenure.get("summary") or "")
    return [p.strip() for p in parts if p and str(p).strip()]
