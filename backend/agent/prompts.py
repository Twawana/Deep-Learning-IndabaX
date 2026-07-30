"""
Advisor prompts — Namibian agricultural extension officer voice.
"""

from __future__ import annotations

import json
from typing import Any


def advisor_system_prompt(*, assistant_name: str, tier: str) -> str:
    depth = (
        "Premium: a few short paragraphs, warm and concrete."
        if tier == "premium"
        else "Free: keep it short (a few sentences), still warm and clear."
    )
    return f"""You are {assistant_name}, an experienced Namibian agricultural extension officer
helping communal and commercial livestock farmers through Farmar.

You are NOT a chatbot script, NOT a weather app, and NOT a database dump.

Think in this order (silently):
1) What is the farmer actually asking?
2) Do I already know enough?
3) What evidence do I have?
4) Answer that question first.
5) Only then recommend an action if it naturally follows.

Rules:
- Answer the farmer's actual question first.
- Educational / seasonal / definition questions: teach clearly. Do NOT recommend moving the herd.
- Decision questions: use the provided evidence; explain what was checked, what was found,
  why it matters, what to do, and when to review again.
- If the internal plan says ask for clarification, ask naturally — do not invent herd size,
  rainfall mm, NDVI, cover %, or carrying capacity.
- Never fabricate environmental data.
- Tools already ran (or were skipped on purpose). Do not pretend you called tools you did not.
- Sound like a calm neighbour who knows the veld. Vary your language. Avoid repeating
  "Based on available data..." every time.
- Prefer phrases like: "From what I'm seeing...", "At the moment...", "The grass is recovering
  slowly because...", "Current rainfall conditions indicate..."
- Plain language. No emoji. No upselling Premium. No mentioning Gemini, JSON, or APIs.
- {depth}
"""


def build_advisor_user_payload(
    *,
    message: str,
    reasoning: dict[str, Any],
    evidence: dict[str, Any],
) -> str:
    # Strip bulky raw_results for the model prompt
    slim_evidence = {
        k: v
        for k, v in evidence.items()
        if k not in {"raw_results", "_traces"}
    }
    return (
        "INTERNAL REASONING (never quote this object to the farmer):\n"
        + json.dumps(reasoning, default=str)[:4500]
        + "\n\nEVIDENCE:\n"
        + json.dumps(slim_evidence, default=str)[:5500]
        + f"\n\nFARMER MESSAGE:\n{message}\n\n"
        "Write the farmer-facing reply now. Answer their question. "
        "Recommend a move/stay only if response_shape is recommendation or scenario."
    )


# Local educational fallbacks when Gemini is offline
EDU_FALLBACKS = {
    "ndvi": (
        "NDVI is a satellite measure of how green and active the vegetation looks. "
        "Higher NDVI usually means more living plant cover; lower NDVI often means "
        "stressed or sparse veld. It helps track pasture condition over time, but "
        "you should still walk the camp — satellites do not replace eyes on the ground."
    ),
    "bush": (
        "Bush encroachment is when woody shrubs and bushes thicken and crowd out the "
        "grass that cattle prefer. It can slowly reduce grazing capacity. Management "
        "options depend on your tenure and resources — thinning, controlled browsing, "
        "or resting camps — and should be planned carefully for your area."
    ),
    "carrying": (
        "Carrying capacity is roughly how much grazing an area can support without "
        "damaging the veld long-term, often spoken of as hectares per LSU (livestock unit). "
        "It changes with rainfall and season — dry years usually mean you need more hectares "
        "per animal."
    ),
    "seasonal": (
        "In Namibia, livestock graze throughout the year, but pasture quality changes "
        "with the seasons.\n\n"
        "During the rainy season, grass grows and recovers much faster.\n"
        "During the dry season, pasture recovery slows and grazing pressure usually feels heavier.\n\n"
        "So there is not one short 'grazing season' like a crop calendar — it is about "
        "matching herd pressure to how the veld is holding up right now."
    ),
    "stocking": (
        "Stocking rate is how many animals you keep on a given area. Safe stocking stays "
        "within what the pasture can support given recent rain and cover. Pushing too hard "
        "in a dry spell is when camps tip into overgrazing."
    ),
}


def educational_fallback(message: str, intent: str) -> str:
    text = (message or "").lower()
    if "ndvi" in text:
        return EDU_FALLBACKS["ndvi"]
    if "bush" in text or "encroach" in text:
        return EDU_FALLBACKS["bush"]
    if "carrying" in text or "ha/lsu" in text or "ha per" in text:
        return EDU_FALLBACKS["carrying"]
    if "stocking" in text:
        return EDU_FALLBACKS["stocking"]
    if intent == "seasonal" or "grazing season" in text or "rainy season" in text:
        return EDU_FALLBACKS["seasonal"]
    return (
        "Happy to explain that in plain language. In Namibian rangelands, the key is "
        "matching your herd to pasture condition and recent rainfall — tell me which "
        "camp or topic you want to unpack (NDVI, bush, stocking, or move timing)."
    )
