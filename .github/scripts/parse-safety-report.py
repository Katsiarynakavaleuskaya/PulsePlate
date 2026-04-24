#!/usr/bin/env python3
"""Compatibility wrapper for the canonical Safety audit parser."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.ci.run_safety_audit import parse_legacy_report

if __name__ == "__main__":
    raise SystemExit(
        parse_legacy_report(
            report_path=Path("safety-report.json"),
            summary_path=Path("safety-report.txt"),
        )
    )
