"""Tests for snapshot manager contracts."""

from __future__ import annotations

import json
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


@dataclass
class _AdvancingToday:
    first: date
    second: date
    calls: int = 0

    def __call__(self) -> date:
        self.calls += 1
        if self.calls == 1:
            return self.first
        return self.second


@dataclass
class _EmptyDeltaSource:
    name: str
    updates_available: bool = True

    def has_updates_since(self, last_snapshot: date) -> bool:
        _ = last_snapshot
        return self.updates_available

    def download_full(self, dest: Path) -> SnapshotMeta:
        output_path = dest / "full.bin"
        output_path.write_bytes(b"full")
        return SnapshotMeta(
            source=self.name,
            snapshot_date=date(2026, 2, 23),
            file_path=output_path,
            checksum_sha256=sha256_file(output_path),
            record_count=1,
            size_bytes=output_path.stat().st_size,
            mode="full",
        )

    def download_delta(self, since: date, dest: Path) -> SnapshotMeta:
        _ = since
        output_path = dest / "delta.bin"
        output_path.write_bytes(b"")
        return SnapshotMeta(
            source=self.name,
            snapshot_date=date(2026, 2, 24),
            file_path=output_path,
            checksum_sha256=sha256_file(output_path),
            record_count=0,
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


def test_snapshot_manager_noop_sync_does_not_create_empty_date_dir(tmp_path: Path) -> None:
    today_provider = _AdvancingToday(first=date(2026, 2, 23), second=date(2026, 2, 24))
    manager = SnapshotManager(tmp_path, today_provider=today_provider)
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None

    source.updates_available = False
    assert manager.sync_if_needed(source) is None
    assert not (tmp_path / "dummy" / "2026-02-24").exists()


def test_snapshot_manager_syncs_delta_after_initial_snapshot(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None

    source.updates_available = True
    meta = manager.sync_if_needed(source)
    assert meta is not None
    assert meta.mode == "delta"


def test_snapshot_manager_skips_empty_delta_without_advancing_manifest(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _EmptyDeltaSource(name="dummy")

    first_meta = manager.sync_if_needed(source)
    assert first_meta is not None
    assert manager.get_last_snapshot_date("dummy") == date(2026, 2, 23)

    second_meta = manager.sync_if_needed(source)
    assert second_meta is None
    assert manager.get_last_snapshot_date("dummy") == date(2026, 2, 23)
    assert not (tmp_path / "dummy" / "2026-02-24" / "delta.bin").exists()


def test_snapshot_manager_force_sync_uses_delta_even_without_updates(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None

    source.updates_available = False
    meta = manager.sync_if_needed(source, force=True)
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

    manifest_path.write_text('{"snapshots":[]}', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text('{"source":"other-source","snapshots":[]}', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text('{"source":"broken-source","snapshots":"bad"}', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text('{"source":"broken-source","snapshots":[1]}', encoding="utf-8")
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"2026-02-24","file":"f"}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"2026-02-24","file":"f","mode":1}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"2026-02-24","file":"f","mode":"delta","checksum":1,"records":1,"bytes":1}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"2026-02-24","file":"f","mode":"delta","checksum":"x","records":"1","bytes":1}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"2026-02-24","file":"f","mode":"delta","checksum":"x","records":1,"bytes":"1"}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")

    manifest_path.write_text(
        '{"source":"broken-source","snapshots":[{"date":"not-a-date","file":"f","mode":"delta","checksum":"x","records":1,"bytes":1}]}',
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError):
        manager.get_last_snapshot_date("broken-source")


def test_snapshot_manager_record_snapshot_dedup_and_ordering(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source_dir = tmp_path / "dummy" / "2026-02-24"
    source_dir.mkdir(parents=True, exist_ok=True)

    file_a = source_dir / "a.bin"
    file_b = source_dir / "b.bin"
    file_c = source_dir / "c.bin"
    for file_path in (file_a, file_b, file_c):
        file_path.write_bytes(file_path.name.encode("utf-8"))

    meta_a = SnapshotMeta(
        source="dummy",
        snapshot_date=date(2026, 2, 24),
        file_path=file_a,
        checksum_sha256=sha256_file(file_a),
        record_count=1,
        size_bytes=file_a.stat().st_size,
        mode="full",
    )
    meta_a_dup = SnapshotMeta(
        source="dummy",
        snapshot_date=date(2026, 2, 24),
        file_path=file_a,
        checksum_sha256=sha256_file(file_a),
        record_count=1,
        size_bytes=file_a.stat().st_size,
        mode="full",
    )
    meta_b = SnapshotMeta(
        source="dummy",
        snapshot_date=date(2026, 2, 25),
        file_path=file_b,
        checksum_sha256=sha256_file(file_b),
        record_count=1,
        size_bytes=file_b.stat().st_size,
        mode="delta",
    )
    meta_c = SnapshotMeta(
        source="dummy",
        snapshot_date=date(2026, 2, 24),
        file_path=file_c,
        checksum_sha256=sha256_file(file_c),
        record_count=1,
        size_bytes=file_c.stat().st_size,
        mode="delta",
    )

    manager.record_snapshot(meta_a)
    manager.record_snapshot(meta_a_dup)
    manager.record_snapshot(meta_b)
    manager.record_snapshot(meta_c)

    manifest_path = tmp_path / "dummy" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshots = manifest["snapshots"]

    assert len(snapshots) == 3
    keys = [(row["date"], row["file"], row["mode"]) for row in snapshots]
    assert keys == sorted(keys)


def test_snapshot_manager_size_mismatch_fails_closed(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    snapshot_file = tmp_path / "sz" / "2026-02-24" / "f.bin"
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_bytes(b"abc")
    bad_meta = SnapshotMeta(
        source="sz",
        snapshot_date=date(2026, 2, 24),
        file_path=snapshot_file,
        checksum_sha256=sha256_file(snapshot_file),
        record_count=1,
        size_bytes=999,
        mode="full",
    )
    with pytest.raises(SnapshotIntegrityError, match="Size mismatch"):
        manager.validate_snapshot(bad_meta)


def test_verify_recorded_snapshots_revalidates_manifest(tmp_path: Path) -> None:
    """``verify_recorded_snapshots`` should load manifest and validate each entry."""
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None
    assert manager.verify_recorded_snapshots("dummy") == 1


def test_verify_recorded_snapshots_detects_tampering(tmp_path: Path) -> None:
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source = _DummySource(name="dummy", full_payload=b"full", delta_payload=b"delta")
    assert manager.sync_if_needed(source) is not None
    manifest = json.loads((tmp_path / "dummy" / "manifest.json").read_text(encoding="utf-8"))
    fpath = Path(manifest["snapshots"][0]["file"])
    fpath.write_bytes(b"tampered")
    with pytest.raises(SnapshotIntegrityError):
        manager.verify_recorded_snapshots("dummy")


def test_verify_recorded_snapshots_invalid_date_fails_closed(tmp_path: Path) -> None:
    """Bad ISO date strings in manifest entries must raise ``SnapshotIntegrityError``."""
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source_dir = tmp_path / "bad-dates"
    source_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = source_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "bad-dates",
                "snapshots": [
                    {
                        "date": "not-a-valid-iso-date",
                        "file": str(source_dir / "x.bin"),
                        "checksum": "0" * 64,
                        "records": 1,
                        "bytes": 0,
                        "mode": "full",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError, match="Invalid snapshot date"):
        manager.verify_recorded_snapshots("bad-dates")


def test_verify_recorded_snapshots_size_mismatch_fails_closed(tmp_path: Path) -> None:
    """Manifest ``bytes`` must match on-disk file size during re-validation."""
    manager = SnapshotManager(tmp_path, today_provider=lambda: date(2026, 2, 24))
    source_dir = tmp_path / "size-mismatch"
    snap_dir = source_dir / "2026-02-24"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snap_file = snap_dir / "full.bin"
    snap_file.write_bytes(b"abc")

    manifest_path = source_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "source": "size-mismatch",
                "snapshots": [
                    {
                        "date": "2026-02-24",
                        "file": str(snap_file),
                        "checksum": sha256_file(snap_file),
                        "records": 1,
                        "bytes": 999,
                        "mode": "full",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SnapshotIntegrityError, match="Size mismatch"):
        manager.verify_recorded_snapshots("size-mismatch")
