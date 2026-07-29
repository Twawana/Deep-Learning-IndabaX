"""Pasture API routes."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query

from models.schemas import PastureResponse
from tools.pasture_tool import get_pasture_data

router = APIRouter(tags=["pasture"])


@router.get(
    "/pasture/{region}",
    response_model=PastureResponse,
    summary="Get pasture / rangeland conditions",
    response_description="Aggregated pasture metrics with limitations and confidence.",
)
def pasture_by_region(
    region: str = Path(
        ...,
        description="Site, ecoregion, plot, or place alias (e.g. Gobabis, Molly, Central Kalahari).",
        examples=["Gobabis"],
    ),
    include_history: bool = Query(
        default=False,
        description="If true, include all seasonal plot rows in details_by_plot.",
    ),
) -> dict:
    """
    Return rangeland condition information from the **processed** advisory dataset.

    Does not read raw Excel research files. Values are aggregates of measured fields only.
    Missing measurements appear in `limitations` — nothing is fabricated.
    """
    return get_pasture_data(region, include_history=include_history)
