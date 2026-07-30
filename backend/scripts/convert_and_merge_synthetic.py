"""
Convert Namibia synthetic .numbers workbook to CSV and merge into the
processed advisory dataset used at runtime.

Sources:
  data/raw/Namibia_Rangeland_Pasture_Synthetic_Dataset_2.numbers  (preferred)
  data/raw/Namibia_Rangeland_Pasture_Synthetic_Dataset_2.csv      (already converted)

Output:
  data/raw/..._2.csv                         — flat export of the workbook
  data/processed/synthetic_dataset.csv       — same rows, archived
  data/processed/advisory_dataset.csv        — Lacuna field rows + mapped synthetic
  data/processed/advisory_dataset_summary.json
"""

from __future__ import annotations

import json
import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

NUMBERS_NAME = "Namibia_Rangeland_Pasture_Synthetic_Dataset_2.numbers"
CSV_NAME = "Namibia_Rangeland_Pasture_Synthetic_Dataset_2.csv"
SYNTHETIC_SOURCE = "synthetic_v2"
LACUNA_SOURCE = "lacuna_field"

BUSH_LEVEL_TO_PCT = {
    "low": 12.0,
    "moderate": 35.0,
    "medium": 35.0,
    "high": 55.0,
    "severe": 65.0,
}


def convert_numbers_to_csv(
    numbers_path: Path | None = None,
    csv_path: Path | None = None,
) -> Path:
    """Read Apple Numbers workbook and write a CSV beside it."""
    numbers_path = numbers_path or (RAW_DIR / NUMBERS_NAME)
    csv_path = csv_path or (RAW_DIR / CSV_NAME)

    if not numbers_path.exists():
        if csv_path.exists():
            print(f"Numbers file missing; reusing existing CSV: {csv_path}")
            return csv_path
        raise FileNotFoundError(f"Missing both {numbers_path} and {csv_path}")

    try:
        from numbers_parser import Document
    except ImportError as exc:
        if csv_path.exists():
            print("numbers-parser not installed; reusing existing CSV.")
            return csv_path
        raise ImportError(
            "Install numbers-parser to convert .numbers files: pip install numbers-parser"
        ) from exc

    print(f"Reading {numbers_path.name}…")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = Document(str(numbers_path))

    table = doc.sheets[0].tables[0]
    headers = [table.cell(0, c).value for c in range(table.num_cols)]
    rows: list[list[Any]] = []
    for r in range(1, table.num_rows):
        row = [table.cell(r, c).value for c in range(table.num_cols)]
        if all(v is None or v == "" for v in row):
            continue
        rows.append(row)

    df = pd.DataFrame(rows, columns=headers)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"Wrote {len(df)} rows -> {csv_path}")
    return csv_path


def _site_code(site_id: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(site_id).strip().lower()).strip("-")
    return text[:24] or "synth"


def map_synthetic_to_advisory(raw: pd.DataFrame) -> pd.DataFrame:
    """Map synthetic columns onto the advisory schema (+ extra synthetic fields)."""
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

    out = pd.DataFrame(
        {
            "region": df["region"].astype(str).str.strip(),
            "site": site_id,
            "site_code": site_id.map(_site_code),
            "plot_name": site_id.str.lower(),
            "latitude": pd.to_numeric(df["latitude"], errors="coerce"),
            "longitude": pd.to_numeric(df["longitude"], errors="coerce"),
            "observation_date": pd.to_datetime(df["survey_date"], errors="coerce").dt.date,
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
            # Keep numeric grazing_pressure empty — Lacuna uses head counts.
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
    return out


def _write_summary(df: pd.DataFrame, path: Path) -> None:
    summary = {
        "rows": int(len(df)),
        "by_dataset_source": (
            df["dataset_source"].fillna("unknown").value_counts().to_dict()
            if "dataset_source" in df.columns
            else {}
        ),
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
            "vegetation_cover": "Lacuna: mean forage presence %. Synthetic: vegetation_cover_percent.",
            "biomass": (
                "Lacuna: field biomass / standing crop. "
                "Synthetic: grass_biomass_kg_per_ha (typically larger scale)."
            ),
            "bush_encroachment": (
                "Lacuna: woody presence %. "
                "Synthetic: mapped from bush_encroachment_level "
                "(Low=12, Moderate=35, Severe=65)."
            ),
            "ndvi": "Synthetic only.",
            "carrying_capacity_ha_per_lsu": "Synthetic only (ha per LSU).",
            "grazing_pressure": "Lacuna head-count sum. Synthetic leaves blank; see grazing_pressure_label.",
            "dataset_source": f"'{LACUNA_SOURCE}' or '{SYNTHETIC_SOURCE}'.",
        },
    }
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


def merge_into_advisory(synthetic: pd.DataFrame) -> pd.DataFrame:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    advisory_path = PROCESSED_DIR / "advisory_dataset.csv"
    if not advisory_path.exists():
        print("No existing advisory_dataset.csv — writing synthetic-only dataset.")
        combined = synthetic.copy()
    else:
        existing = pd.read_csv(advisory_path)
        if "dataset_source" not in existing.columns:
            existing["dataset_source"] = LACUNA_SOURCE
        else:
            existing["dataset_source"] = existing["dataset_source"].fillna(LACUNA_SOURCE)
        # Drop previous synthetic rows so re-runs are idempotent
        keep = existing[existing["dataset_source"] != SYNTHETIC_SOURCE].copy()
        print(f"Keeping {len(keep)} non-synthetic rows; adding {len(synthetic)} synthetic.")
        combined = pd.concat([keep, synthetic], ignore_index=True, sort=False)

    # Ensure core columns exist
    for col in [
        "region",
        "site",
        "site_code",
        "plot_name",
        "latitude",
        "longitude",
        "observation_date",
        "biomass",
        "vegetation_cover",
        "bush_encroachment",
        "dataset_source",
    ]:
        if col not in combined.columns:
            combined[col] = pd.NA

    # Normalize dates to ISO strings so Lacuna + synthetic concat cleanly
    combined["observation_date"] = (
        pd.to_datetime(combined["observation_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
        .replace({"NaT": None})
    )

    combined = combined.sort_values(
        ["dataset_source", "region", "site", "observation_date"],
        na_position="last",
    ).reset_index(drop=True)

    # Archive mapped synthetic alone
    synthetic_out = PROCESSED_DIR / "synthetic_dataset.csv"
    synthetic.to_csv(synthetic_out, index=False)

    combined.to_csv(advisory_path, index=False)
    _write_summary(combined, PROCESSED_DIR / "advisory_dataset_summary.json")
    print(f"Advisory rows: {len(combined)} -> {advisory_path}")
    print(f"Synthetic archive -> {synthetic_out}")
    return combined


def main() -> None:
    csv_path = convert_numbers_to_csv()
    raw = pd.read_csv(csv_path)
    mapped = map_synthetic_to_advisory(raw)
    combined = merge_into_advisory(mapped)
    print("\nSample synthetic-mapped rows:")
    cols = [
        "region",
        "site",
        "observation_date",
        "vegetation_cover",
        "biomass",
        "ndvi",
        "carrying_capacity_ha_per_lsu",
        "dataset_source",
    ]
    print(combined.loc[combined["dataset_source"] == SYNTHETIC_SOURCE, cols].head(5).to_string(index=False))
    print(
        "\nSources:",
        combined["dataset_source"].value_counts().to_dict(),
    )


if __name__ == "__main__":
    main()
