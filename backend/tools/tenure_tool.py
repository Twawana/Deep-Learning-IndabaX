"""Tenure peer comparison tool (synthetic land_tenure neighbourhood)."""

from __future__ import annotations

from typing import Any, Optional

from services.dataset_bridge import compare_tenure_peers

TOOL_DESCRIPTION = (
    "Compares pasture/stocking indicators for the farmer's area against nearby "
    "synthetic sites with the same or different land tenure "
    "(communal, commercial, conservancy)."
)


def compare_tenure_nearby(
    location: str,
    *,
    land_tenure: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 120.0,
) -> dict[str, Any]:
    return compare_tenure_peers(
        location=location,
        land_tenure=land_tenure,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
    )
