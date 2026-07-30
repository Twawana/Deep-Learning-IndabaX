"""
Load advisory rangeland rows from Supabase tables.

- range_sites: advisory schema (Lacuna + previously merged synthetic)
- range_landsites: raw synthetic survey → mapped onto advisory columns

When both are present, Lacuna rows come from range_sites and synthetic rows
are rebuilt from range_landsites so edits in Supabase stay live.
"""

from __future__ import annotations

import os
import re
from typing import Any

import pandas as pd

from services import supabase_client

SYNTHETIC_SOURCE = "synthetic_v2"
LACUNA_SOURCE = "lacuna_field"

BUSH_LEVEL_TO_PCT = {
    "low": 12.0,
    "moderate": 35.0,
    "medium": 35.0,
    "high": 55.0,
    "severe": 65.0,
}


def use_supabase_datasets() -> bool:
    mode = (os.getenv("DATA_SOURCE") or "auto").strip().lower()
    if mode in {"csv", "local", "file"}:
        return False
    if mode in {"supabase", "remote"}:
        return supabase_client.is_configured()
    # auto
    return supabase_client.is_configured()


def _site_code(site_id: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(site_id).strip().lower()).strip("-")
    return text[:24] or "synth"


def map_landsites_to_advisory(raw: pd.DataFrame) -> pd.DataFrame:
    """Map range_landsites columns onto the advisory schema."""
    if raw.empty:
        return raw.copy()

    df = raw.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]

    bush_level = (
        df.get("bush_encroachment_level", pd.Series(dtype=str))
        .astype(str)
        .str.strip()
        .str.lower()
    )
    bush_pct = bush_level.map(BUSH_LEVEL_TO_PCT)

    site_id = df["site_id"].astype(str).str.strip()
    grazing_label = df.get("grazing_pressure", pd.Series(dtype=str)).astype(str).str.strip()
    browsing_label = df.get("browsing_pressure", pd.Series(dtype=str)).astype(str).str.strip()

    return pd.DataFrame(
        {
            "region": df["region"].astype(str).str.strip(),
            "site": site_id,
            "site_code": site_id.map(_site_code),
            "plot_name": site_id.str.lower(),
            "latitude": pd.to_numeric(df["latitude"], errors="coerce"),
            "longitude": pd.to_numeric(df["longitude"], errors="coerce"),
            "observation_date": pd.to_datetime(df["survey_date"], errors="coerce"),
            "biomass": pd.to_numeric(df["grass_biomass_kg_per_ha"], errors="coerce").round(2),
            "vegetation_cover": pd.to_numeric(
                df["vegetation_cover_percent"], errors="coerce"
            ).round(2),
            "bush_encroachment": bush_pct.round(2),
            "bush_encroachment_level": df.get("bush_encroachment_level"),
            "ndvi": pd.to_numeric(df["ndvi"], errors="coerce").round(3),
            "grass_biomass_kg_per_ha": pd.to_numeric(
                df["grass_biomass_kg_per_ha"], errors="coerce"
            ).round(2),
            "bush_biomass_kg_per_ha": pd.to_numeric(
                df["bush_biomass_kg_per_ha"], errors="coerce"
            ).round(2),
            "recorded_rainfall_mm": pd.to_numeric(
                df["rainfall_last_30_days_mm"], errors="coerce"
            ).round(2),
            "livestock_density_lsu_per_ha": pd.to_numeric(
                df["livestock_density_lsu_per_ha"], errors="coerce"
            ).round(4),
            "carrying_capacity_ha_per_lsu": pd.to_numeric(
                df["estimated_carrying_capacity_ha_per_lsu"], errors="coerce"
            ).round(2),
            "grazing_pressure_label": grazing_label,
            "browsing_pressure_label": browsing_label,
            "grazing_pressure": pd.NA,
            "dominant_herbaceous": df.get("dominant_plant_species"),
            "dominant_woody": pd.NA,
            "pasture_condition": grazing_label,
            "season": df.get("season"),
            "land_tenure": df.get("land_tenure"),
            "data_source_note": df.get("data_source"),
            "dataset_source": SYNTHETIC_SOURCE,
            "grazing_comments": (
                "Synthetic survey · grazing "
                + grazing_label
                + " · browsing "
                + browsing_label
            ),
            "livestock_comments": pd.NA,
        }
    )


def _normalize_advisory_frame(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in ["site", "site_code", "region", "plot_name"]:
        if col in out.columns:
            out[col] = out[col].where(out[col].notna(), None)
            out[col] = out[col].apply(lambda v: str(v) if v is not None else None)
    if "observation_date" in out.columns:
        out["observation_date"] = pd.to_datetime(out["observation_date"], errors="coerce")
    return out


def load_advisory_from_supabase() -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Build the runtime advisory dataframe from Supabase.

    Returns (dataframe, meta) where meta describes sources used.
    """
    if not supabase_client.is_configured():
        raise supabase_client.SupabaseError("Supabase is not configured.")

    sites_rows = supabase_client.fetch_all("range_sites")
    lands_rows = supabase_client.fetch_all("range_landsites")

    sites_df = pd.DataFrame(sites_rows) if sites_rows else pd.DataFrame()
    lands_df = pd.DataFrame(lands_rows) if lands_rows else pd.DataFrame()

    meta: dict[str, Any] = {
        "source": "supabase",
        "range_sites_rows": int(len(sites_df)),
        "range_landsites_rows": int(len(lands_df)),
    }

    if sites_df.empty and lands_df.empty:
        raise supabase_client.SupabaseError(
            "Supabase tables range_sites and range_landsites returned no rows."
        )

    if not lands_df.empty and "site_id" in lands_df.columns:
        synthetic = map_landsites_to_advisory(lands_df)
        if not sites_df.empty and "dataset_source" in sites_df.columns:
            lacuna = sites_df.loc[
                sites_df["dataset_source"].astype(str) != SYNTHETIC_SOURCE
            ].copy()
        elif not sites_df.empty:
            # No source column — keep all site rows and append mapped landsites
            lacuna = sites_df.copy()
        else:
            lacuna = pd.DataFrame()
        combined = pd.concat([lacuna, synthetic], ignore_index=True, sort=False)
        meta["compose"] = "lacuna_from_range_sites + synthetic_from_range_landsites"
        meta["rows"] = int(len(combined))
        return _normalize_advisory_frame(combined), meta

    meta["compose"] = "range_sites_only"
    meta["rows"] = int(len(sites_df))
    return _normalize_advisory_frame(sites_df), meta
