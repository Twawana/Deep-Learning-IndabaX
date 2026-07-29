"""
Load and query the processed advisory dataset.

AI agents and API routes should use this service — never raw Excel research files.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = ROOT / "data" / "processed" / "advisory_dataset.csv"

# Farmer-friendly place names → dataset site / region search terms.
# Only maps to real sites/ecoregions present in the processed data.
PLACE_ALIASES: dict[str, str] = {
    "gobabis": "Central Kalahari",
    "windhoek": "Neudamm",
    "keetmanshoop": "Keetmanshop",
    "katima": "Katima Mulilo Quarantine Station",
    "katima mulilo": "Katima Mulilo Quarantine Station",
    "otjiwarongo": "Lardner",
    "outjo": "Ghaub",
}


def _dataset_path() -> Path:
    env_path = os.getenv("ADVISORY_DATASET_PATH")
    return Path(env_path) if env_path else DEFAULT_DATASET_PATH


@lru_cache(maxsize=1)
def load_advisory_dataframe() -> pd.DataFrame:
    path = _dataset_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {path}. "
            "Run: python scripts/process_dataset.py"
        )
    df = pd.read_csv(path)
    for col in ["site", "site_code", "region", "plot_name"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
    if "observation_date" in df.columns:
        df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
    return df


def reload_dataset() -> pd.DataFrame:
    """Clear cache and reload (useful after reprocessing)."""
    load_advisory_dataframe.cache_clear()
    return load_advisory_dataframe()


def _norm(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def resolve_query(query: str) -> tuple[str, str]:
    """
    Resolve a farmer query to (matched_on, match_value).

    matched_on is one of: alias, site, site_code, region, plot_name, unresolved
    """
    q = _norm(query)
    if not q:
        return "unresolved", query

    if q in PLACE_ALIASES:
        return "alias", PLACE_ALIASES[q]

    df = load_advisory_dataframe()

    # Exact site
    sites = { _norm(s): s for s in df["site"].dropna().unique() }
    if q in sites:
        return "site", sites[q]

    # Exact site code
    codes = { _norm(c): c for c in df["site_code"].dropna().unique() }
    if q in codes:
        return "site_code", codes[q]

    # Exact region / ecoregion
    regions = { _norm(r): r for r in df["region"].dropna().unique() }
    if q in regions:
        return "region", regions[q]

    # Exact plot
    plots = { _norm(p): p for p in df["plot_name"].dropna().unique() }
    if q in plots:
        return "plot_name", plots[q]

    # Partial contains (site first, then region)
    for original in sorted(sites.values(), key=len):
        if q in _norm(original) or _norm(original) in q:
            return "site", original
    for original in sorted(regions.values(), key=len, reverse=True):
        if q in _norm(original) or _norm(original) in q:
            return "region", original

    return "unresolved", query


def filter_by_query(query: str) -> tuple[pd.DataFrame, str, Optional[str]]:
    """
    Return (filtered_df, matched_on, match_value).
    Empty dataframe when nothing matches.
    """
    matched_on, match_value = resolve_query(query)
    if matched_on == "unresolved":
        return pd.DataFrame(), matched_on, None

    df = load_advisory_dataframe()
    search_term = match_value

    # Alias resolves to a site or region string — detect which.
    if matched_on == "alias":
        site_hit = df["site"].str.lower() == search_term.lower()
        region_hit = df["region"].str.lower() == search_term.lower()
        if site_hit.any():
            return df.loc[site_hit].copy(), "alias->site", search_term
        if region_hit.any():
            return df.loc[region_hit].copy(), "alias->region", search_term
        # Partial region/site for alias target
        mask = (
            df["site"].str.lower().str.contains(search_term.lower(), na=False)
            | df["region"].str.lower().str.contains(search_term.lower(), na=False)
        )
        return df.loc[mask].copy(), "alias", search_term

    if matched_on == "site":
        return df.loc[df["site"] == search_term].copy(), matched_on, search_term
    if matched_on == "site_code":
        return df.loc[df["site_code"] == search_term].copy(), matched_on, search_term
    if matched_on == "region":
        return df.loc[df["region"] == search_term].copy(), matched_on, search_term
    if matched_on == "plot_name":
        return df.loc[df["plot_name"] == search_term].copy(), matched_on, search_term

    return pd.DataFrame(), "unresolved", None


def latest_per_plot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "observation_date" not in df.columns:
        return df
    ordered = df.sort_values("observation_date", ascending=False)
    return ordered.drop_duplicates(subset=["plot_name"], keep="first")


def representative_coordinates(df: pd.DataFrame) -> Optional[tuple[float, float, dict[str, Any]]]:
    """
    Mean lat/lon of matching plots (from latest observations).
    Returns (lat, lon, meta) or None.
    """
    latest = latest_per_plot(df)
    if latest.empty:
        return None
    if "latitude" not in latest.columns or "longitude" not in latest.columns:
        return None
    lat = pd.to_numeric(latest["latitude"], errors="coerce").mean()
    lon = pd.to_numeric(latest["longitude"], errors="coerce").mean()
    if pd.isna(lat) or pd.isna(lon):
        return None
    meta = {
        "site": latest["site"].dropna().iloc[0] if latest["site"].notna().any() else None,
        "region": latest["region"].dropna().iloc[0] if latest["region"].notna().any() else None,
        "plot_count": int(latest["plot_name"].nunique()),
    }
    return float(lat), float(lon), meta


def row_to_dict(row: pd.Series) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in row.items():
        if pd.isna(value):
            data[key] = None
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()[:10]
        elif hasattr(value, "item"):
            try:
                data[key] = value.item()
            except (ValueError, AttributeError):
                data[key] = value
        else:
            data[key] = value
    return data


def list_sites() -> list[dict[str, str]]:
    df = load_advisory_dataframe()
    cols = [c for c in ["site", "site_code", "region"] if c in df.columns]
    return (
        df[cols]
        .drop_duplicates()
        .sort_values("site")
        .to_dict(orient="records")
    )
