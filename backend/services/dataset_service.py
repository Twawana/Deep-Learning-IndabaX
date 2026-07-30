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

# Farmer-friendly place names → dataset SITE names (prefer sites over whole ecoregions).
# Only maps to real sites present in the processed data.
PLACE_ALIASES: dict[str, str] = {
    # Gobabis area → Molly (Central Kalahari); Cala is also nearby but Molly is the default.
    "gobabis": "Molly",
    "windhoek": "Neudamm",
    "keetmanshoop": "Keetmanshop",
    "keetmanshop": "Keetmanshop",
    "katima": "Katima Mulilo Quarantine Station",
    "katima mulilo": "Katima Mulilo Quarantine Station",
    "otjiwarongo": "Lardner",
    "outjo": "Ghaub",
}

# Minimum query length for fuzzy "site name contains query" matching.
MIN_PARTIAL_QUERY_LEN = 4


def _dataset_path() -> Path:
    env_path = os.getenv("ADVISORY_DATASET_PATH")
    if not env_path:
        return DEFAULT_DATASET_PATH
    path = Path(env_path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


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
            # Avoid turning real NaN into the string "nan"
            df[col] = df[col].where(df[col].notna(), None)
            df[col] = df[col].apply(lambda v: str(v) if v is not None else None)
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

    Matching order (tightened to avoid short-substring false hits):
    1. Exact alias
    2. Exact site / site_code / region / plot
    3. Partial only if query length >= MIN_PARTIAL_QUERY_LEN
       and (query is contained in site name OR site name is contained in query)
    """
    q = _norm(query)
    if not q:
        return "unresolved", query

    if q in PLACE_ALIASES:
        return "alias", PLACE_ALIASES[q]

    df = load_advisory_dataframe()

    sites = {_norm(s): s for s in df["site"].dropna().unique()}
    if q in sites:
        return "site", sites[q]

    codes = {_norm(c): c for c in df["site_code"].dropna().unique()}
    if q in codes:
        return "site_code", codes[q]

    regions = {_norm(r): r for r in df["region"].dropna().unique()}
    if q in regions:
        return "region", regions[q]

    plots = {_norm(p): p for p in df["plot_name"].dropna().unique()}
    if q in plots:
        return "plot_name", plots[q]

    # Safe partial for sites only. Regions stay exact-match (above) so
    # fragments like "highland" do not pull entire ecoregions.
    if len(q) >= MIN_PARTIAL_QUERY_LEN:
        site_hits = [
            original
            for original in sites.values()
            if _token_match(q, _norm(original))
        ]
        if site_hits:
            site_hits.sort(key=lambda s: (abs(len(_norm(s)) - len(q)), len(s)))
            return "site", site_hits[0]

    return "unresolved", query


def _token_match(query: str, candidate: str) -> bool:
    """
    Match when query equals candidate, or the farmer typed the site name plus
    extra words. Single-token queries only match the *first* token of a site
    (or a prefix of it) so fragments like "west" / "station" / "highland"
    do not hitch onto trailing qualifiers.
    """
    if not query or not candidate:
        return False
    if query == candidate:
        return True

    q_tokens = query.split()
    c_tokens = candidate.split()

    # Candidate name appears as a contiguous phrase inside a longer farmer query
    # e.g. "molly farm" → Molly
    if len(candidate) >= MIN_PARTIAL_QUERY_LEN and len(c_tokens) <= len(q_tokens):
        for i in range(len(q_tokens) - len(c_tokens) + 1):
            if q_tokens[i : i + len(c_tokens)] == c_tokens:
                return True

    # Multi-token query: require contiguous phrase inside candidate
    if len(q_tokens) >= 2:
        for i in range(len(c_tokens) - len(q_tokens) + 1):
            if c_tokens[i : i + len(q_tokens)] == q_tokens:
                return True
        return False

    # Single-token query: only match against the primary (first) token
    q = q_tokens[0]
    first = c_tokens[0]
    if len(q) < MIN_PARTIAL_QUERY_LEN:
        return False
    if first == q:
        return True
    # Prefix either way for typos / short forms of the primary name
    if len(first) >= MIN_PARTIAL_QUERY_LEN and (
        first.startswith(q) or q.startswith(first)
    ):
        return True
    return False


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

    if matched_on == "alias":
        site_hit = df["site"].str.lower() == search_term.lower()
        region_hit = df["region"].str.lower() == search_term.lower()
        if site_hit.any():
            return df.loc[site_hit].copy(), "alias->site", search_term
        if region_hit.any():
            return df.loc[region_hit].copy(), "alias->region", search_term
        return pd.DataFrame(), "unresolved", None

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


def nearest_site_by_coordinates(
    latitude: float,
    longitude: float,
    *,
    max_distance_km: float = 150.0,
) -> Optional[tuple[str, float]]:
    """
    Find nearest research site by mean plot coordinates.
    Returns (site_name, distance_km) or None if nothing within max_distance_km.
    """
    df = load_advisory_dataframe()
    latest = latest_per_plot(df)
    if latest.empty:
        return None

    rows: list[tuple[str, float]] = []
    for site, group in latest.groupby("site"):
        if site is None or str(site).lower() in {"none", "nan"}:
            continue
        lat = pd.to_numeric(group["latitude"], errors="coerce").mean()
        lon = pd.to_numeric(group["longitude"], errors="coerce").mean()
        if pd.isna(lat) or pd.isna(lon):
            continue
        dist = _haversine_km(latitude, longitude, float(lat), float(lon))
        rows.append((str(site), dist))

    if not rows:
        return None
    rows.sort(key=lambda item: item[1])
    site, dist = rows[0]
    if dist > max_distance_km:
        return None
    return site, dist


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


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


def list_sites() -> list[dict[str, Any]]:
    df = load_advisory_dataframe()
    latest = latest_per_plot(df)
    rows: list[dict[str, Any]] = []
    for site, group in latest.groupby("site"):
        if site is None or str(site).lower() in {"none", "nan"}:
            continue
        lat = pd.to_numeric(group["latitude"], errors="coerce").mean() if "latitude" in group.columns else None
        lon = pd.to_numeric(group["longitude"], errors="coerce").mean() if "longitude" in group.columns else None
        cover = (
            pd.to_numeric(group["vegetation_cover"], errors="coerce").mean()
            if "vegetation_cover" in group.columns
            else None
        )
        biomass = (
            pd.to_numeric(group["biomass"], errors="coerce").mean()
            if "biomass" in group.columns
            else None
        )
        region = None
        if "region" in group.columns and group["region"].notna().any():
            region = str(group["region"].dropna().iloc[0])
        code = None
        if "site_code" in group.columns and group["site_code"].notna().any():
            code = str(group["site_code"].dropna().iloc[0])
        source = None
        if "dataset_source" in group.columns and group["dataset_source"].notna().any():
            source = str(group["dataset_source"].dropna().iloc[0])
        rows.append(
            {
                "site": str(site),
                "site_code": code,
                "region": region,
                "latitude": None if pd.isna(lat) else round(float(lat), 5),
                "longitude": None if pd.isna(lon) else round(float(lon), 5),
                "vegetation_cover": None if cover is None or pd.isna(cover) else round(float(cover), 2),
                "biomass": None if biomass is None or pd.isna(biomass) else round(float(biomass), 2),
                "dataset_source": source,
            }
        )
    rows.sort(key=lambda r: r["site"])
    return rows


def list_supported_place_aliases() -> list[dict[str, str]]:
    """Aliases the API accepts for farmer-friendly town names."""
    return [
        {"query": key, "maps_to": value}
        for key, value in sorted(PLACE_ALIASES.items())
    ]
