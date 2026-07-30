"""
Phase 2: Transform raw Lacuna field forms into a farmer-friendly advisory dataset.

Pipeline:
  raw Excel forms → clean/aggregate → data/processed/advisory_dataset.csv (+ .json)

Grain: one row per plot × observation_date (primarily from cover surveys).
No fabricated qualitative scores — only aggregates of measured fields.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

COVER_DIR = RAW_DIR / "fieldform_cover"
GRAZING_DIR = RAW_DIR / "fieldform_grazing"
QUANT_DIR = RAW_DIR / "fieldform_quant"
STANDING_DIR = RAW_DIR / "fieldform_standing"
OTHER_DIR = RAW_DIR / "other_data"
SUPPORT_DIR = RAW_DIR / "supportive_material"

# Filename stem prefixes that differ from plot_name site codes
SITE_CODE_ALIASES = {
    "ghaub": "ghau",
    "nedu": "neud",
}

COVER_GROUPS = [
    "annual_grass",
    "perennial_grass",
    "forb",
    "shrub",
    "short_shrub",
    "tree",
    "litter",
    "bare_ground",
]


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace from column names and collapse spaces."""
    out = df.copy()
    out.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in out.columns]
    return out


def to_numeric_series(series: pd.Series) -> pd.Series:
    """Coerce values to numeric; non-numeric tokens (e.g. NotApp) become NaN."""
    return pd.to_numeric(series, errors="coerce")


def parse_date_series(series: pd.Series) -> pd.Series:
    """Parse survey dates; prefer day-first (DD/MM/YYYY) used in field forms."""
    return pd.to_datetime(series, errors="coerce", dayfirst=True).dt.date


def site_code_from_plot(plot_name: Any) -> str | None:
    if pd.isna(plot_name):
        return None
    text = str(plot_name).strip().lower()
    if not text or "_" not in text:
        # handle rare forms like kmqs4
        match = re.match(r"^([a-z]+)", text)
        return match.group(1) if match else text or None
    code = text.split("_", 1)[0]
    return SITE_CODE_ALIASES.get(code, code)


def normalize_site_code(code: Any) -> str | None:
    if pd.isna(code):
        return None
    text = str(code).strip().lower()
    return SITE_CODE_ALIASES.get(text, text) or None


