"""
Pasture tool — Gemini-ready interface over the processed advisory dataset.

Retrieves rangeland condition information for a Namibian location.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from models.schemas import PastureMetrics, PastureResponse
from services import dataset_service
from services.transparency import (
    confidence_from_limitations,
    is_stale,
    merge_limitations,
    missing_field_limitations,
    observation_age_days,
)

TOOL_DESCRIPTION = (
    "Retrieves rangeland condition information for a Namibian location "
    "from the processed advisory dataset (biomass, vegetation cover, bush encroachment)."
)

DETAIL_FIELDS = [
    "site",
    "site_code",
    "plot_name",
    "observation_date",
    "latitude",
    "longitude",
    "biomass",
    "vegetation_cover",
    "bush_encroachment",
    "grazing_pressure",
    "number_cattle",
    "cover_perennial_grass_pct",
    "cover_annual_grass_pct",
    "cover_bare_ground_pct",
    "dominant_herbaceous",
    "dominant_woody",
]


def _mean(series: pd.Series) -> Optional[float]:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().any():
        return round(float(numeric.mean()), 2)
    return None


def _first_non_null(series: pd.Series) -> Optional[str]:
    for value in series:
        if pd.notna(value) and str(value).strip():
            return str(value)
    return None


def get_pasture_data(location: str, *, include_history: bool = False) -> dict[str, Any]:
    """
    Retrieve pasture condition information for a location/site/region query.

    Args:
        location: Namibian place, research site, site code, or ecoregion.
        include_history: If True, details_by_plot includes all seasonal rows.

    Returns:
        Clean JSON with pasture metrics, limitations, and confidence.
        If not found: {"found": false, "message": "Region not found", ...}
    """
    query = (location or "").strip()
    if not query:
        return PastureResponse(
            found=False,
            location=query,
            message="Region not found",
            confidence="low",
            limitations=["No location provided"],
        ).model_dump()

    try:
        matched, matched_on, match_value = dataset_service.filter_by_query(query)
    except FileNotFoundError as exc:
        return PastureResponse(
            found=False,
            location=query,
            message=str(exc),
            confidence="low",
            limitations=["Processed advisory dataset unavailable"],
        ).model_dump()

    if matched.empty:
        return PastureResponse(
            found=False,
            location=query,
            message="Region not found",
            confidence="low",
            limitations=["No matching site or region in processed dataset"],
        ).model_dump()

    latest = dataset_service.latest_per_plot(matched)
    coords = dataset_service.representative_coordinates(matched)

    pasture = PastureMetrics(
        biomass=_mean(latest["biomass"]) if "biomass" in latest.columns else None,
        vegetation_cover=_mean(latest["vegetation_cover"]) if "vegetation_cover" in latest.columns else None,
        bush_encroachment=_mean(latest["bush_encroachment"]) if "bush_encroachment" in latest.columns else None,
        cover_perennial_grass_pct=_mean(latest["cover_perennial_grass_pct"])
        if "cover_perennial_grass_pct" in latest.columns
        else None,
        cover_annual_grass_pct=_mean(latest["cover_annual_grass_pct"])
        if "cover_annual_grass_pct" in latest.columns
        else None,
        cover_bare_ground_pct=_mean(latest["cover_bare_ground_pct"])
        if "cover_bare_ground_pct" in latest.columns
        else None,
        grazing_pressure_recorded=_mean(latest["grazing_pressure"])
        if "grazing_pressure" in latest.columns
        else None,
    )

    # Most recent observation date across latest plots
    observation_date = None
    if "observation_date" in latest.columns and latest["observation_date"].notna().any():
        observation_date = str(pd.to_datetime(latest["observation_date"]).max().date())

    detail_source = matched if include_history else latest
    details: list[dict[str, Any]] = []
    for _, row in detail_source.sort_values(
        ["plot_name", "observation_date"] if "observation_date" in detail_source.columns else ["plot_name"]
    ).iterrows():
        raw = dataset_service.row_to_dict(row)
        details.append({key: raw.get(key) for key in DETAIL_FIELDS})

    pasture_dict = pasture.model_dump()
    limitations = missing_field_limitations(
        pasture_dict,
        {
            "biomass": "Biomass measurement unavailable for one or more matched plots",
            "vegetation_cover": "Vegetation cover measurement unavailable",
            "bush_encroachment": "Bush encroachment measurement unavailable",
            "grazing_pressure_recorded": "Historical grazing/livestock counts unavailable for matched plots",
        },
    )

    # If biomass is partially missing, clarify
    if "biomass" in latest.columns:
        missing_biomass_share = float(pd.to_numeric(latest["biomass"], errors="coerce").isna().mean())
        if 0 < missing_biomass_share < 1:
            limitations.append("Biomass missing for some matched plots; mean uses available plots only")
        elif missing_biomass_share == 1:
            limitations = merge_limitations(
                limitations,
                ["Recent biomass measurement unavailable"],
            )

    age_days = observation_age_days(observation_date)
    if observation_date is None:
        limitations.append("Observation date unavailable")
    elif is_stale(observation_date):
        limitations.append(
            f"Pasture observations are dated {observation_date} "
            f"({age_days} days old) and may not reflect current conditions"
        )

    if matched_on and "alias" in matched_on:
        limitations.append(
            f"Location '{query}' mapped via place alias to dataset match '{match_value}'"
        )

    limitations = merge_limitations(limitations)
    # Pasture field data is rarely "high" confidence for live advice
    confidence = confidence_from_limitations(limitations, high_max=0, medium_max=3)
    if confidence == "high":
        confidence = "medium"

    latitude = coords[0] if coords else None
    longitude = coords[1] if coords else None

    return PastureResponse(
        found=True,
        location=query,
        matched_on=matched_on,
        match_value=match_value,
        sites=sorted(matched["site"].dropna().astype(str).unique().tolist()),
        pasture=pasture,
        observation_date=observation_date,
        plot_count=int(latest["plot_name"].nunique()) if "plot_name" in latest.columns else len(latest),
        latitude=latitude,
        longitude=longitude,
        dominant_herbaceous=_first_non_null(latest["dominant_herbaceous"])
        if "dominant_herbaceous" in latest.columns
        else None,
        dominant_woody=_first_non_null(latest["dominant_woody"])
        if "dominant_woody" in latest.columns
        else None,
        details_by_plot=details,
        limitations=limitations,
        confidence=confidence,  # type: ignore[arg-type]
    ).model_dump()
