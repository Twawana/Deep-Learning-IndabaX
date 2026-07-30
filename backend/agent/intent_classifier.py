"""
Intent Analyzer — what is the farmer actually asking?

Never assume every farm-related message wants a move/stocking recommendation.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from services.agent_router import classify_conversation
from services.scenario_parser import is_scenario_question

# Fine-grained intents for the reasoning pipeline
INTENT_GREETING = "greeting"
INTENT_CHITCHAT = "chitchat"
INTENT_OFF_TOPIC = "off_topic"
INTENT_DEFINITION = "definition"
INTENT_EXPLANATION = "explanation"
INTENT_SEASONAL = "seasonal"
INTENT_WEATHER = "weather"
INTENT_RAINFALL = "rainfall"
INTENT_PASTURE = "pasture_condition"
INTENT_DECISION = "decision_support"
INTENT_HERD = "herd_management"
INTENT_COMPARISON = "comparison"
INTENT_SCENARIO = "scenario"
INTENT_YOY = "year_over_year"
INTENT_TENURE = "tenure_compare"
INTENT_FOLLOW_UP = "follow_up"
INTENT_FARM_MGMT = "farm_management"

# Response shapes (Decision Engine outcomes)
SHAPE_CONVERSATION = "conversation"
SHAPE_EDUCATIONAL = "educational"
SHAPE_CLARIFICATION = "clarification"
SHAPE_RECOMMENDATION = "recommendation"
SHAPE_COMPARISON = "comparison"
SHAPE_SCENARIO = "scenario"
SHAPE_STATUS = "status"  # pasture/weather facts without move advice


def _has(text: str, *patterns: str) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def classify_intent(
    message: str,
    *,
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Return structured intent analysis (never shown raw to the farmer).

    {
      intent, secondary, wants_recommendation, confidence, notes
    }
    """
    raw = (message or "").strip()
    text = raw.lower()
    mode = classify_conversation(raw)

    if mode == "greeting":
        return _pack(INTENT_GREETING, wants_recommendation=False, confidence="high")
    if mode == "chitchat":
        return _pack(INTENT_CHITCHAT, wants_recommendation=False, confidence="high")
    if mode == "off_topic":
        return _pack(INTENT_OFF_TOPIC, wants_recommendation=False, confidence="high")

    # Definitions / concepts — teach, do not recommend
    if _has(
        text,
        r"\bwhat\s+is\b",
        r"\bdefine\b",
        r"\bexplain\s+(what|ndvi|bush|stocking|carrying|grazing)",
        r"\bmean(?:s|ing)?\b",
    ) and _has(
        text,
        r"\bndvi\b",
        r"\bbush\b",
        r"\bencroach",
        r"\bcarrying\s+capacit",
        r"\bstocking\s+rate\b",
        r"\blsu\b",
        r"\bovergraz",
        r"\brangeland\b",
        r"\bveld\b",
        r"\bbiomass\b",
        r"\bgrazing\s+pressure\b",
        r"\bgrazing\s+season\b",
    ):
        # "what is grazing season" is seasonal education, not a definition dump
        if _has(text, r"grazing\s+season", r"rainy\s+season", r"dry\s+season"):
            return _pack(
                INTENT_SEASONAL,
                secondary=INTENT_EXPLANATION,
                wants_recommendation=False,
                confidence="high",
            )
        return _pack(INTENT_DEFINITION, wants_recommendation=False, confidence="high")

    # Seasonal / calendar education
    if _has(
        text,
        r"grazing\s+season",
        r"is\s+it\s+(the\s+)?(grazing|rainy|dry)\s+season",
        r"when\s+(is|does)\s+(the\s+)?(rainy|dry|grazing)\s+season",
        r"rainy\s+season\s+vs",
        r"dry\s+season\s+(mean|start|end)",
    ):
        return _pack(
            INTENT_SEASONAL,
            secondary=INTENT_EXPLANATION,
            wants_recommendation=False,
            confidence="high",
            notes="Answer seasonality first; optional local conditions only if asked.",
        )

    # Explicit recommendation / stay-or-move decisions
    wants_rec = _has(
        text,
        r"\bshould\s+i\s+(move|stay|rest|graze|reduce|add)\b",
        r"\bcan\s+(my|the)\s+(cattle|herd|animals|goats|sheep)\s+stay\b",
        r"\bhow\s+long\s+can\b",
        r"\bprepare\s+to\s+move\b",
        r"\bmove\s+(my|the)\s+herd\b",
        r"\bwhen\s+should\s+i\s+move\b",
        r"\brecommend\b",
        r"\bwhat\s+should\s+i\s+do\b",
        r"\bovergrazed\b",
        r"\bsafe\s+stocking\b",
        r"\bcarrying\s+capacit",
        r"\banother\s+week\b",
        r"\bstay\s+(another|one\s+more|here)\b",
    )

    if is_scenario_question(text) or _has(
        text, r"\bwhat\s*if\b", r"\bsuppose\b", r"\bif\s+i\s+(add|reduce|halve|double|move)\b"
    ):
        return _pack(INTENT_SCENARIO, wants_recommendation=True, confidence="high")

    if _has(
        text,
        r"\bcompare\b",
        r"\bvs\.?\b",
        r"\bversus\b",
        r"\bdifference\s+between\b",
        r"\bwhich\s+(camp|area|site)\b",
    ):
        return _pack(INTENT_COMPARISON, wants_recommendation=False, confidence="high")

    if _has(
        text,
        r"last\s+year",
        r"same\s+time\s+last",
        r"year\s+ago",
        r"bush\s+encroach",
        r"getting\s+worse",
        r"compared?\s+to\s+last",
    ):
        return _pack(INTENT_YOY, wants_recommendation=False, confidence="high")

    if _has(
        text,
        r"\bcommunal\b",
        r"\bcommercial\b",
        r"\bconservanc",
        r"land\s+tenure",
        r"similar\s+(land|tenure|farms?)",
    ):
        return _pack(INTENT_TENURE, wants_recommendation=False, confidence="high")

    if _has(
        text,
        r"\brainfall\b",
        r"\bhow\s+much\s+rain\b",
        r"\bdid\s+it\s+rain\b",
        r"\brecent\s+rain\b",
    ):
        return _pack(INTENT_RAINFALL, wants_recommendation=False, confidence="high")

    if _has(
        text,
        r"\bweather\b",
        r"\bforecast\b",
        r"\btemperature\b",
        r"\bdrought\b",
    ):
        return _pack(INTENT_WEATHER, wants_recommendation=False, confidence="high")

    if _has(
        text,
        r"\bpasture\b",
        r"\bveld\b",
        r"\bcamp\s+condition\b",
        r"\bvegetation\b",
        r"\bndvi\b",
        r"\bbiomass\b",
        r"\bhow\s+(is|does)\s+(the\s+)?(pasture|veld|camp)\b",
        r"\bpasture\s+health\b",
    ) and not wants_rec:
        return _pack(INTENT_PASTURE, wants_recommendation=False, confidence="medium")

    if wants_rec or _has(
        text,
        r"\bstocking\b",
        r"\bherd\s+size\b",
        r"\bgrazing\s+pressure\b",
        r"\bover\s*graz",
    ):
        return _pack(INTENT_DECISION, wants_recommendation=True, confidence="high")

    if _has(text, r"\bherd\b", r"\bcattle\b", r"\bgoats?\b", r"\bsheep\b") and _has(
        text, r"\bmanage\b", r"\brest\b", r"\brotate\b", r"\bwater\b"
    ):
        return _pack(INTENT_HERD, wants_recommendation=True, confidence="medium")

    # Follow-up short messages after prior farm talk
    if history and len(raw) < 40 and _has(
        text, r"^(and|also|what\s+about|how\s+about|yes|no|ok)\b"
    ):
        return _pack(
            INTENT_FOLLOW_UP,
            wants_recommendation=False,
            confidence="medium",
            notes="Reuse prior context; clarify if unclear.",
        )

    if _has(text, r"\bfarm\b", r"\bcamp\b", r"\bgraz", r"\bpasture", r"\brain"):
        return _pack(
            INTENT_FARM_MGMT,
            secondary=INTENT_EXPLANATION,
            wants_recommendation=False,
            confidence="low",
            notes="Prefer explaining/asking before recommending.",
        )

    return _pack(
        INTENT_EXPLANATION,
        wants_recommendation=False,
        confidence="low",
        notes="Default: answer the question; do not force a move recommendation.",
    )


def _pack(
    intent: str,
    *,
    wants_recommendation: bool,
    confidence: str,
    secondary: Optional[str] = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "intent": intent,
        "secondary": secondary,
        "wants_recommendation": wants_recommendation,
        "confidence": confidence,
        "notes": notes,
    }
