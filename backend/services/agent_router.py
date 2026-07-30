"""
Lightweight intent router for Farmar chat (pre-Gemini).

Chooses which dataset tools to run based on the farmer's question so both
Lacuna and synthetic fields are used for the right hackathon questions.

Also classifies greetings / small talk / off-topic so In Vision does not
dump a scripted "Prepare to Move" card when someone just says hey.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from services.scenario_parser import is_scenario_question

# Pure greetings / small talk — do not run pasture tools or decision cards.
_GREETING_RE = re.compile(
    r"^\s*("
    r"hi+|h+e+y+|hello+|howdy|hola|hallo|howzit|how\s*z\s*it|"
    r"good\s*(morning|afternoon|evening|day)|"
    r"morning|afternoon|evening|"
    r"sawubona|dumela|moro|"
    r"how\s*(are|r)\s*(you|u)(\s*(doing|today))?|"
    r"what'?s\s*up|wassup|sup|yo+|"
    r"thanks?(?:\s*you)?|thank\s*you|ty|"
    r"ok(?:ay)?|cool|great|nice|"
    r"bye+|goodbye|see\s*you|"
    r"test|testing"
    r")[\s!.?]*$",
    re.IGNORECASE,
)

_OFF_TOPIC = re.compile(
    r"\b("
    r"car|cars|truck|trucks|motorbike|motorcycle|driving\s+licence|"
    r"plane|planes|airplane|airplanes|flight|airport|pilot|"
    r"football|soccer|rugby|cricket|nba|netflix|movie|movies|"
    r"bitcoin|crypto|stock\s+market|forex|"
    r"python\s+code|javascript|programming|coding\s+help|"
    r"recipe|cooking\s+pasta|video\s+game|playstation|xbox|"
    r"dating|girlfriend|boyfriend|politics\s+party"
    r")\b",
    re.I,
)

_FARMISH = re.compile(
    r"\b("
    r"camp|paddock|pasture|veld|graz|herd|cattle|cow|cows|goat|sheep|ox|"
    r"livestock|stocking|carrying|overgraz|bush|encroach|ndvi|biomass|"
    r"rain|rainfall|drought|move|rest\s+camp|tenure|communal|commercial|"
    r"conservanc|farm|farmer|lsu|fodder|water\s+point|borehole|calf|bull|"
    r"lamb|kraal|omah|gobabis|neudamm|namibia|rangeland"
    r")\b",
    re.I,
)

_GREETING = re.compile(
    r"^\s*("
    r"hey+|hi+|hello+|hola|howdy|howzit|how\s*z\s*it|"
    r"good\s*(morning|afternoon|evening|day)|"
    r"morning|afternoon|evening|"
    r"sawubona|dumela|moro|"
    r"how\s+are\s+you(\s+doing)?|how('?s|\s+is)\s+it\s+going|"
    r"what'?s\s+up|wassup|yo+"
    r")[\s!.?]*$",
    re.I,
)

_CHITCHAT = re.compile(
    r"^\s*("
    r"thanks|thank\s*you|thank\s*u|ty|cheers|ok|okay|cool|great|nice|"
    r"bye|goodbye|see\s+you|later|"
    r"who\s+are\s+you|what('?s|\s+is)\s+your\s+name|"
    r"what\s+can\s+you\s+(do|help\s+with)|help\s*me\??|"
    r"are\s+you\s+(there|real|an?\s+ai)"
    r")[\s!.?]*$",
    re.I,
)


def is_greeting(message: str) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 80:
        return False
    return bool(_GREETING_RE.match(text) or _GREETING.match(text))


def is_basic_question(message: str) -> bool:
    """
    Definitions / how-to / general knowledge — answer without farm decision cards.
    """
    text = (message or "").strip().lower()
    if not text or is_greeting(text):
        return False
    if re.search(
        r"\b(my|our|this)\s+(camp|pasture|farm|herd|veld|paddock)\b|"
        r"\b(how is|how'?s)\s+(my|the|our)\b|"
        r"\bshould i (move|rest|reduce|add|stock)\b|"
        r"\bwhat if\b",
        text,
    ):
        return False
    return bool(
        re.search(
            r"^(what\s+(is|are|does|do)|what'?s|explain|define|"
            r"how\s+does|how\s+do\s+i|tell\s+me\s+about|"
            r"meaning of|difference between)\b",
            text,
        )
    )


def needs_farm_tools(message: str, intents: Optional[list[str]] = None) -> bool:
    """True when the question needs local pasture/weather/stocking tools."""
    text = (message or "").strip().lower()
    if not text or is_greeting(text) or is_basic_question(text):
        return False

    intents = intents or detect_intents(text)
    farm_intents = {
        "scenario",
        "stocking",
        "yoy",
        "bush",
        "tenure",
        "compare",
        "move",
    }
    if any(i in farm_intents for i in intents):
        return True

    if re.search(
        r"\b(pasture|grazing|veld|camp|paddock|herd|cattle|goats?|sheep|"
        r"rainfall|rain|ndvi|biomass|cover|stock|carry|drought|"
        r"should i (move|rest|reduce|add)|how is (my|the) (camp|pasture|veld))\b",
        text,
    ):
        return True

    return False


def classify_conversation(message: str) -> str:
    """
    Return conversation mode:
      greeting | chitchat | off_topic | farm
    """
    text = (message or "").strip()
    if not text:
        return "chitchat"
    if _GREETING.match(text) or is_greeting(text):
        return "greeting"
    if _CHITCHAT.match(text):
        return "chitchat"
    if len(text) <= 24 and not _FARMISH.search(text) and re.match(
        r"^[\w\s'?!.,]+$", text
    ):
        if re.search(r"\b(lol|haha|hmm+|yes|no|sure|please)\b", text, re.I):
            return "chitchat"
    if _OFF_TOPIC.search(text) and not _FARMISH.search(text):
        return "off_topic"
    return "farm"


def conversational_reply(
    *,
    mode: str,
    farmer_name: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """Warm fallback replies when Gemini is offline."""
    name = (farmer_name or "").strip()
    who = name.split()[0] if name else ""
    hello = f"Hey{', ' + who if who else ''}"
    place = f" around {location}" if location else ""

    if mode == "greeting":
        return (
            f"{hello}. I'm In Vision — here when you need a clear read on your "
            f"camps, herd, or rainfall{place}.\n\n"
            "Ask me anything about grazing, stocking, moving the herd, or how "
            "the veld is holding up. No rush."
        )
    if mode == "chitchat":
        return (
            f"{hello if who else 'Got it'}. I'm here for your livestock and "
            "pasture decisions whenever you're ready — stocking, move timing, "
            "rainfall, bush, or comparing camps."
        )
    if mode == "off_topic":
        return (
            "I hear you — but I'm built for Namibian livestock and rangeland "
            "decisions: camps, grazing pressure, rainfall, stocking, bush, "
            "and when to move the herd.\n\n"
            "Cars, planes, and that sort of thing aren't my patch. Want to "
            "check how your pasture is looking instead?"
        )
    return (
        f"I'm with you{', ' + who if who else ''}. Tell me what you're seeing "
        "on the farm — overgrazing, rain, stocking, or whether to move — and "
        "I'll dig into the data and talk it through plainly."
    )


def detect_intents(message: str) -> list[str]:
    text = (message or "").strip().lower()
    intents: list[str] = []

    if is_greeting(text):
        return ["greeting"]

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
