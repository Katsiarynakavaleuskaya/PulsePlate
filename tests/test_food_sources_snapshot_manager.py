"""Tests for snapshot manager contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from core.food_sources.snapshot_manager import (
    SnapshotIntegrityError,
    SnapshotManager,
    SnapshotMeta,
    sha256_file,
)


@dataclass
class _DummySource:
    name: str
    full_payload: bytes
    delta_payload: bytes
    updates_available: bool = True

    def has_updates_since(self, last_snapshot: date) -> bool:
        _ = last_snapshot
        return self.updates_available

    def download_full(self, dest: Path) -> SnapshotMeta:
        output_path = dest / "full.bin"
        output_path.write_bytes(self.full_payload)
        return SnapshotMeta(
            source=self.name,
            snapshot_date=date(2026, 2, 24),
            file_path=output_path,
            checksum_sha256=sha256_file(output_path),
            record_count=1,
            size_bytes=output_path.stat().st_size,
            mode="full",
        )

    def download_delta(self, since: date, dest: Path) -> SnapshotMeta:
        _ = since
        output_path = dest / "delta.bin"
        output_path.write_bytes(self.delta_payload)
        return SnapshotMeta(
            source=self.name,
            snapshot_date=date(2026, 2, 24),
            file_path=output_path,
            checksum_sha256=sha256_file(output_path),
            record_count=1,
            size_bytes=output_path.stat().st_size,
            mode="delta",
        )


def test_snapshot_manager_first_sync_and_manifest_integrity(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")

    meta = manager.sync_if_needed(source)
    assert meta is not None
    assert meta.mode == "full"

    manifest_path = tmp_path / "dummy" / "manifest.json"
    assert manifest_path.exists()

    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert '"source": "dummy"' in manifest_text
    assert '"mode": "full"' in manifest_text
    assert manager.get_last_snapshot_date("dummy") == date(2026, 2, 24)


def test_snapshot_manager_skips_when_no_updates(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None

    source.updates_available = False
    assert manager.sync_if_needed(source) is None


def test_snapshot_manager_syncs_delta_after_initial_snapshot(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None

    source.updates_available = True
    meta = manager.sync_if_needed(source)
    assert meta is not None
    assert meta.mode == "delta"


def test_snapshot_manager_checksum_mismatch_fails_closed(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    snapshot_file = tmp_path / "bad-source" / "2026-02-24" / "bad.bin"
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_bytes(b"payload")

    bad_meta = SnapshotMeta(
        source="bad-source",
        snapshot_date=date(2026, 2, 24),
        file_path=snapshot_file,
        checksum_sha256="0" * 64,
        record_count=1,
        size_bytes=snapshot_file.stat().st_size,
        mode="full",
    )

    with pytest.raises(SnapshotIntegrityError):
        manager.record_snapshot(bad_meta)

    assert not (tmp_path / "bad-source" / "manifest.json").exists()


def test_snapshot_manager_missing_snapshot_file_fails_closed(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    missing_meta = SnapshotMeta(
        source="missing-source",
        snapshot_date=date(2026, 2, 24),
        file_path=tmp_path / "missing-source" / "2026-02-24" / "missing.bin",
        checksum_sha256="0" * 64,
        record_count=0,
        size_bytes=0,
        mode="full",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.validate_snapshot(missing_meta)


def test_snapshot_manager_manifest_schema_errors(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source_dir = tmp_path / "broken-source"
    source_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = source_dir / "manifest.json"

    manifest_path.write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text('{"source":"broken-source","snapshots":"bad"}', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"not-a-date"}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")
