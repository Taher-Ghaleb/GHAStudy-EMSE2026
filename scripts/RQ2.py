#!/usr/bin/env python3
"""
RQ2 — Structure and usage patterns (full pipeline).

Runs stratified sampling, semantic step labeling, pattern grouping,
and cross-language statistical tests on the N=382 workflow sample.

Usage (from repository root):
    python scripts/RQ2.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
RQ2_DIR = SCRIPTS_DIR / "rq2"

PIPELINE = (
    ("Stratified sampling", RQ2_DIR / "sample.py"),
    ("Semantic labeling", RQ2_DIR / "semantic.py"),
    ("Pattern analysis + statistics", RQ2_DIR / "patterns.py"),
)


def main() -> int:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SCRIPTS_DIR)

    for label, script in PIPELINE:
        if not script.exists():
            print(f"[ERROR] Missing script: {script}")
            return 1
        print(f"\n{'=' * 60}\nRQ2 — {label}\n{'=' * 60}")
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=PROJECT_ROOT,
            env=env,
            check=False,
        )
        if result.returncode != 0:
            print(f"[ERROR] Step failed: {label}")
            return result.returncode

    print("\nRQ2 pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
