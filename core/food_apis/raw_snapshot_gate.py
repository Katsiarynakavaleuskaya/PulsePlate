"""
Fail-closed gate: verify recorded OFF raw snapshots before heavy DB build steps.

RU: Проверка манифеста/файлов OFF до сборки БД.
EN: Manifest + on-disk verification gate before database build.
"""

from __future__ import annotations

from pathlib import Path

from core.food_sources.snapshot_manager import SnapshotIntegrityError, SnapshotManager

from .snapshot_sync import default_raw_snapshot_root


def validate_off_raw_manifest_gate(
    project_root: Path,
    enabled: bool,
    snapshot_root: Path | None = None,
) -> dict[str, object]:
    """
    When ``enabled`` is False, return a disabled marker dict.

    When enabled and ``off/manifest.json`` is missing under the snapshot root, return
    ``status=skipped``. Otherwise run :meth:`SnapshotManager.verify_recorded_snapshots`
    for source ``off`` and return ``status=verified``.
    """
    if not enabled:
        return {"enabled": False}
    root = snapshot_root if snapshot_root is not None else default_raw_snapshot_root(project_root)
    manifest_path = root / "off" / "manifest.json"
    if not manifest_path.is_file():
        return {
            "enabled": True,
            "status": "skipped",
            "reason": "missing_off_manifest",
            "root": str(root),
        }
    try:
        manager = SnapshotManager(root)
        checked = manager.verify_recorded_snapshots("off")
    except SnapshotIntegrityError as exc:
        raise SnapshotIntegrityError(f"OFF raw snapshot gate failed: {exc}") from exc
    return {
        "enabled": True,
        "status": "verified",
        "snapshots_checked": checked,
        "root": str(root),
    }
