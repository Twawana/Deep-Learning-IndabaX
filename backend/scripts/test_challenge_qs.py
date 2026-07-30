"""Smoke-test the 8 Farmar challenge questions via offline Vision."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["VISION_FORCE_MODE"] = "offline"

from services.offline_advisor import run_offline_advisor

QUESTIONS = [
    "Is this camp/paddock currently overgrazed?",
    "What's a safe stocking rate (carrying capacity) for this area right now?",
    "Should I move my herd, and if so, roughly when?",
    "How does the current pasture condition compare to the same time last year?",
    "Which of my camps should I rest this season, and which can still take grazing pressure?",
    "Is bush encroachment getting worse on my farm, and what should I do about it?",
    "Given the recent rainfall, how long can my herd stay on this pasture before I need to move them?",
    "How does my land's condition compare to similar land tenure types (communal vs. conservancy vs. commercial) nearby?",
]


def main() -> None:
    for i, q in enumerate(QUESTIONS, 1):
        r = run_offline_advisor(
            message=q,
            location="Gobabis",
            herd_size=40,
            farm_size_ha=400,
            land_tenure="commercial",
            livestock_type="cattle",
        )
        lines = [
            ln
            for ln in r["response"].splitlines()
            if ln.startswith("Direct answer")
            or ln.startswith("Camp rest")
            or ln.startswith("Rainfall")
        ]
        print(f"{i}. {'OK' if lines else 'MISSING'}  {q[:70]}")
        for ln in lines:
            print("   ", ln[:180].encode("ascii", "replace").decode())
        print()


if __name__ == "__main__":
    main()
