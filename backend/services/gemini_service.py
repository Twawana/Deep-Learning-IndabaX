"""
Oryx — Gemini agent for Namibian livestock decision support.

Not a scripted chatbot: the model chooses when to call pasture/dataset tools
vs live weather (Open-Meteo) via Gemini function calling.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from tools.registry import GEMINI_TOOLS

ASSISTANT_NAME_DEFAULT = "Oryx"
DEFAULT_MODEL = "gemini-2.0-flash"
MAX_TOOL_ROUNDS = 5


class GeminiError(Exception):
    pass


def assistant_name() -> str:
    return (os.getenv("ASSISTANT_NAME") or ASSISTANT_NAME_DEFAULT).strip() or ASSISTANT_NAME_DEFAULT


def model_name() -> str:
    return (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()


def is_configured() -> bool:
    return bool(api_key())


def _system_instruction(*, tier: str) -> str:
    name = assistant_name()
    depth = (
        "For farm decisions on Premium: a few short paragraphs, warm but concrete, "
        "ending with one clear next step."
        if tier == "premium"
        else "For farm decisions on Free: keep it short (a few sentences), still warm and clear."
    )
    return f"""You are {name}, a trusted Namibian livestock advisor inside Farmar (extension-officer voice).

First determine what the farmer is asking. Only call tools needed for that question.
Educational / seasonal / definition questions: explain naturally — do NOT recommend moving.
Decision questions: call pasture/weather/stocking tools as needed, then explain evidence.
Never fabricate NDVI, rainfall mm, cover %, or herd size. Ask if missing.
Never force "Prepare to Move" into unrelated answers. Do not upsell Premium. No emoji.
{depth}
"""


def _tool_declarations():
    from google.genai import types

    decls = []
    for tool in GEMINI_TOOLS:
        decls.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters_json_schema=tool["parameters"],
            )
        )
    return decls


def _callable_map() -> dict[str, Any]:
    return {tool["name"]: tool["callable"] for tool in GEMINI_TOOLS}


def _inject_defaults(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Fill farm context when the model omits obvious args."""
    out = dict(args or {})
    loc = ctx.get("location")
    if name in {
        "get_pasture_data",
        "get_weather",
        "calculate_grazing_pressure",
        "estimate_safe_stocking",
        "compare_to_prior_year",
        "compare_tenure_nearby",
        "run_what_if_scenario",
    }:
        out.setdefault("location", loc)
    if name == "get_weather":
        if ctx.get("lat") is not None:
            out.setdefault("latitude", ctx["lat"])
        if ctx.get("lon") is not None:
            out.setdefault("longitude", ctx["lon"])
    if name in {"calculate_grazing_pressure", "estimate_safe_stocking"}:
        if ctx.get("herd_size") is not None:
            out.setdefault("herd_size", ctx["herd_size"])
        if ctx.get("livestock_type"):
            out.setdefault("animal_type", ctx["livestock_type"])
        if ctx.get("farm_size_ha") is not None:
            out.setdefault("farm_size_ha", ctx["farm_size_ha"])
    if name == "compare_tenure_nearby":
        if ctx.get("land_tenure"):
            out.setdefault("land_tenure", ctx["land_tenure"])
        if ctx.get("lat") is not None:
            out.setdefault("latitude", ctx["lat"])
        if ctx.get("lon") is not None:
            out.setdefault("longitude", ctx["lon"])
    if name == "run_what_if_scenario":
        out.setdefault("question", ctx.get("message") or "")
        if ctx.get("herd_size") is not None:
            out.setdefault("current_herd_size", ctx["herd_size"])
        if ctx.get("livestock_type"):
            out.setdefault("livestock_type", ctx["livestock_type"])
        if ctx.get("farm_size_ha") is not None:
            out.setdefault("farm_size_ha", ctx["farm_size_ha"])
        if ctx.get("land_tenure"):
            out.setdefault("land_tenure", ctx["land_tenure"])
        out.pop("animal_type", None)
    return out