def find_xlsx(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(folder.rglob("*.xlsx"))


def read_excel_clean(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    return clean_columns(df)


def load_site_registry() -> pd.DataFrame:
    """Sites, ecoregions, and coordinates from supportive material."""
    species_path = next(
        (p for p in find_xlsx(SUPPORT_DIR) if p.name.lower() == "coordinates_and_species.xlsx"),
        None,
    )
    coords_path = next(
        (p for p in find_xlsx(SUPPORT_DIR) if p.name.lower() == "coordinates.xlsx"),
        None,
    )

    if species_path is None:
        raise FileNotFoundError("coordinates_and_species.xlsx not found under supportive_material")

    meta = read_excel_clean(species_path)
    # Expected columns from Phase 1 inspection
    rename = {
        "Ecoregion": "region",
        "Site Name": "site",
        "Plot Name": "plot_name",
        "Latitude": "latitude",
        "Longitude": "longitude",
    }
    meta = meta.rename(columns=rename)
    for col in ["region", "site"]:
        if col in meta.columns:
            meta[col] = meta[col].ffill()

    meta["plot_name"] = meta["plot_name"].astype(str).str.strip().str.lower()
    meta["site_code"] = meta["plot_name"].map(site_code_from_plot)
    meta["latitude"] = to_numeric_series(meta.get("latitude", pd.Series(dtype=float)))
    meta["longitude"] = to_numeric_series(meta.get("longitude", pd.Series(dtype=float)))

    keep = ["plot_name", "site_code", "site", "region", "latitude", "longitude"]
    meta = meta[[c for c in keep if c in meta.columns]].dropna(subset=["plot_name"])
    meta = meta[meta["plot_name"].str.lower() != "nan"]

    # coordinates.xlsx labels are swapped vs geography (long holds lat values).
    # Prefer coordinates_and_species; only fill gaps from coordinates.xlsx after fixing orientation.
    if coords_path is not None:
        try:
            coords = clean_columns(pd.read_excel(coords_path, sheet_name="Coordinates"))
        except ValueError:
            coords = read_excel_clean(coords_path)
        coords = coords.rename(columns={"lat": "latitude", "long": "longitude"})
        coords["plot_name"] = coords["plot_name"].astype(str).str.strip().str.lower()
        coords["latitude"] = to_numeric_series(coords["latitude"])
        coords["longitude"] = to_numeric_series(coords["longitude"])
        swapped = (
            coords["latitude"].between(12, 26, inclusive="both")
            & coords["longitude"].between(-30, -15, inclusive="both")
        )
        if swapped.any():
            coords.loc[swapped, ["latitude", "longitude"]] = coords.loc[
                swapped, ["longitude", "latitude"]
            ].to_numpy()
        coords = coords[["plot_name", "latitude", "longitude"]].drop_duplicates("plot_name")
        meta = meta.merge(coords, on="plot_name", how="left", suffixes=("", "_fallback"))
        meta["latitude"] = meta["latitude"].combine_first(meta.get("latitude_fallback"))
        meta["longitude"] = meta["longitude"].combine_first(meta.get("longitude_fallback"))
        meta = meta.drop(columns=["latitude_fallback", "longitude_fallback"], errors="ignore")

    return meta.drop_duplicates("plot_name")


def load_all_cover() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in find_xlsx(COVER_DIR):
        df = read_excel_clean(path)
        if "plot_name" not in df.columns:
            continue
        df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
        df["source_file"] = path.name
        for col in ["presence", "G%", "NG%", "lat", "long"]:
            if col in df.columns:
                df[col] = to_numeric_series(df[col])
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def aggregate_cover(cover: pd.DataFrame) -> pd.DataFrame:
    if cover.empty:
        return pd.DataFrame()

    cover = cover.copy()
    cover["observation_date"] = parse_date_series(cover["date"])
    cover = cover.dropna(subset=["plot_name", "observation_date", "functional_group"])

    presence = (
        cover.groupby(["plot_name", "observation_date", "functional_group"], as_index=False)[
            "presence"
        ]
        .mean()
        .rename(columns={"presence": "presence_rate"})
    )
    wide = presence.pivot_table(
        index=["plot_name", "observation_date"],
        columns="functional_group",
        values="presence_rate",
        aggfunc="mean",
    ).reset_index()
    wide.columns.name = None

    for group in COVER_GROUPS:
        if group not in wide.columns:
            wide[group] = pd.NA
        wide[group] = (to_numeric_series(wide[group]) * 100).round(2)

    rename = {g: f"cover_{g}_pct" for g in COVER_GROUPS}
    wide = wide.rename(columns=rename)

    # Vegetation cover: mean presence of forage-relevant herbaceous groups
    forage_cols = ["cover_perennial_grass_pct", "cover_annual_grass_pct", "cover_forb_pct"]
    wide["vegetation_cover"] = wide[forage_cols].mean(axis=1, skipna=True).round(2)

    # Bush encroachment signal: woody functional-group presence
    woody_cols = ["cover_shrub_pct", "cover_short_shrub_pct", "cover_tree_pct"]
    wide["bush_encroachment"] = wide[woody_cols].mean(axis=1, skipna=True).round(2)

    # Lat/lon from cover rows (mean) as fallback
    coords = (
        cover.groupby(["plot_name", "observation_date"], as_index=False)
        .agg(cover_lat=("lat", "mean"), cover_lon=("long", "mean"))
    )
    wide = wide.merge(coords, on=["plot_name", "observation_date"], how="left")
    return wide


def load_aggregate_standing() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in find_xlsx(STANDING_DIR):
        df = read_excel_clean(path)
        if "plot_name" not in df.columns:
            continue
        df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
        for col in ["standing_crop_estimate", "max_height", "old_standing_%", "clipped", "lat", "long"]:
            if col in df.columns:
                df[col] = to_numeric_series(df[col])
        df["observation_date"] = parse_date_series(df.get("date"))
        frames.append(df)
    if not frames:
        return pd.DataFrame()

    all_standing = pd.concat(frames, ignore_index=True)
    grouped = (
        all_standing.groupby(["plot_name", "observation_date"], as_index=False)
        .agg(
            standing_crop_mean=("standing_crop_estimate", "mean"),
            standing_max_height_mean=("max_height", "mean"),
            old_standing_pct_mean=("old_standing_%", "mean"),
            standing_n=("standing_crop_estimate", "count"),
        )
    )
    for col in ["standing_crop_mean", "standing_max_height_mean", "old_standing_pct_mean"]:
        grouped[col] = grouped[col].round(2)
    return grouped


def _aggregate_quant_frame(quant: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key_vals, group in quant.groupby(keys, dropna=False):
        if not isinstance(key_vals, tuple):
            key_vals = (key_vals,)
        record = dict(zip(keys, key_vals))
        plant_groups = group["plant_groups"]
        woody = group[plant_groups.isin(["tall_plants", "short_plants", "woody_seedlings"])]
        seedlings = group[plant_groups == "woody_seedlings"]
        height = to_numeric_series(group["height"]) if "height" in group.columns else pd.Series(dtype=float)
        record.update(
            {
                "woody_stem_count": int(len(woody)),
                "woody_seedling_count": int(len(seedlings)),
                "woody_species_count": int(group["woody_species"].dropna().nunique())
                if "woody_species" in group.columns
                else None,
                "mean_woody_height": round(float(height.mean()), 2) if height.notna().any() else None,
            }
        )
        rows.append(record)
    return pd.DataFrame(rows)


def load_aggregate_quant() -> dict[str, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for path in find_xlsx(QUANT_DIR):
        df = read_excel_clean(path)
        if "plot_name" not in df.columns:
            continue
        df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
        for col in ["height", "max_height_canopy_diam", "canopy_diam_1", "canopy_diam_2", "seedlings_number"]:
            if col in df.columns:
                df[col] = to_numeric_series(df[col])
        df["observation_date"] = parse_date_series(df.get("date"))
        frames.append(df)
    if not frames:
        return {"by_date": pd.DataFrame(), "by_plot": pd.DataFrame()}

    quant = pd.concat(frames, ignore_index=True)
    quant["plant_groups"] = (
        quant.get("plant_groups", pd.Series(dtype=str)).astype(str).str.strip().str.lower()
    )

    with_date = quant.dropna(subset=["observation_date"])
    by_date = (
        _aggregate_quant_frame(with_date, ["plot_name", "observation_date"])
        if not with_date.empty
        else pd.DataFrame()
    )
    by_plot = _aggregate_quant_frame(quant, ["plot_name"])
    return {"by_date": by_date, "by_plot": by_plot}


def load_aggregate_grazing() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in find_xlsx(GRAZING_DIR):
        df = read_excel_clean(path)
        if "plot_name" not in df.columns:
            continue
        df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
        df["observation_date"] = parse_date_series(df.get("date"))
        for col in [
            "presence_cattle",
            "number_cattle",
            "presence_sheep",
            "number_sheep",
            "presence_goat",
            "number_goat",
            "rotational_grazing",
            "rainfall",
            "area",
        ]:
            if col in df.columns:
                df[col] = to_numeric_series(df[col])
        frames.append(df)
    if not frames:
        return pd.DataFrame()

    grazing = pd.concat(frames, ignore_index=True)
    keep_cols = [
        "plot_name",
        "observation_date",
        "presence_cattle",
        "number_cattle",
        "presence_sheep",
        "number_sheep",
        "presence_goat",
        "number_goat",
        "rotational_grazing",
        "rainfall",
        "area",
        "livestock_comments",
        "grazing_comments",
    ]
    grazing = grazing[[c for c in keep_cols if c in grazing.columns]]
    grazing = grazing.drop_duplicates(["plot_name", "observation_date"], keep="last")

    # Grazing pressure: total recorded livestock head (measured counts only)
    for col in ["number_cattle", "number_sheep", "number_goat"]:
        if col not in grazing.columns:
            grazing[col] = pd.NA
    grazing["grazing_pressure"] = (
        grazing[["number_cattle", "number_sheep", "number_goat"]].sum(axis=1, min_count=1)
    )
    return grazing.rename(columns={"rainfall": "recorded_rainfall_mm"})


def load_biomass() -> pd.DataFrame:
    path = next((p for p in find_xlsx(OTHER_DIR) if p.name.lower() == "biomass.xlsx"), None)
    if path is None:
        return pd.DataFrame()
    df = read_excel_clean(path)
    df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
    df["biomass_before"] = to_numeric_series(df["biomass_before"])
    df["biomass_after"] = to_numeric_series(df["biomass_after"])
    grouped = (
        df.groupby("plot_name", as_index=False)
        .agg(
            biomass_before_mean=("biomass_before", "mean"),
            biomass_after_mean=("biomass_after", "mean"),
            biomass_n=("biomass_after", "count"),
        )
    )
    grouped["biomass_before_mean"] = grouped["biomass_before_mean"].round(2)
    grouped["biomass_after_mean"] = grouped["biomass_after_mean"].round(2)
    # Prefer oven-dry / after value when present
    grouped["biomass"] = grouped["biomass_after_mean"].combine_first(grouped["biomass_before_mean"])
    return grouped


def load_dominant_species() -> pd.DataFrame:
    path = next(
        (p for p in find_xlsx(OTHER_DIR) if p.name.lower() == "dominant_species.xlsx"),
        None,
    )
    if path is None:
        return pd.DataFrame()
    df = read_excel_clean(path)
    df["plot_name"] = df["plot_name"].astype(str).str.strip().str.lower()
    df["plant_type"] = df["plant_type"].astype(str).str.strip().str.lower()
    df["species_name"] = df["species_name"].astype(str).str.strip()

    rows: list[dict[str, Any]] = []
    for plot_name, group in df.groupby("plot_name"):
        herb = group.loc[group["plant_type"].str.startswith("herbaceous"), "species_name"]
        woody = group.loc[group["plant_type"].str.startswith("woody"), "species_name"]
        rows.append(
            {
                "plot_name": plot_name,
                "dominant_herbaceous": ", ".join(sorted(herb.dropna().unique())),
                "dominant_woody": ", ".join(sorted(woody.dropna().unique())),
            }
        )
    return pd.DataFrame(rows)


def build_advisory_dataset() -> pd.DataFrame:
    print("Loading site registry...")
    sites = load_site_registry()
    print(f"  plots in registry: {len(sites)}")

    print("Loading and aggregating cover...")
    cover = aggregate_cover(load_all_cover())
    print(f"  cover plot-date rows: {len(cover)}")

    print("Loading standing crop...")
    standing = load_aggregate_standing()
    print(f"  standing rows: {len(standing)}")

    print("Loading quant (woody)...")
    quant_parts = load_aggregate_quant()
    quant_by_date = quant_parts["by_date"]
    quant_by_plot = quant_parts["by_plot"]
    print(f"  quant by date: {len(quant_by_date)} | by plot: {len(quant_by_plot)}")

    print("Loading grazing...")
    grazing = load_aggregate_grazing()
    print(f"  grazing rows: {len(grazing)}")

    print("Loading biomass + dominant species...")
    biomass = load_biomass()
    species = load_dominant_species()
    print(f"  biomass plots: {len(biomass)} | species plots: {len(species)}")

    # Cover rows are the spine (richest seasonal coverage)
    advisory = cover.merge(sites, on="plot_name", how="left")

    if not standing.empty:
        advisory = advisory.merge(standing, on=["plot_name", "observation_date"], how="left")
    if not quant_by_date.empty:
        advisory = advisory.merge(quant_by_date, on=["plot_name", "observation_date"], how="left")
    if not grazing.empty:
        advisory = advisory.merge(grazing, on=["plot_name", "observation_date"], how="left")
    if not biomass.empty:
        advisory = advisory.merge(biomass, on="plot_name", how="left")
    if not species.empty:
        advisory = advisory.merge(species, on="plot_name", how="left")

    # Fill woody metrics from plot-level quant when date-aligned quant is missing
    if not quant_by_plot.empty:
        woody_cols = [
            "woody_stem_count",
            "woody_seedling_count",
            "woody_species_count",
            "mean_woody_height",
        ]
        plot_woody = quant_by_plot[["plot_name"] + [c for c in woody_cols if c in quant_by_plot.columns]]
        advisory = advisory.merge(plot_woody, on="plot_name", how="left", suffixes=("", "_plot"))
        for col in woody_cols:
            plot_col = f"{col}_plot"
            if col in advisory.columns and plot_col in advisory.columns:
                advisory[col] = advisory[col].combine_first(advisory[plot_col])
                advisory = advisory.drop(columns=[plot_col])
            elif plot_col in advisory.columns:
                advisory = advisory.rename(columns={plot_col: col})

    # Fill missing site_code / coords
    advisory["site_code"] = advisory["site_code"].fillna(advisory["plot_name"].map(site_code_from_plot))
    if "latitude" in advisory.columns and "cover_lat" in advisory.columns:
        advisory["latitude"] = advisory["latitude"].combine_first(advisory["cover_lat"])
    if "longitude" in advisory.columns and "cover_lon" in advisory.columns:
        advisory["longitude"] = advisory["longitude"].combine_first(advisory["cover_lon"])

    # Prefer clipped biomass; else standing crop mean as biomass proxy field only when biomass missing
    if "biomass" not in advisory.columns:
        advisory["biomass"] = pd.NA
    if "standing_crop_mean" in advisory.columns:
        advisory["biomass"] = advisory["biomass"].combine_first(advisory["standing_crop_mean"])

    # pasture_condition intentionally left null — no qualitative label in source data
    advisory["pasture_condition"] = pd.NA

    # Final column order for tools / DB
    ordered = [
        "region",
        "site",
        "site_code",
        "plot_name",
        "latitude",
        "longitude",
        "observation_date",
        "biomass",
        "biomass_before_mean",
        "biomass_after_mean",
        "standing_crop_mean",
        "vegetation_cover",
        "bush_encroachment",
        "cover_perennial_grass_pct",
        "cover_annual_grass_pct",
        "cover_forb_pct",
        "cover_shrub_pct",
        "cover_short_shrub_pct",
        "cover_tree_pct",
        "cover_litter_pct",
        "cover_bare_ground_pct",
        "woody_stem_count",
        "woody_seedling_count",
        "woody_species_count",
        "mean_woody_height",
        "grazing_pressure",
        "presence_cattle",
        "number_cattle",
        "presence_sheep",
        "number_sheep",
        "presence_goat",
        "number_goat",
        "rotational_grazing",
        "recorded_rainfall_mm",
        "dominant_herbaceous",
        "dominant_woody",
        "pasture_condition",
        "livestock_comments",
        "grazing_comments",
    ]
    for col in ordered:
        if col not in advisory.columns:
            advisory[col] = pd.NA
    extra = [c for c in advisory.columns if c not in ordered and c not in ("cover_lat", "cover_lon")]
    advisory = advisory[ordered + extra].drop(columns=["cover_lat", "cover_lon"], errors="ignore")

    advisory = advisory.sort_values(["site", "plot_name", "observation_date"], na_position="last")
    return advisory.reset_index(drop=True)


def records_for_json(df: pd.DataFrame) -> list[dict[str, Any]]:
    out = df.copy()
    if "observation_date" in out.columns:
        out["observation_date"] = out["observation_date"].astype(str).replace("NaT", None)
    # Convert NaN/NaT to None for clean JSON
    return json.loads(out.to_json(orient="records", date_format="iso"))


def write_outputs(df: pd.DataFrame) -> dict[str, Path]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED_DIR / "advisory_dataset.csv"
    json_path = PROCESSED_DIR / "advisory_dataset.json"
    summary_path = PROCESSED_DIR / "advisory_dataset_summary.json"

    df.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(records_for_json(df), indent=2), encoding="utf-8")

    summary = {
        "rows": int(len(df)),
        "sites": sorted(df["site"].dropna().astype(str).unique().tolist()),
        "site_codes": sorted(df["site_code"].dropna().astype(str).unique().tolist()),
        "regions": sorted(df["region"].dropna().astype(str).unique().tolist()),
        "date_range": {
            "min": str(df["observation_date"].min()) if len(df) else None,
            "max": str(df["observation_date"].max()) if len(df) else None,
        },
        "columns": list(df.columns),
        "null_rates": {
            col: round(float(df[col].isna().mean()), 3) for col in df.columns
        },
        "field_notes": {
            "vegetation_cover": "Mean presence % of perennial_grass, annual_grass, and forb.",
            "bush_encroachment": "Mean presence % of shrub, short_shrub, and tree.",
            "grazing_pressure": "Sum of recorded cattle + sheep + goat head counts when available.",
            "biomass": "Prefer Biomass.xlsx biomass_after mean; else standing_crop_mean.",
            "pasture_condition": "Left null — source data has no qualitative condition label.",
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "summary": summary_path}


def main() -> None:
    advisory = build_advisory_dataset()
    paths = write_outputs(advisory)

    print("\n=== Phase 2 complete ===")
    print(f"Rows: {len(advisory)}")
    print(f"Sites: {advisory['site'].nunique(dropna=True)}")
    print(f"CSV:  {paths['csv']}")
    print(f"JSON: {paths['json']}")
    print(f"Summary: {paths['summary']}")
    print("\nSample rows:")
    cols = [
        "region",
        "site",
        "plot_name",
        "observation_date",
        "vegetation_cover",
        "bush_encroachment",
        "biomass",
        "grazing_pressure",
    ]
    print(advisory[cols].head(8).to_string(index=False))


if __name__ == "__main__":
    main()
