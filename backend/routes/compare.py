"""Comparison API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from tools.compare_tool import compare_locations

router = APIRouter(tags=["compare"])


@router.get(
    "/compare",
    summary="Compare pasture conditions between two locations",
)
def compare_regions(
    location_a: str = Query(..., min_length=1, examples=["Gobabis"]),
    location_b: str = Query(..., min_length=1, examples=["Neudamm"]),
    land_tenure: Optional[str] = Query(default=None),
    herd_size: Optional[int] = Query(default=None),
) -> dict:
    """
    Side-by-side comparison of measured pasture indicators plus farmer summary.
    """
    return compare_locations(
        location_a,
        location_b,
        land_tenure=land_tenure,
        herd_size=herd_size,
    )
