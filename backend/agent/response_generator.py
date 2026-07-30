"""
Natural Response Generator — Advisor stage (Gemini or local fallback).
"""

from __future__ import annotations

from typing import Any, Optional

from agent.intent_classifier import (
    INTENT_CHITCHAT,
    INTENT_GREETING,
    INTENT_OFF_TOPIC,
    SHAPE_CLARIFICATION,
    SHAPE_COMPARISON,
    SHAPE_EDUCATIONAL,
    SHAPE_STATUS,
)
from agent.prompts import (
    advisor_system_prompt,
    build_advisor_user_payload,
    educational_fallback,
)
from services.agent_router import conversational_reply


def generate_response(
    *,
    message: str,
    tier: str,
    intent_info: dict[str, Any],
    reasoning: dict[str, Any],
    evidence: dict[str, Any],
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Returns { ok, text, model, assistant, error? }
    """
    from services import gemini_service

    shape = reasoning.get("response_shape")
    intent = intent_info.get("intent")
    known = evidence.get("known_context") or {}

    if shape == SHAPE_CLARIFICATION:
        focus = reasoning.get("missing_information") or []
        if "herd_size" in focus:
            text = (
                "I can help with that. Roughly how many cattle (or goats/sheep) are "
                f"grazing around {known.get('region') or 'your camp'}? "
                "Herd size makes a big difference when estimating grazing pressure."
            )
            # Soft status if we have pasture/rain
            pasture = evidence.get("pasture") or {}
            rain = evidence.get("rainfall") or {}
            extras = []
            if pasture.get("found") and pasture.get("message"):
                extras.append(str(pasture["message"]))
            if rain.get("found") and rain.get("message"):
                extras.append(str(rain["message"]))
            if extras:
                text += "\n\nMeanwhile, from the local conditions: " + " ".join(extras[:2])
            return {
                "ok": True,
                "text": text,
                "model": None,
                "assistant": gemini_service.assistant_name(),
                "error": None,
            }

    if intent in {INTENT_GREETING, INTENT_CHITCHAT, INTENT_OFF_TOPIC}:
        mode = {
            INTENT_GREETING: "greeting",
            INTENT_CHITCHAT: "chitchat",
            INTENT_OFF_TOPIC: "off_topic",
        }[intent]
        return {
            "ok": True,
            "text": conversational_reply(
                mode=mode,
                farmer_name=None,
                location=known.get("region"),
            ),
            "model": None,
            "assistant": gemini_service.assistant_name(),
            "error": None,
        }

    # Prefer Gemini advisor when configured
    if gemini_service.is_configured():
        crafted = _gemini_advise(
            message=message,
            tier=tier,
            reasoning=reasoning,
            evidence=evidence,
            history=history or [],
        )
        if crafted.get("ok") and crafted.get("text"):
            return crafted

    # Local fallbacks
    if shape in {SHAPE_EDUCATIONAL} or intent in {"definition", "seasonal", "explanation"}:
        return {
            "ok": True,
            "text": educational_fallback(message, intent or ""),
            "model": None,
            "assistant": gemini_service.assistant_name(),
            "error": None,
        }

    if shape == SHAPE_STATUS:
        return {
            "ok": True,
            "text": _status_fallback(evidence),
            "model": None,
            "assistant": gemini_service.assistant_name(),
            "error": None,
        }

    if shape == SHAPE_COMPARISON:
        return {
            "ok": True,
            "text": _comparison_fallback(evidence),
            "model": None,
            "assistant": gemini_service.assistant_name(),
            "error": None,
        }

    return {
        "ok": True,
        "text": _recommendation_fallback(evidence, reasoning),
        "model": None,
        "assistant": gemini_service.assistant_name(),
        "error": None,
    }


def _gemini_advise(
    *,
    message: str,
    tier: str,
    reasoning: dict[str, Any],
    evidence: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    from services import gemini_service

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        return {"ok": False, "text": None, "model": None, "assistant": gemini_service.assistant_name(), "error": str(exc)}

    client = genai.Client(api_key=gemini_service.api_key())
    contents: list[Any] = []
    for turn in history[-6:]:
        role = (turn.get("role") or "").strip().lower()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=content)]))
        elif role == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part(text=content)]))

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=build_advisor_user_payload(
                        message=message, reasoning=reasoning, evidence=evidence
                    )
                )
            ],
        )
    )

    try:
        response = client.models.generate_content(
            model=gemini_service.model_name(),
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=advisor_system_prompt(
                    assistant_name=gemini_service.assistant_name(), tier=tier
                ),
                temperature=0.55,
                max_output_tokens=900 if tier == "premium" else 420,
            ),
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            return {
                "ok": False,
                "text": None,
                "model": gemini_service.model_name(),
                "assistant": gemini_service.assistant_name(),
                "error": "Empty Gemini advisor response",
            }
        return {
            "ok": True,
            "text": text,
            "model": gemini_service.model_name(),
            "assistant": gemini_service.assistant_name(),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "text": None,
            "model": gemini_service.model_name(),
            "assistant": gemini_service.assistant_name(),
            "error": str(exc),
        }


def _status_fallback(evidence: dict[str, Any]) -> str:
    pasture = evidence.get("pasture") or {}
    rain = evidence.get("rainfall") or {}
    bits = []
    region = (evidence.get("known_context") or {}).get("region") or "your area"
    bits.append(f"Here is what I can see for {region} right now.")
    if pasture.get("message"):
        bits.append(str(pasture["message"]))
    elif pasture.get("found"):
        bits.append("Pasture measurements are on file for this location.")
    if rain.get("message"):
        bits.append(str(rain["message"]))
    elif rain.get("found"):
        recent = rain.get("recent_rainfall_mm")
        bits.append(
            f"Recent rainfall looks like about {recent} mm."
            if recent is not None
            else "I pulled the latest rainfall context."
        )
    if len(bits) == 1:
        bits.append(
            "I do not have a strong local reading yet — ask about a specific camp, "
            "rainfall, or whether the herd can stay another week."
        )
    return "\n\n".join(bits)


def _comparison_fallback(evidence: dict[str, Any]) -> str:
    compare = evidence.get("comparison") or {}
    if compare.get("summary"):
        return str(compare["summary"])
    if compare.get("farmer_summary"):
        return str(compare["farmer_summary"])
    a = (compare.get("location_a") or compare.get("a") or {}).get("location") if isinstance(compare.get("location_a") or compare.get("a"), dict) else None
    b = (compare.get("location_b") or compare.get("b") or {}).get("location") if isinstance(compare.get("location_b") or compare.get("b"), dict) else None
    if compare.get("found"):
        return (
            f"I compared the two camps"
            + (f" ({a} vs {b})" if a and b else "")
            + ". Cover, rainfall stress, and grazing pressure differ between them — "
            "ask which side you want to lean on this week and we can unpack it."
        )
    return (
        "I can compare two camps when you name them clearly — for example "
        "'Compare Gobabis and Outjo'."
    )


def _recommendation_fallback(evidence: dict[str, Any], reasoning: dict[str, Any]) -> str:
    grazing = evidence.get("grazing") or {}
    stocking = evidence.get("stocking") or {}
    scenario = evidence.get("scenario") or {}
    pasture = evidence.get("pasture") or {}
    rain = evidence.get("rainfall") or {}
    region = (evidence.get("known_context") or {}).get("region") or "this camp"

    if scenario.get("farmer_summary"):
        return scenario["farmer_summary"]

    parts = [f"Looking at {region} with your herd in mind:"]
    if pasture.get("message"):
        parts.append(str(pasture["message"]))
    if rain.get("message"):
        parts.append(str(rain["message"]))
    if grazing.get("summary") or grazing.get("message"):
        parts.append(str(grazing.get("summary") or grazing.get("message")))
    elif stocking.get("advice"):
        # Soften raw stocking dump
        advice = str(stocking["advice"])
        if len(advice) > 320:
            advice = advice[:317] + "…"
        parts.append(advice)
    if len(parts) == 1:
        parts.append(
            "Pasture and rainfall together will tell us whether another week is wise. "
            "Walk the camp too — numbers help, but your eyes still matter."
        )
    parts.append("Review again after the next meaningful rain, or if animals start losing condition.")
    return "\n\n".join(parts)
