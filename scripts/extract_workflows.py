#!/usr/bin/env python3
"""
Extract per-language GHA workflow YAML archives into data/workflows/.

Run this script once before the analysis pipeline (RQ1-RQ3).

Usage (from repository root):
    python scripts/extract_workflows.py
    python scripts/extract_workflows.py --force
"""

from __future__ import annotations

import argparse
import shutil
import zipfile

from repo_paths import ARCHIVE_FILES, ARCHIVE_INNER_FOLDERS, ARCHIVES_DIR, WORKFLOWS_DIR


def flatten_language_folder(target_dir, inner_name: str) -> bool:
    """Move contents of <target>/<inner_name>/ up one level and remove inner_name/."""
    inner = target_dir / inner_name
    if not inner.is_dir():
        return False

    for item in list(inner.iterdir()):
        destination = target_dir / item.name
        if destination.exists():
            if destination.is_dir() and item.is_dir():
                for sub_item in list(item.iterdir()):
                    sub_dest = destination / sub_item.name
                    if not sub_dest.exists():
                        shutil.move(str(sub_item), str(sub_dest))
                shutil.rmtree(item, ignore_errors=True)
        else:
            shutil.move(str(item), str(destination))

    if inner.is_dir():
        shutil.rmtree(inner, ignore_errors=True)

    print(f"  Flattened {inner_name}/ into {target_dir.name}/")
    return True


def is_flat_extraction(target_dir, inner_name: str) -> bool:
    nested = target_dir / inner_name
    if not target_dir.exists():
        return False
    has_yaml = any(target_dir.rglob("*.yml")) or any(target_dir.rglob("*.yaml"))
    return has_yaml and not nested.is_dir()


def extract_archive(zip_path, target_dir, inner_name: str, force: bool = False) -> bool:
    """Extract one archive and flatten its inner language folder. Returns True if extraction ran."""
    if not zip_path.exists():
        return False

    nested = target_dir / inner_name

    if target_dir.exists() and nested.is_dir() and not force:
        flatten_language_folder(target_dir, inner_name)
        print(f"Flattened existing extraction at {target_dir}")
        return False

    if is_flat_extraction(target_dir, inner_name) and not force:
        print(f"Skipping {zip_path.name} - already extracted at {target_dir}")
        return False

    if target_dir.exists() and force:
        shutil.rmtree(target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {zip_path.name} -> {target_dir}")
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(target_dir)

    flatten_language_folder(target_dir, inner_name)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract GHA workflow YAML archives into data/workflows/"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract archives even when workflow folders already exist",
    )
    args = parser.parse_args()

    WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVES_DIR.mkdir(parents=True, exist_ok=True)

    missing = []
    extracted = 0
    for archive_name, target_dir in ARCHIVE_FILES.items():
        zip_path = ARCHIVES_DIR / archive_name
        inner_name = ARCHIVE_INNER_FOLDERS[archive_name]
        if not zip_path.exists():
            missing.append(archive_name)
            continue
        if extract_archive(zip_path, target_dir, inner_name, force=args.force):
            extracted += 1

    if missing:
        print("\nMissing archives - place these files in data/archives/:")
        for name in missing:
            print(f"  - {name}")
        return 1

    print(f"\nDone. Workflow YAMLs are available under {WORKFLOWS_DIR}")
    if extracted == 0 and not args.force:
        print("All archives were already extracted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
