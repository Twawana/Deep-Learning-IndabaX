"""Comparison API routes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from models.schemas import CompareResponse
from tools.compare_tool import compare_locations

router = APIRouter(tags=["compare"])


@router.get(
    "/compare",
    response_model=CompareResponse,
    summary="Compare pasture conditions between two locations",
)
def compare_regions(
    location_a: str = Query(..., min_length=1, examples=["Gobabis"]),
    location_b: str = Query(..., min_length=1, examples=["Neudamm"]),
) -> dict:
    """
    Side-by-side comparison of measured pasture indicators.

    Useful for agent tool-calling when a farmer asks which area looks better.
    """
    return compare_locations(location_a, location_b)
