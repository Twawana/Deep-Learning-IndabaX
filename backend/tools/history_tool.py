"""Year-over-year pasture comparison tool (Lacuna multi-date plots)."""

from __future__ import annotations

from typing import Any

from services.dataset_bridge import year_over_year_for_location

TOOL_DESCRIPTION = (
    "Compares current pasture indicators to roughly the same season last year "
    "using multi-date Lacuna field plots (cover, biomass, bush encroachment)."
)


def compare_to_prior_year(location: str) -> dict[str, Any]:
    return year_over_year_for_location(location)
