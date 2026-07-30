"""
Oryx — Gemini-powered Namibian rangeland advisor with agentic tool-calling.

The model decides which tools to call (pasture dataset, Open-Meteo weather,
grazing, stocking, etc.). Offline callers should skip this module and use
local dataset tools only.
"""

from __future__ import annotations

import inspect
import json
import logging
import os
from typing import Any, Optional

from services.connectivity import is_online
from tools.registry import GEMINI_TOOLS

logger = logging.getLogger(__name__)

AGENT_NAME = "Oryx"
MAX_TOOL_ROUNDS = 6
MAX_TOOL_RESULT_CHARS = 8000

ORYX_SYSTEM_PROMPT = """You are Oryx, a Namibian-themed rangeland advisor for livestock farmers.
Oryx is Namibia's national animal — resilient in dry land, like the farmers you serve.

YOUR JOB
- Help farmers with grazing, pasture condition, rainfall, stocking, and herd moves.
- You have tools. YOU decide when to call them — do not wait for a script.
- For site-specific questions (this camp, my pasture, rainfall here, should I move,
  how many animals, what-if herd changes): call the relevant tools first.
- For basic/general questions (what is NDVI, what is carrying capacity, how does
  rotation work): answer from knowledge — usually no tools needed.
- Prefer get_pasture_data for vegetation/cover/biomass from the local dataset.
- Prefer get_weather for live rainfall/forecast (Open-Meteo).
- Use calculate_grazing_pressure / estimate_safe_stocking when herd size matters.
- Use run_what_if_scenario for "what if …" questions.
- Never invent pasture or rainfall numbers. If a tool fails or returns found=false,
  say so and give cautious general advice.

RESPONSE STYLE
- Clear plain English a working farmer can use.
- State reasoning: e.g. "Based on grazing pressure X and recent rainfall Y…"
- Avoid definitive claims the data cannot support. Use "suggests", "likely", "based on".
- Free tier (USER_TIER=free): keep it short. One Premium upgrade nudge only for farm advice.
- Premium: fuller analysis and next actions.
- Do not invent UI badges like "Monitor Closely".

IDENTITY
- Your name is Oryx.
- Speak as a practical veld advisor for Namibia.
"""


def gemini_configured() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def _model_candidates() -> list[str]:
    primary = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip() or "gemini-2.0-flash"
    # Fallbacks help when a free-tier model is quota-exhausted.
    fallbacks = [
        "gemini-flash-latest",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
    ]
    out = [primary]
    for name in fallbacks:
        if name not in out:
            out.append(name)
    return out


def _tool_index() -> dict[str, dict[str, Any]]:
    return {t["name"]: t for t in GEMINI_TOOLS}


def _truncate_json(value: Any, limit: int = MAX_TOOL_RESULT_CHARS) -> str:
    text = json.dumps(value, default=str, ensure_ascii=False)
    if len(text) > limit:
        return text[:limit] + "…[truncated]"
    return text


def _build_declarations(types_mod: Any) -> list[Any]:
    decls = []
    for tool in GEMINI_TOOLS:
        decls.append(
            types_mod.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters_json_schema=tool["parameters"],
            )
        )
    return decls


def _extract_function_calls(response: Any) -> list[Any]:
    calls: list[Any] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", None):
                calls.append(fc)
    return calls


def _response_text(response: Any) -> str:
    try:
        text = (getattr(response, "text", None) or "").strip()
        if text:
            return text
    except Exception:  # noqa: BLE001 — SDK may raise if only function calls
        pass
    chunks: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                chunks.append(t)
    return "\n".join(chunks).strip()