def _execute_tool(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    fn = _callable_map().get(name)
    if not fn:
        return {"found": False, "error": f"Unknown tool: {name}"}
    call_args = _inject_defaults(name, args, ctx)
    try:
        if name == "run_what_if_scenario":
            location = call_args.pop("location", ctx.get("location"))
            question = call_args.pop("question", ctx.get("message") or "")
            result = fn(location, question, **{
                k: v for k, v in call_args.items()
                if k in {"current_herd_size", "livestock_type", "land_tenure", "farm_size_ha"}
            })
        elif name == "compare_locations":
            location_a = call_args.pop("location_a", ctx.get("location"))
            location_b = call_args.pop("location_b", None)
            if not location_b:
                return {"found": False, "error": "compare_locations needs location_b"}
            result = fn(location_a, location_b, **{
                k: v for k, v in call_args.items() if k in {"land_tenure", "herd_size"}
            })
        elif "location" in call_args:
            location = call_args.pop("location")
            result = fn(location, **call_args)
        else:
            result = fn(**call_args)
        if not isinstance(result, dict):
            return {"found": True, "result": result}
        return result
    except TypeError:
        import inspect

        sig = inspect.signature(fn)
        allowed = set(sig.parameters)
        trimmed = {k: v for k, v in call_args.items() if k in allowed}
        try:
            if "location" in trimmed and list(sig.parameters)[0] == "location":
                location = trimmed.pop("location")
                result = fn(location, **trimmed)
            else:
                result = fn(**trimmed)
            return result if isinstance(result, dict) else {"found": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            return {"found": False, "error": str(exc), "tool": name}
    except Exception as exc:  # noqa: BLE001
        return {"found": False, "error": str(exc), "tool": name}


def _summarize_tool(name: str, result: dict[str, Any]) -> str:
    if not result:
        return name
    if result.get("error"):
        return f"{name}: error"
    if name == "get_pasture_data":
        return f"Pasture lookup · found={result.get('found')}"
    if name == "get_weather":
        recent = (result.get("recent_rainfall") or {}).get("total_precipitation_mm")
        return f"Open-Meteo weather · recent_mm={recent}"
    if name == "calculate_grazing_pressure":
        return f"Grazing pressure · risk={result.get('grazing_risk')}"
    if name == "estimate_safe_stocking":
        return f"Stocking · {result.get('status')}"
    if name == "compare_to_prior_year":
        return "Year-over-year pasture"
    if name == "compare_tenure_nearby":
        return "Tenure peer compare"
    if name == "run_what_if_scenario":
        return "What-if scenario"
    if name == "compare_locations":
        return "Compare camps"
    return name


def run_agent(
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
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    Agentic loop: Oryx decides which tools to call, then answers.

    Returns:
      ok, text, model, assistant, tools_used, tool_results, rounds, error?
    """
    if not is_configured():
        return {
            "ok": False,
            "text": None,
            "model": model_name(),
            "assistant": assistant_name(),
            "tools_used": [],
            "tool_results": {},
            "rounds": 0,
            "error": "GEMINI_API_KEY not configured",
        }

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        return {
            "ok": False,
            "text": None,
            "model": model_name(),
            "assistant": assistant_name(),
            "tools_used": [],
            "tool_results": {},
            "rounds": 0,
            "error": f"google-genai not installed: {exc}",
        }

    ctx = {
        "message": message,
        "location": location,
        "herd_size": herd_size,
        "livestock_type": livestock_type,
        "farm_size_ha": farm_size_ha,
        "land_tenure": land_tenure,
        "farm_notes": farm_notes,
        "lat": lat,
        "lon": lon,
    }

    profile_bits = [
        f"Default LOCATION: {location}",
        f"Herd size: {herd_size if herd_size is not None else 'not set'}",
        f"Livestock: {livestock_type or 'not set'}",
        f"Farm/camp size ha: {farm_size_ha if farm_size_ha is not None else 'not set'}",
        f"Land tenure: {land_tenure or 'unknown'}",
    ]
    if farmer_name:
        profile_bits.append(f"Farmer: {farmer_name}")
    if farm_notes:
        profile_bits.append(f"Notes: {farm_notes}")
    if lat is not None and lon is not None:
        profile_bits.append(f"GPS: {lat}, {lon}")

    contents: list[Any] = []
    for turn in (history or [])[-6:]:
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
                    text=(
                        "FARM CONTEXT:\n"
                        + "\n".join(f"- {b}" for b in profile_bits)
                        + f"\n\nFARMER MESSAGE:\n{message}\n\n"
                        "Respond as Oryx. Greetings and small talk: warm reply, no tools. "
                        "Off-topic: gentle redirect to livestock/grazing. "
                        "Farm questions: call only the tools you need, then answer with clear "
                        "reasoning in a natural, comforting voice — not a scripted report."
                    )
                )
            ],
        )
    )

    client = genai.Client(api_key=api_key())
    model = model_name()
    tool_config = types.GenerateContentConfig(
        system_instruction=_system_instruction(tier=tier),
        temperature=0.55,
        max_output_tokens=900 if tier == "premium" else 420,
        tools=[types.Tool(function_declarations=_tool_declarations())],
    )

    tools_used: list[dict[str, str]] = []
    tool_results: dict[str, Any] = {}
    final_text = ""

    try:
        for round_i in range(MAX_TOOL_ROUNDS):
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=tool_config,
            )

            candidate = (response.candidates or [None])[0]
            if candidate is None or candidate.content is None:
                raise GeminiError("Empty Gemini candidate.")

            parts = list(candidate.content.parts or [])
            function_calls = [p for p in parts if getattr(p, "function_call", None)]

            # Model finished with a text answer
            if not function_calls:
                text = (getattr(response, "text", None) or "").strip()
                if not text:
                    # assemble text from parts
                    chunks = []
                    for p in parts:
                        if getattr(p, "text", None):
                            chunks.append(p.text)
                    text = "\n".join(chunks).strip()
                final_text = text
                break

            # Append model turn with function calls
            contents.append(types.Content(role="model", parts=parts))

            # Execute each call and return results
            response_parts = []
            for part in function_calls:
                fc = part.function_call
                name = fc.name
                raw_args = dict(fc.args or {})
                result = _execute_tool(name, raw_args, ctx)
                tool_results[name] = result
                tools_used.append({"name": name, "summary": _summarize_tool(name, result)})
                # Keep payload small for the model
                compact = json.loads(json.dumps(result, default=str))
                if isinstance(compact, dict) and len(json.dumps(compact)) > 12000:
                    compact = {
                        k: compact[k]
                        for k in list(compact)[:40]
                    }
                    compact["_truncated"] = True
                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=name,
                            response={"result": compact},
                        )
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))
        else:
            # Max rounds — ask once more without tools for a wrap-up
            wrap = client.models.generate_content(
                model=model,
                contents=contents
                + [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text="Stop calling tools. Give your best farmer-facing recommendation now with reasoning."
                            )
                        ],
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=_system_instruction(tier=tier),
                    temperature=0.35,
                    max_output_tokens=700 if tier == "premium" else 360,
                ),
            )
            final_text = (getattr(wrap, "text", None) or "").strip()

        if not final_text:
            raise GeminiError("Oryx returned no text after tool use.")

        return {
            "ok": True,
            "text": final_text,
            "model": model,
            "assistant": assistant_name(),
            "tools_used": tools_used,
            "tool_results": tool_results,
            "rounds": round_i + 1,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "text": None,
            "model": model,
            "assistant": assistant_name(),
            "tools_used": tools_used,
            "tool_results": tool_results,
            "rounds": 0,
            "error": str(exc),
        }


# Back-compat alias used by older bridge code paths
def craft_reply(**kwargs: Any) -> dict[str, Any]:
    """Deprecated wrapper — prefers agentic run_agent when possible."""
    agent = run_agent(
        message=kwargs.get("message") or "",
        location=kwargs.get("location") or "",
        tier=kwargs.get("tier") or "free",
        herd_size=kwargs.get("herd_size"),
        livestock_type=kwargs.get("livestock_type"),
        farm_size_ha=kwargs.get("farm_size_ha"),
        land_tenure=kwargs.get("land_tenure"),
        farm_notes=kwargs.get("farm_notes"),
        history=kwargs.get("history"),
    )
    return {
        "ok": agent.get("ok"),
        "text": agent.get("text"),
        "model": agent.get("model"),
        "assistant": agent.get("assistant"),
        "error": agent.get("error"),
        "tools_used": agent.get("tools_used"),
        "tool_results": agent.get("tool_results"),
    }
