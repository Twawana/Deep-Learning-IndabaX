"""
Spatial + temporal helpers so Lacuna field plots and synthetic_v2 rows work together.

Lacuna ecoregions and synthetic political regions do not share names, so GPS
neighbourhood and tenure filters bridge the two sources.
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from services import dataset_service

SYNTHETIC_SOURCE = "synthetic_v2"
LACUNA_SOURCE = "lacuna_field"

# Namibia's 14 political regions (synthetic dataset grain).
POLITICAL_REGIONS = {
    "erongo",
    "hardap",
    "karas",
    "ǁkaras",
    "kavango east",
    "kavango west",
    "khomas",
    "kunene",
    "ohangwena",
    "omaheke",
    "omusati",
    "oshana",
    "oshikoto",
    "otjozondjupa",
    "zambezi",
}


def is_political_region(name: str) -> bool:
    return dataset_service._norm(name) in POLITICAL_REGIONS


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    return dataset_service._haversine_km(lat1, lon1, lat2, lon2)


def filter_source(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df.empty or "dataset_source" not in df.columns:
        return df.iloc[0:0].copy()
    return df.loc[df["dataset_source"].astype(str) == source].copy()


def nearby_rows(
    *,
    latitude: float,
    longitude: float,
    source: Optional[str] = SYNTHETIC_SOURCE,
    radius_km: float = 80.0,
    limit: int = 40,
) -> pd.DataFrame:
    """Return latest-per-plot rows within radius_km of a point."""
    df = dataset_service.load_advisory_dataframe()
    latest = dataset_service.latest_per_plot(df)
    if source:
        latest = filter_source(latest, source)
    if latest.empty:
        return latest

    rows: list[dict[str, Any]] = []
    for _, row in latest.iterrows():
        lat = pd.to_numeric(row.get("latitude"), errors="coerce")
        lon = pd.to_numeric(row.get("longitude"), errors="coerce")
        if pd.isna(lat) or pd.isna(lon):
            continue
        dist = _haversine_km(latitude, longitude, float(lat), float(lon))
        if dist <= radius_km:
            item = dataset_service.row_to_dict(row)
            item["distance_km"] = round(dist, 1)
            rows.append(item)

    rows.sort(key=lambda r: r.get("distance_km") or 9999)
    return pd.DataFrame(rows[:limit])


def summarise_metric_frame(df: pd.DataFrame) -> dict[str, Any]:
    """Mean metrics for a set of advisory rows (dict-friendly)."""
    if df.empty:
        return {"found": False, "plot_count": 0}

    def mean(col: str) -> Optional[float]:
        if col not in df.columns:
            return None
        series = pd.to_numeric(df[col], errors="coerce")
        if not series.notna().any():
            return None
        return round(float(series.mean()), 3)

    def mode_str(col: str) -> Optional[str]:
        if col not in df.columns:
            return None
        series = df[col].dropna().astype(str)
        if series.empty:
            return None
        return str(series.mode().iloc[0])

    tenure_counts: dict[str, int] = {}
    if "land_tenure" in df.columns:
        tenure_counts = (
            df["land_tenure"].dropna().astype(str).str.strip().str.lower().value_counts().to_dict()
        )

    return {
        "found": True,
        "plot_count": int(len(df)),
        "vegetation_cover": mean("vegetation_cover"),
        "biomass": mean("biomass"),
        "bush_encroachment": mean("bush_encroachment"),
        "ndvi": mean("ndvi"),
        "carrying_capacity_ha_per_lsu": mean("carrying_capacity_ha_per_lsu"),
        "livestock_density_lsu_per_ha": mean("livestock_density_lsu_per_ha"),
        "recorded_rainfall_mm": mean("recorded_rainfall_mm"),
        "grazing_pressure_label": mode_str("grazing_pressure_label"),
        "browsing_pressure_label": mode_str("browsing_pressure_label"),
        "bush_encroachment_level": mode_str("bush_encroachment_level"),
        "land_tenure_counts": tenure_counts,
        "mean_distance_km": mean("distance_km") if "distance_km" in df.columns else None,
        "regions": sorted({str(r) for r in df["region"].dropna().unique()}) if "region" in df.columns else [],
    }


def enrich_with_nearby_synthetic(
    *,
    latitude: Optional[float],
    longitude: Optional[float],
    radius_km: float = 80.0,
) -> dict[str, Any]:
    """Attach nearby synthetic averages (capacity, NDVI, tenure) to a Lacuna hit."""
    if latitude is None or longitude is None:
        return {"found": False, "reason": "No coordinates for neighbourhood search"}
    nearby = nearby_rows(
        latitude=float(latitude),
        longitude=float(longitude),
        source=SYNTHETIC_SOURCE,
        radius_km=radius_km,
    )
    summary = summarise_metric_frame(nearby)
    if not summary.get("found"):
        summary["reason"] = f"No synthetic sites within {radius_km:.0f} km"
        return summary
    summary["radius_km"] = radius_km
    summary["dataset_source"] = SYNTHETIC_SOURCE
    summary["note"] = (
        f"Nearby synthetic estimates from {summary['plot_count']} sites "
        f"within ~{radius_km:.0f} km (NDVI, carrying capacity, tenure)."
    )
    return summary


def year_over_year_for_location(location: str) -> dict[str, Any]:
    """
    Compare latest observations vs same season ~1 year earlier (Lacuna multi-date plots).
    Synthetic rows are usually single-date and contribute little here.
    """
    matched, matched_on, match_value = dataset_service.filter_by_query(location)
    if matched.empty:
        return {
            "found": False,
            "location": location,
            "message": "Location not found for year-over-year comparison",
        }

    df = matched.copy()
    if "observation_date" not in df.columns:
        return {"found": False, "location": location, "message": "No observation dates available"}

    df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    df = df.dropna(subset=["observation_date", "plot_name"])
    if df.empty:
        return {"found": False, "location": location, "message": "No dated plot observations"}

    # Prefer Lacuna multi-year field plots when present
    lacuna = filter_source(df, LACUNA_SOURCE) if "dataset_source" in df.columns else df
    work = lacuna if not lacuna.empty else df

    latest_date = work["observation_date"].max()
    prior_window_start = latest_date - pd.Timedelta(days=400)
    prior_window_end = latest_date - pd.Timedelta(days=300)

    latest = (
        work.sort_values("observation_date", ascending=False)
        .drop_duplicates("plot_name", keep="first")
    )
    prior = work[
        (work["observation_date"] >= prior_window_start)
        & (work["observation_date"] <= prior_window_end)
    ]
    if prior.empty:
        # Fallback: any observation 9–15 months earlier
        prior = work[
            (work["observation_date"] <= latest_date - pd.Timedelta(days=270))
            & (work["observation_date"] >= latest_date - pd.Timedelta(days=450))
        ]
    prior = (
        prior.sort_values("observation_date", ascending=False)
        .drop_duplicates("plot_name", keep="first")
        if not prior.empty
        else prior
    )

    def block(frame: pd.DataFrame) -> dict[str, Any]:
        if frame.empty:
            return {"found": False, "plot_count": 0}
        out = summarise_metric_frame(frame)
        out["observation_date_min"] = str(frame["observation_date"].min().date())
        out["observation_date_max"] = str(frame["observation_date"].max().date())
        return out

    current = block(latest)
    previous = block(prior)

    deltas: dict[str, Optional[float]] = {}
    for key in ("vegetation_cover", "biomass", "bush_encroachment", "ndvi"):
        a = current.get(key)
        b = previous.get(key)
        if a is None or b is None:
            deltas[key] = None
        else:
            deltas[key] = round(float(a) - float(b), 2)

    narrative_bits: list[str] = []
    if deltas.get("vegetation_cover") is not None:
        d = deltas["vegetation_cover"]
        if d <= -5:
            narrative_bits.append(f"Vegetation cover is about {abs(d):.0f} points lower than last year.")
        elif d >= 5:
            narrative_bits.append(f"Vegetation cover is about {d:.0f} points higher than last year.")
        else:
            narrative_bits.append("Vegetation cover is similar to the same season last year.")
    if deltas.get("bush_encroachment") is not None:
        d = deltas["bush_encroachment"]
        if d >= 5:
            narrative_bits.append(
                f"Bush/woody signal is higher than last year (+{d:.0f} points) — watch encroachment."
            )
        elif d <= -5:
            narrative_bits.append(
                f"Bush/woody signal is lower than last year ({d:.0f} points) — a positive change."
            )

    if not previous.get("found"):
        narrative_bits.append(
            "Not enough prior-year observations for a firm same-season comparison "
            "(synthetic sites are mostly single-date)."
        )

    return {
        "found": True,
        "location": location,
        "matched_on": matched_on,
        "match_value": match_value,
        "current": current,
        "previous": previous,
        "deltas": deltas,
        "summary": " ".join(narrative_bits) if narrative_bits else "Year-over-year comparison incomplete.",
        "limitations": [
            "Year-over-year works best on Lacuna multi-date field plots.",
            "Synthetic rows are usually one survey date and may not appear in the prior window.",
        ],
    }


def compare_tenure_peers(
    *,
    location: str,
    land_tenure: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 120.0,
) -> dict[str, Any]:
    """
    Compare the farmer's area to nearby synthetic sites with the same / other tenures.
    """
    matched, matched_on, match_value = dataset_service.filter_by_query(location)
    if matched.empty and (latitude is None or longitude is None):
        return {"found": False, "location": location, "message": "Location not found"}

    coords = dataset_service.representative_coordinates(matched) if not matched.empty else None
    lat = latitude if latitude is not None else (coords[0] if coords else None)
    lon = longitude if longitude is not None else (coords[1] if coords else None)
    if lat is None or lon is None:
        return {"found": False, "location": location, "message": "No coordinates for tenure peer search"}

    nearby = nearby_rows(
        latitude=float(lat),
        longitude=float(lon),
        source=SYNTHETIC_SOURCE,
        radius_km=radius_km,
        limit=80,
    )
    if nearby.empty:
        return {
            "found": False,
            "location": location,
            "message": f"No synthetic tenure peers within {radius_km:.0f} km",
        }

    tenure = (land_tenure or "").strip().lower()
    if tenure in {"", "unknown"}:
        # Infer modal tenure from neighbourhood
        if "land_tenure" in nearby.columns and nearby["land_tenure"].notna().any():
            tenure = str(nearby["land_tenure"].mode().iloc[0]).strip().lower()

    peers = nearby
    same = nearby
    if "land_tenure" in nearby.columns and tenure:
        same = nearby[nearby["land_tenure"].astype(str).str.strip().str.lower() == tenure]
        peers = nearby

    by_tenure: dict[str, Any] = {}
    if "land_tenure" in peers.columns:
        for name, group in peers.groupby(peers["land_tenure"].astype(str).str.strip().str.lower()):
            by_tenure[str(name)] = summarise_metric_frame(group)

    same_summary = summarise_metric_frame(same) if not same.empty else {"found": False}
    all_summary = summarise_metric_frame(peers)

    lines: list[str] = []
    if same_summary.get("found") and tenure:
        lines.append(
            f"Nearby {tenure} sites (n={same_summary.get('plot_count')}): "
            f"cover ~{same_summary.get('vegetation_cover')}%, "
            f"NDVI ~{same_summary.get('ndvi')}, "
            f"carrying capacity ~{same_summary.get('carrying_capacity_ha_per_lsu')} ha/LSU."
        )
    for other, block in by_tenure.items():
        if tenure and other == tenure:
            continue
        if not block.get("found"):
            continue
        lines.append(
            f"{other.title()} nearby (n={block.get('plot_count')}): "
            f"cover ~{block.get('vegetation_cover')}%, "
            f"capacity ~{block.get('carrying_capacity_ha_per_lsu')} ha/LSU."
        )

    return {
        "found": True,
        "location": location,
        "matched_on": matched_on,
        "match_value": match_value,
        "farmer_tenure": tenure or None,
        "radius_km": radius_km,
        "same_tenure": same_summary,
        "all_nearby": all_summary,
        "by_tenure": by_tenure,
        "summary": " ".join(lines) if lines else "Tenure peer comparison incomplete.",
        "limitations": [
            "Tenure labels come from the synthetic dataset neighbourhood.",
            "Lacuna field forms do not include land tenure, so peers are synthetic-only.",
        ],
    }
