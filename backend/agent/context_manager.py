"""
Context & Memory Resolver — reuse farm profile + chat history facts.
"""

from __future__ import annotations

import re
from typing import Any, Optional


def resolve_context(
    *,
    message: str,
    location: Optional[str] = None,
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
) -> dict[str, Any]:
    """Merge profile + facts mentioned in this session."""
    herd = herd_size
    animal = livestock_type
    loc = location
    size_ha = farm_size_ha

    # Scan recent user turns for herd size / location mentions
    for turn in (history or [])[-8:]:
        if (turn.get("role") or "").lower() != "user":
            continue
        content = turn.get("content") or ""
        herd = herd if herd is not None else _extract_herd(content)
        size_ha = size_ha if size_ha is not None else _extract_ha(content)
        loc = loc or _extract_location_hint(content)

    # Current message can override / fill
    herd = _extract_herd(message) if herd is None else herd
    if size_ha is None:
        size_ha = _extract_ha(message)
    # Location from message only if profile empty (avoid overriding Gobabis with noise)
    if not loc:
        loc = _extract_location_hint(message)

    missing: list[str] = []
    # Missing location is usually already blocked by /chat; still track herd for decisions
    known = {
        "location": loc,
        "herd_size": herd,
        "livestock_type": animal or "cattle",
        "farm_size_ha": size_ha,
        "land_tenure": land_tenure,
        "farm_notes": farm_notes,
        "farmer_name": farmer_name,
        "farm_name": farm_name,
        "lat": lat,
        "lon": lon,
    }
    return {
        "known": known,
        "missing": missing,
        "history": history or [],
    }


def missing_for_decision(context: dict[str, Any]) -> list[str]:
    """What a stay/move decision usually needs."""
    known = context.get("known") or {}
    missing: list[str] = []
    if known.get("herd_size") is None:
        missing.append("herd_size")
    if not known.get("location"):
        missing.append("location")
    return missing


def _extract_herd(text: str) -> Optional[int]:
    m = re.search(
        r"\b(\d{1,5})\s*(cattle|cows?|goats?|sheep|animals?|head|lsu)\b",
        text or "",
        re.I,
    )
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    m2 = re.search(r"\b(?:herd(?:\s+size)?|i have)\s*(?:of\s*)?(\d{1,5})\b", text or "", re.I)
    if m2:
        try:
            return int(m2.group(1))
        except ValueError:
            return None
    return None


def _extract_ha(text: str) -> Optional[float]:
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*(ha|hectares?)\b", text or "", re.I)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


_KNOWN_PLACES = (
    "gobabis",
    "outjo",
    "windhoek",
    "neudamm",
    "molly",
    "omaheke",
    "khomas",
    "otjozondjupa",
    "erongo",
    "kunene",
    "oshikoto",
    "oshana",
    "ohangwena",
    "omusati",
    "kavango",
    "zambezi",
    "hardap",
    "karas",
)


def _extract_location_hint(text: str) -> Optional[str]:
    low = (text or "").lower()
    for place in _KNOWN_PLACES:
        if re.search(rf"\b{re.escape(place)}\b", low):
            return place.title() if place not in {"ndvi"} else place
    return None
