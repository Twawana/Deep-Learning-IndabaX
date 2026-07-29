"""
Phase 1: Discover Lacuna dataset structure without assuming columns.

Walks backend/data/raw, lists folders/files, and prints sheet names,
columns, dtypes, sample rows, and null counts for each Excel workbook.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REPORT_PATH = ROOT / "data" / "processed" / "dataset_inspection_report.json"

# Cap how many workbooks of each type we fully open (all unique schemas still covered).
MAX_SAMPLES_PER_FOLDER = 3


def list_tree(base: Path, max_depth: int = 3) -> list[str]:
    lines: list[str] = []
    if not base.exists():
        return [f"MISSING: {base}"]

    def walk(path: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            lines.append(f"{'  ' * depth}[permission denied] {path.name}")
            return
        for child in children:
            prefix = "  " * depth
            if child.is_dir():
                n_files = sum(1 for _ in child.rglob("*") if _.is_file())
                lines.append(f"{prefix}[DIR] {child.name}/  ({n_files} files)")
                walk(child, depth + 1)
            else:
                size_kb = child.stat().st_size / 1024
                lines.append(f"{prefix}[FILE] {child.name}  ({size_kb:.1f} KB)")

    walk(base, 0)
    return lines


def collect_excel_files(raw_dir: Path) -> dict[str, list[Path]]:
    """Group .xlsx files by top-level category under raw/."""
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(raw_dir.rglob("*.xlsx")):
        try:
            rel = path.relative_to(raw_dir)
            category = rel.parts[0] if rel.parts else "root"
        except ValueError:
            category = "other"
        groups[category].append(path)
    return dict(groups)


def inspect_workbook(path: Path, max_preview_rows: int = 3) -> dict[str, Any]:
    """Inspect all sheets in one Excel file."""
    info: dict[str, Any] = {
        "path": str(path),
        "name": path.name,
        "sheets": {},
        "error": None,
    }
    try:
        workbook = pd.ExcelFile(path)
    except Exception as exc:  # noqa: BLE001 - discovery script should never crash
        info["error"] = str(exc)
        return info

    for sheet_name in workbook.sheet_names:
        try:
            df = pd.read_excel(workbook, sheet_name=sheet_name)
            # Drop fully empty columns often left by Excel templates
            empty_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
            preview = df.head(max_preview_rows)
            info["sheets"][sheet_name] = {
                "rows": int(len(df)),
                "columns": [str(c) for c in df.columns],
                "unnamed_columns": [str(c) for c in empty_cols],
                "dtypes": {str(c): str(t) for c, t in df.dtypes.items()},
                "null_counts": {
                    str(c): int(df[c].isna().sum()) for c in df.columns if df[c].isna().any()
                },
                "sample_rows": json.loads(
                    preview.where(preview.notna(), None).to_json(orient="records", date_format="iso")
                ),
            }
        except Exception as exc:  # noqa: BLE001
            info["sheets"][sheet_name] = {"error": str(exc)}
    return info


def choose_samples(files: list[Path], limit: int = MAX_SAMPLES_PER_FOLDER) -> list[Path]:
    """Pick a few representative files; prefer alphabetically first + last for variety."""
    if len(files) <= limit:
        return files
    chosen = [files[0], files[len(files) // 2], files[-1]]
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in chosen:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique[:limit]


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    print_section("1. RAW DATASET TREE")
    for line in list_tree(RAW_DIR, max_depth=2):
        print(line)

    print_section("2. EXCEL FILE COUNTS BY CATEGORY")
    groups = collect_excel_files(RAW_DIR)
    for category, files in sorted(groups.items()):
        print(f"  {category}: {len(files)} workbook(s)")

    print_section("3. SITE CODES (from cover filenames)")
    cover_files = groups.get("fieldform_cover", [])
    site_codes = sorted(
        {
            p.stem.split("_")[0].lower()
            for p in cover_files
            if "_" in p.stem
        }
    )
    print(f"  Found {len(site_codes)} site codes: {', '.join(site_codes)}")

    print_section("4. WORKBOOK / COLUMN INSPECTION")
    report: dict[str, Any] = {
        "raw_dir": str(RAW_DIR),
        "site_codes": site_codes,
        "file_counts": {k: len(v) for k, v in groups.items()},
        "inspections": {},
    }

    # Always fully inspect supportive / other reference tables (small + critical).
    priority_categories = ["supportive_material", "other_data"]
    for category in priority_categories:
        files = groups.get(category, [])
        print(f"\n--- {category} ({len(files)} files) ---")
        for path in files:
            print(f"\nFILE: {path.relative_to(RAW_DIR)}")
            info = inspect_workbook(path)
            report["inspections"][str(path.relative_to(RAW_DIR))] = info
            if info["error"]:
                print(f"  ERROR: {info['error']}")
                continue
            for sheet, sheet_info in info["sheets"].items():
                if "error" in sheet_info:
                    print(f"  Sheet '{sheet}': ERROR {sheet_info['error']}")
                    continue
                print(f"  Sheet '{sheet}': {sheet_info['rows']} rows, {len(sheet_info['columns'])} columns")
                print(f"    Columns: {sheet_info['columns']}")
                if sheet_info["null_counts"]:
                    print(f"    Nulls: {sheet_info['null_counts']}")
                print(f"    Sample: {sheet_info['sample_rows'][:2]}")

    # Sample field forms for schema discovery
    for category in ["fieldform_cover", "fieldform_grazing", "fieldform_quant", "fieldform_standing"]:
        files = groups.get(category, [])
        samples = choose_samples(files)
        print(f"\n--- {category} (sampling {len(samples)} of {len(files)}) ---")
        for path in samples:
            print(f"\nFILE: {path.name}")
            info = inspect_workbook(path)
            report["inspections"][str(path.relative_to(RAW_DIR))] = info
            if info["error"]:
                print(f"  ERROR: {info['error']}")
                continue
            for sheet, sheet_info in info["sheets"].items():
                if "error" in sheet_info:
                    print(f"  Sheet '{sheet}': ERROR {sheet_info['error']}")
                    continue
                print(f"  Sheet '{sheet}': {sheet_info['rows']} rows, {len(sheet_info['columns'])} columns")
                print(f"    Columns: {sheet_info['columns']}")
                if sheet_info["null_counts"]:
                    top_nulls = dict(list(sheet_info["null_counts"].items())[:8])
                    print(f"    Nulls (first 8): {top_nulls}")
                print(f"    Sample keys: {list(sheet_info['sample_rows'][0].keys()) if sheet_info['sample_rows'] else []}")

    # Schema comparison: collect unique column sets per category
    print_section("5. COLUMN SET SUMMARY (from sampled files)")
    schema_summary: dict[str, list[list[str]]] = defaultdict(list)
    for rel_path, info in report["inspections"].items():
        category = Path(rel_path).parts[0]
        for sheet, sheet_info in info.get("sheets", {}).items():
            if "columns" in sheet_info:
                cols = sheet_info["columns"]
                if cols not in schema_summary[f"{category}::{sheet}"]:
                    schema_summary[f"{category}::{sheet}"].append(cols)

    for key, variants in sorted(schema_summary.items()):
        print(f"\n{key}: {len(variants)} distinct column layout(s)")
        for i, cols in enumerate(variants, start=1):
            print(f"  layout {i} ({len(cols)} cols): {cols}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print_section("6. REPORT SAVED")
    print(f"Wrote inspection JSON to: {REPORT_PATH}")
    print("\nPhase 1 complete. Review columns above before building preprocessing (Phase 2).")


if __name__ == "__main__":
    main()
