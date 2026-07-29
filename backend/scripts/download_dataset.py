"""
Download (or locate) the Lacuna Namibia rangeland dataset.

Preferred path for this project: place the unzipped Kaggle dataset under
backend/data/raw/ so inspection and preprocessing can run offline.

Optional: set LACUNA_DATASET_PATH to point at an existing download folder.
Optional: run with --kaggle to fetch via kagglehub when credentials are configured.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"


def copy_into_raw(source: Path, destination: Path = RAW_DIR) -> Path:
    """Copy dataset files into backend/data/raw if they are not already there."""
    destination.mkdir(parents=True, exist_ok=True)

    if source.resolve() == destination.resolve():
        print(f"Dataset already at: {destination}")
        return destination

    for item in source.iterdir():
        target = destination / item.name
        if target.exists():
            print(f"Skipping existing: {target.name}")
            continue
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
        print(f"Copied: {item.name}")

    return destination


def download_with_kagglehub(destination: Path = RAW_DIR) -> Path:
    """Download farm4tradesrl/lacuna via kagglehub and copy into data/raw."""
    import kagglehub

    path = Path(kagglehub.dataset_download("farm4tradesrl/lacuna"))
    print(f"kagglehub downloaded to: {path}")
    return copy_into_raw(path, destination)


def summarize_raw(raw_dir: Path = RAW_DIR) -> None:
    """Print a short summary of what is present under data/raw."""
    if not raw_dir.exists():
        print(f"Raw directory missing: {raw_dir}")
        return

    entries = sorted(raw_dir.iterdir(), key=lambda p: p.name.lower())
    if not entries:
        print(f"Raw directory is empty: {raw_dir}")
        return

    print(f"Raw dataset root: {raw_dir}")
    for entry in entries:
        kind = "dir" if entry.is_dir() else "file"
        print(f"  [{kind}] {entry.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Locate or download Lacuna dataset.")
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="Download via kagglehub (requires Kaggle credentials).",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Existing unzipped dataset folder to copy into data/raw.",
    )
    args = parser.parse_args()

    if args.kaggle:
        download_with_kagglehub()
    elif args.source:
        copy_into_raw(args.source)
    else:
        print("No download requested. Using local data/raw if present.")
        print("Pass --kaggle to download, or --source <path> to copy an unzipped folder.")

    summarize_raw()


if __name__ == "__main__":
    main()