def _normalize_tool_args(
    name: str,
    args: dict[str, Any],
    *,
    default_location: str,
    herd_size: Optional[int],
    livestock_type: Optional[str],
    farm_size_ha: Optional[float],
    land_tenure: Optional[str],
    message: str,
) -> dict[str, Any]:
    """Fill farmer context defaults and map schema names to Python kwargs."""
    cleaned = {k: v for k, v in (args or {}).items() if v is not None}
    tool = _tool_index().get(name) or {}
    fn = tool.get("callable")
    if not fn:
        return cleaned

    # Common defaults
    if "location" in (tool.get("parameters") or {}).get("properties", {}):
        cleaned.setdefault("location", default_location)
    if name == "compare_locations":
        cleaned.setdefault("location_a", default_location)

    if name == "run_what_if_scenario":
        cleaned.setdefault("location", default_location)
        cleaned.setdefault("question", message)
        if "animal_type" in cleaned and "livestock_type" not in cleaned:
            cleaned["livestock_type"] = cleaned.pop("animal_type")
        cleaned.setdefault("current_herd_size", herd_size)
        cleaned.setdefault("livestock_type", livestock_type or "cattle")
        cleaned.setdefault("farm_size_ha", farm_size_ha)
        cleaned.setdefault("land_tenure", land_tenure)
    elif name in {"calculate_grazing_pressure", "estimate_safe_stocking"}:
        cleaned.setdefault("herd_size", herd_size)
        cleaned.setdefault("animal_type", livestock_type)
        cleaned.setdefault("farm_size_ha", farm_size_ha)
    elif name == "compare_tenure_nearby":
        cleaned.setdefault("land_tenure", land_tenure)

    # Keep only params the callable accepts (positional + keyword)
    sig = inspect.signature(fn)
    allowed = set(sig.parameters.keys())
    return {k: v for k, v in cleaned.items() if k in allowed}


def _execute_tool(
    name: str,
    args: dict[str, Any],
    *,
    default_location: str,
    herd_size: Optional[int],
    livestock_type: Optional[str],
    farm_size_ha: Optional[float],
    land_tenure: Optional[str],
    message: str,
) -> dict[str, Any]:
    tool = _tool_index().get(name)
    if not tool:
        return {"found": False, "error": f"Unknown tool: {name}"}

    kwargs = _normalize_tool_args(
        name,
        args,
        default_location=default_location,
        herd_size=herd_size,
        livestock_type=livestock_type,
        farm_size_ha=farm_size_ha,
        land_tenure=land_tenure,
        message=message,
    )
    fn = tool["callable"]
    try:
        if name == "run_what_if_scenario":
            location = kwargs.pop("location", default_location)
            question = kwargs.pop("question", message)
            return fn(location, question, **kwargs)

        if name == "compare_locations":
            location_a = kwargs.pop("location_a", default_location)
            location_b = kwargs.pop("location_b", None)
            if not location_b:
                return {
                    "found": False,
                    "error": "compare_locations needs location_b",
                    "tool": name,
                }
            return fn(location_a, location_b, **kwargs)

        if "location" in kwargs:
            location = kwargs.pop("location")
            return fn(location, **kwargs)

        return fn(**kwargs)
    except TypeError as exc:
        logger.warning("Tool %s TypeError: %s kwargs=%s", name, exc, kwargs)
        return {"found": False, "error": str(exc), "tool": name}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tool %s failed: %s", name, exc)
        return {"found": False, "error": str(exc), "tool": name}


