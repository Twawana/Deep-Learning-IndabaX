"""What-if scenario tool for free-form farmer questions."""

from __future__ import annotations

from typing import Any, Optional

from services.scenario_service import execute_scenario

TOOL_DESCRIPTION = (
    "Answers free-form what-if grazing questions (herd size, rainfall, move timing, "
    "alternate camp) by comparing current advice to a transparent scenario. "
    "Does not invent vegetation growth."
)


def run_what_if_scenario(
    location: str,
    question: str,
    *,
    current_herd_size: Optional[int] = None,
    livestock_type: Optional[str] = "cattle",
    land_tenure: Optional[str] = None,
    farm_size_ha: Optional[float] = None,
) -> dict[str, Any]:
    return execute_scenario(
        location=location,
        question=question,
        current_herd_size=current_herd_size,
        livestock_type=livestock_type,
        land_tenure=land_tenure,
        farm_size_ha=farm_size_ha,
    )
