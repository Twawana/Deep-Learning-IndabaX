"""
Parse free-form farmer what-if questions into scenario parameters.

Farmers should ask in their own words; this extracts herd/rain/move/location
signals without forcing a fixed form.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from services import dataset_service


def _known_place_names() -> list[str]:
    names: set[str] = set()
    try:
        df = dataset_service.load_advisory_dataframe()
        for col in ("site", "region"):
            if col in df.columns:
                names.update(str(v) for v in df[col].dropna().unique())
    except Exception:
        pass
    for alias, target in dataset_service.PLACE_ALIASES.items():
        names.add(alias)
        names.add(target)
    # Prefer longer names first for matching ("Katima Mulilo" before "Katima")
    return sorted({n.strip() for n in names if n and str(n).strip()}, key=len, reverse=True)


def is_scenario_question(message: str) -> bool:
    text = (message or "").strip().lower()
    if not text:
        return False
    patterns = (
        r"\bwhat\s*if\b",
        r"\bsuppose\b",
        r"\bscenario\b",
        r"\bif\s+i\s+(had|have|add|reduce|move|keep|double|halve|sell|buy)\b",
        r"\bif\s+we\s+(get|got|receive|had|have)\b",
        r"\bif\s+it\s+rains?\b",
        r"\bif\s+the\s+herd\b",
        r"\bimagine\b",
        r"\bhypothetic",
        r"\binstead\s+of\b",
        r"\bwould\s+it\s+(be|help|change)\b",
    )
    return any(re.search(p, text) for p in patterns)


def parse_scenario_question(
    message: str,
    *,
    current_herd_size: Optional[int] = None,
    current_location: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return extracted scenario knobs + a short reading of what the farmer asked.
    Missing knobs stay None (scenario uses current values).
    """
    text = (message or "").strip()
    lower = text.lower()
    assumptions: list[str] = []

    scenario_herd: Optional[int] = None
    assume_rain_mm: Optional[float] = None
    move_in_days: Optional[int] = None
    alternate_location: Optional[str] = None

    # --- herd size ---
    herd_match = re.search(
        r"(?:herd(?:\s+size)?|cattle|animals?|livestock|stock)\s*(?:of|to|at|=|:)?\s*(\d{1,4})",
        lower,
    )
    if herd_match:
        scenario_herd = int(herd_match.group(1))
        assumptions.append(f"Using scenario herd size {scenario_herd}.")
    else:
        had_match = re.search(r"\bif\s+i\s+had\s+(\d{1,4})\b", lower)
        if had_match:
            scenario_herd = int(had_match.group(1))
            assumptions.append(f"Using scenario herd size {scenario_herd}.")

    if scenario_herd is None and current_herd_size is not None:
        add = re.search(r"\b(?:add|buy|bring\s+in)\s+(\d{1,4})\b", lower)
        reduce = re.search(r"\b(?:reduce|sell|remove|cut)\s+(\d{1,4})\b", lower)
        if add:
            scenario_herd = int(current_herd_size) + int(add.group(1))
            assumptions.append(
                f"Adding {add.group(1)} animals -> scenario herd {scenario_herd}."
            )
        elif reduce:
            scenario_herd = max(1, int(current_herd_size) - int(reduce.group(1)))
            assumptions.append(
                f"Reducing by {reduce.group(1)} -> scenario herd {scenario_herd}."
            )
        elif re.search(r"\bdouble\b", lower):
            scenario_herd = int(current_herd_size) * 2
            assumptions.append(f"Doubling herd -> scenario herd {scenario_herd}.")
        elif re.search(r"\bhalve\b|\bhalf\b", lower):
            scenario_herd = max(1, int(current_herd_size) // 2)
            assumptions.append(f"Halving herd -> scenario herd {scenario_herd}.")

    # --- rainfall ---
    rain = re.search(
        r"(\d+(?:\.\d+)?)\s*mm(?:\s+of)?\s*(?:rain|rainfall)?",
        lower,
    )
    if rain and (
        "rain" in lower
        or "mm" in lower
        or re.search(r"\bif\s+it\s+rains?", lower)
        or re.search(r"get\s+\d", lower)
    ):
        assume_rain_mm = float(rain.group(1))
        assumptions.append(f"Assuming about {assume_rain_mm} mm of rain in the coming window.")
    else:
        rain2 = re.search(r"(?:rain|rainfall)\s*(?:of|about|around)?\s*(\d+(?:\.\d+)?)", lower)
        if rain2:
            assume_rain_mm = float(rain2.group(1))
            assumptions.append(
                f"Assuming about {assume_rain_mm} mm of rain in the coming window."
            )

    # --- move window ---
    days = re.search(r"(?:in|within|after)\s+(\d{1,3})\s*days?", lower)
    if days and re.search(r"\bmove\b|\bmoving\b|\brelocat", lower):
        move_in_days = int(days.group(1))
        assumptions.append(f"Planning around a move in about {move_in_days} days.")
    elif re.search(r"\bnext\s+week\b", lower) and re.search(r"\bmove\b", lower):
        move_in_days = 7
        assumptions.append("Planning around a move in about 7 days (next week).")
    elif re.search(r"\bin\s+two\s+weeks\b", lower):
        move_in_days = 14
        assumptions.append("Planning around a move in about 14 days.")

    # --- alternate location ---
    place_hint = re.search(
        r"(?:move\s+to|go\s+to|switch\s+to|use|at|camp\s+at|paddock\s+at|instead\s+(?:to|at|of))\s+([a-z0-9][a-z0-9\s\-/']{1,40})",
        lower,
    )
    candidate_blob = place_hint.group(1).strip() if place_hint else lower
    for name in _known_place_names():
        n = name.lower()
        if len(n) < 3:
            continue
        if n in candidate_blob or n in lower:
            # Skip if it's just restating the current location
            if current_location and dataset_service._norm(name) == dataset_service._norm(
                current_location
            ):
                continue
            # Require explicit relocation language unless "what if … at X"
            if place_hint or re.search(
                rf"(?:move|switch|go|compare|instead|at)\s+.*{re.escape(n)}",
                lower,
            ):
                alternate_location = name.title() if name.islower() else name
                # Prefer canonical casing from dataset when possible
                alternate_location = name
                assumptions.append(f"Comparing with alternate location '{alternate_location}'.")
                break

    understood = assumptions[:] if assumptions else [
        "Treating this as a what-if on your current camp using your profile herd and location."
    ]

    return {
        "is_scenario": is_scenario_question(text) or bool(assumptions),
        "scenario_herd_size": scenario_herd,
        "assume_rain_mm": assume_rain_mm,
        "move_in_days": move_in_days,
        "alternate_location": alternate_location,
        "assumptions": assumptions,
        "understood": " ".join(understood),
        "raw_question": text,
    }
