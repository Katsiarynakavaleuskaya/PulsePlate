"""
Sync Open Food Facts raw snapshots into the local raw snapshot tree.

RU: Синхронизация сырых снапшотов OFF в ``data/raw/snapshots`` (или корень из env).
EN: Sync OFF raw snapshots under ``data/raw/snapshots`` (or env-configured root).
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Callable

from core.food_sources.off_delta import OFFTransport, OpenFoodFactsDeltaSource
from core.food_sources.snapshot_manager import SnapshotManager, SnapshotMeta


def default_raw_snapshot_root(project_root: Path | None = None) -> Path:
    """Return canonical raw snapshot root (env override or ``<project>/data/raw/snapshots``)."""
    env = os.environ.get("PULSEPLATE_FOOD_RAW_SNAPSHOT_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    root = project_root if project_root is not None else Path(__file__).resolve().parents[2]
    return (root / "data" / "raw" / "snapshots").resolve()


def sync_openfoodfacts_snapshot(
    raw_root: Path | None = None,
    *,
    project_root: Path | None = None,
    force: bool = False,
    transport: OFFTransport | None = None,
    today_provider: Callable[[], date] | None = None,
) -> SnapshotMeta | None:
    """
    Pull OFF snapshot via :class:`OpenFoodFactsDeltaSource` into the raw tree.

    When ``raw_root`` is omitted, uses :func:`default_raw_snapshot_root`.
    """
    resolved = (
        raw_root.expanduser().resolve()
        if raw_root is not None
        else default_raw_snapshot_root(project_root)
    )
    manager = SnapshotManager(resolved)
    source = OpenFoodFactsDeltaSource(transport=transport, today_provider=today_provider)
    return manager.sync_if_needed(source, force=force)