def run_vision_agent(
    *,
    message: str,
    location: str,
    advisor: Optional[dict[str, Any]] = None,  # kept for API compat; unused in agentic mode
    user_tier: str = "free",
    is_guest: bool = False,
    herd_size: Optional[int] = None,
    livestock_type: Optional[str] = None,
    farmer_name: Optional[str] = None,
    farm_name: Optional[str] = None,
    land_tenure: Optional[str] = None,
    farm_size_ha: Optional[float] = None,
    history: Optional[list[dict[str, Any]]] = None,
    require_online: bool = True,
    grounded: bool = True,  # unused — model decides tools
) -> Optional[dict[str, Any]]:
    """
    Run Oryx with Gemini agentic tool-calling.

    Returns None when offline / unconfigured / failed so callers can use local data.
    """
    _ = advisor, grounded  # API compatibility

    if require_online and not is_online():
        logger.info("%s skipped: offline (local data mode).", AGENT_NAME)
        return None

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("%s skipped: GEMINI_API_KEY not set", AGENT_NAME)
        return None

    tier = "free" if is_guest else (
        "premium" if str(user_tier).strip().lower() == "premium" else "free"
    )

    farm_bits = []
    if farmer_name:
        farm_bits.append(f"farmer={farmer_name}")
    if farm_name:
        farm_bits.append(f"farm={farm_name}")
    if herd_size is not None:
        farm_bits.append(f"herd_size={herd_size}")
    if livestock_type:
        farm_bits.append(f"livestock={livestock_type}")
    if farm_size_ha is not None:
        farm_bits.append(f"farm_size_ha={farm_size_ha}")
    if land_tenure:
        farm_bits.append(f"land_tenure={land_tenure}")

    history_lines: list[str] = []
    for item in (history or [])[-6:]:
        role = item.get("role") or "user"
        content = str(item.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    user_prompt = (
        f"USER_TIER={tier}\n"
        f"DEFAULT_LOCATION={location or 'not set'}\n"
        f"FARM_CONTEXT={', '.join(farm_bits) if farm_bits else 'not provided'}\n"
        f"IS_GUEST={'yes' if is_guest else 'no'}\n"
        f"DATA_MODE=online\n\n"
    )
    if history_lines:
        user_prompt += "RECENT_CHAT:\n" + "\n".join(history_lines) + "\n\n"
    user_prompt += (
        f"FARMER_QUESTION:\n{message}\n\n"
        "Decide whether you need tools. If you do, call them. "
        f"Default location for tools is {location}. "
        "Then answer as Oryx with clear reasoning grounded in tool results when used."
    )

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning("google-genai not installed; %s disabled.", AGENT_NAME)
        return None

    tools_used: list[dict[str, str]] = []
    tool_trace: list[str] = []
    last_error: Optional[BaseException] = None

    try:
        client = genai.Client(api_key=api_key)
        declarations = _build_declarations(types)
        config = types.GenerateContentConfig(
            system_instruction=ORYX_SYSTEM_PROMPT,
            temperature=0.35,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        for model_name in _model_candidates():
            tools_used = []
            tool_trace = []
            contents: list[Any] = [
                types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])
            ]
            final_text = ""
            try:
                for _round in range(MAX_TOOL_ROUNDS):
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                    calls = _extract_function_calls(response)

                    if not calls:
                        final_text = _response_text(response)
                        break

                    model_content = None
                    for candidate in getattr(response, "candidates", None) or []:
                        if getattr(candidate, "content", None):
                            model_content = candidate.content
                            break
                    if model_content is not None:
                        contents.append(model_content)

                    response_parts: list[Any] = []
                    for fc in calls:
                        name = fc.name
                        raw_args = dict(fc.args or {})
                        result = _execute_tool(
                            name,
                            raw_args,
                            default_location=location,
                            herd_size=herd_size,
                            livestock_type=livestock_type,
                            farm_size_ha=farm_size_ha,
                            land_tenure=land_tenure,
                            message=message,
                        )
                        summary = (
                            f"{name} -> found={result.get('found')}"
                            if isinstance(result, dict)
                            else name
                        )
                        tools_used.append({"name": name, "summary": summary})
                        tool_trace.append(
                            f"{name}({json.dumps(raw_args, default=str)[:200]})"
                        )
                        payload = result
                        raw = json.dumps(result, default=str, ensure_ascii=False)
                        if len(raw) > MAX_TOOL_RESULT_CHARS:
                            payload = {
                                "truncated": True,
                                "preview": raw[:MAX_TOOL_RESULT_CHARS],
                                "found": (
                                    result.get("found")
                                    if isinstance(result, dict)
                                    else None
                                ),
                            }
                        response_parts.append(
                            types.Part.from_function_response(
                                name=name,
                                response={"result": payload},
                            )
                        )

                    contents.append(types.Content(role="user", parts=response_parts))
                else:
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_text(
                                    text=(
                                        "Stop calling tools. Give your best farmer-facing "
                                        "answer now from the tool results you already have."
                                    )
                                )
                            ],
                        )
                    )
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=ORYX_SYSTEM_PROMPT,
                            temperature=0.35,
                        ),
                    )
                    final_text = _response_text(response)

                if final_text:
                    reasoning_bits = [
                        f"{AGENT_NAME} (Gemini {model_name}) used agentic tool-calling.",
                        f"Tools invoked: {', '.join(tool_trace) if tool_trace else 'none'}.",
                    ]
                    return {
                        "response": final_text,
                        "reasoning": " ".join(reasoning_bits),
                        "model": model_name,
                        "agent": AGENT_NAME,
                        "mode": "online",
                        "tools_used": tools_used,
                        "grounded": bool(tools_used),
                    }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                err = str(exc)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                    logger.warning(
                        "%s model %s quota/rate-limited; trying next model.",
                        AGENT_NAME,
                        model_name,
                    )
                    continue
                logger.warning("%s model %s failed: %s", AGENT_NAME, model_name, exc)
                continue

        if last_error:
            logger.warning(
                "%s Gemini agent failed (local fallback): %s", AGENT_NAME, last_error
            )
        return None
    except Exception as exc:  # noqa: BLE001 — soft-fail to local path
        logger.warning("%s Gemini agent failed (local fallback): %s", AGENT_NAME, exc)
        return None


# Backwards-compatible alias
run_oryx_agent = run_vision_agent
