"""W1 integration tests: raw snapshot sync, gate, and update_manager delegate."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import pytest

from core.food_apis.raw_snapshot_gate import validate_off_raw_manifest_gate
from core.food_apis.snapshot_sync import default_raw_snapshot_root, sync_openfoodfacts_snapshot
from core.food_apis.update_manager import DatabaseUpdateManager
from core.food_sources.snapshot_manager import SnapshotIntegrityError, SnapshotManager, SnapshotMeta
from core.food_sources.snapshot_manager import sha256_file


def test_default_raw_snapshot_root_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PULSEPLATE_FOOD_RAW_SNAPSHOT_ROOT", str(tmp_path / "custom"))
    assert default_raw_snapshot_root(tmp_path) == (tmp_path / "custom").resolve()


def test_default_raw_snapshot_root_project_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PULSEPLATE_FOOD_RAW_SNAPSHOT_ROOT", raising=False)
    root = default_raw_snapshot_root(tmp_path)
    assert root == (tmp_path / "data" / "raw" / "snapshots").resolve()


def test_validate_off_raw_manifest_gate_disabled() -> None:
    assert validate_off_raw_manifest_gate(Path("/tmp"), enabled=False) == {"enabled": False}


def test_validate_off_raw_manifest_gate_skips_without_manifest(tmp_path: Path) -> None:
    snap_root = tmp_path / "snapshots"
    snap_root.mkdir(parents=True)
    result = validate_off_raw_manifest_gate(tmp_path, enabled=True, snapshot_root=snap_root)
    assert result["enabled"] is True
    assert result["status"] == "skipped"
    assert result["reason"] == "missing_off_manifest"


def test_validate_off_raw_manifest_gate_verifies_recorded(tmp_path: Path) -> None:
    base = tmp_path / "snapshots"
    manager = SnapshotManager(base)
    off_dir = base / "off" / "2026-04-06"
    off_dir.mkdir(parents=True)
    blob = off_dir / "sample.gz"
    blob.write_bytes(b"gz-bytes")
    meta = SnapshotMeta(
        source="off",
        snapshot_date=date(2026, 4, 6),
        file_path=blob,
        checksum_sha256=sha256_file(blob),
        record_count=1,
        size_bytes=blob.stat().st_size,
        mode="full",
    )
    manager.record_snapshot(meta)

    result = validate_off_raw_manifest_gate(tmp_path, enabled=True, snapshot_root=base)
    assert result["status"] == "verified"
    assert result["snapshots_checked"] == 1


def test_validate_off_raw_manifest_gate_tamper_raises(tmp_path: Path) -> None:
    base = tmp_path / "snapshots"
    manager = SnapshotManager(base)
    off_dir = base / "off" / "2026-04-06"
    off_dir.mkdir(parents=True)
    blob = off_dir / "sample.gz"
    blob.write_bytes(b"gz-bytes")
    meta = SnapshotMeta(
        source="off",
        snapshot_date=date(2026, 4, 6),
        file_path=blob,
        checksum_sha256=sha256_file(blob),
        record_count=1,
        size_bytes=blob.stat().st_size,
        mode="full",
    )
    manager.record_snapshot(meta)
    blob.write_bytes(b"tampered")

    with pytest.raises(SnapshotIntegrityError, match="OFF raw snapshot gate failed"):
        validate_off_raw_manifest_gate(tmp_path, enabled=True, snapshot_root=base)


def test_sync_openfoodfacts_snapshot_uses_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    def fake_sync(self: SnapshotManager, source: object, force: bool = False) -> None:
        calls.append(force)
        return None

    monkeypatch.setattr(SnapshotManager, "sync_if_needed", fake_sync)
    sync_openfoodfacts_snapshot(tmp_path, project_root=tmp_path, force=True)
    assert calls == [True]


def test_sync_openfoodfacts_raw_root_expanduser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User-supplied ``raw_root`` must expand ``~`` like env-based default root."""
    home = tmp_path / "homedir"
    target = home / "snapshots"
    target.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    captured: list[Path] = []

    def fake_sync(self: SnapshotManager, source: object, force: bool = False) -> None:
        captured.append(self.base_path)
        return None

    monkeypatch.setattr(SnapshotManager, "sync_if_needed", fake_sync)
    sync_openfoodfacts_snapshot(Path("~/snapshots"), project_root=tmp_path, force=False)
    assert captured == [target.resolve()]


def test_database_update_manager_sync_openfoodfacts_raw_snapshot_delegates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    def fake_sync(
        raw_root: Path | None,
        *,
        project_root: Path | None = None,
        force: bool = False,
        transport: object | None = None,
        today_provider: object | None = None,
    ) -> None:
        captured["raw_root"] = raw_root
        captured["force"] = force
        _ = (project_root, transport, today_provider)
        return None

    import core.food_apis.snapshot_sync as snapshot_sync_mod

    monkeypatch.setattr(snapshot_sync_mod, "sync_openfoodfacts_snapshot", fake_sync)
    mgr = DatabaseUpdateManager(cache_dir=tmp_path / "cache")
    mgr.sync_openfoodfacts_raw_snapshot(tmp_path / "raw", force=True)
    assert captured["raw_root"] == tmp_path / "raw"
    assert captured["force"] is True


def test_manifest_file_relative_path_verify(tmp_path: Path) -> None:
    """Manifest entries may use paths relative to the manifest directory."""
    base = tmp_path / "snapshots"
    off_root = base / "off"
    day_dir = off_root / "2026-04-07"
    day_dir.mkdir(parents=True)
    blob = day_dir / "delta.gz"
    blob.write_bytes(b"x")
    manifest_path = off_root / "manifest.json"
    entry = {
        "date": "2026-04-07",
        "file": "2026-04-07/delta.gz",
        "checksum": sha256_file(blob),
        "records": 1,
        "bytes": blob.stat().st_size,
        "mode": "delta",
    }
    manifest_path.write_text(
        json.dumps({"source": "off", "snapshots": [entry]}, indent=2),
        encoding="utf-8",
    )
    manager = SnapshotManager(base)
    assert manager.verify_recorded_snapshots("off") == 1
