"""
Snapshot manager contracts for snapshot-first food source ingestion.

RU: Контракты и менеджер снапшотов для snapshot-first пайплайна.
EN: Snapshot contracts and manager for snapshot-first ingestion.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Protocol, cast


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return SHA-256 checksum for a file."""
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        while True:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SnapshotMeta:
    """Metadata about a synchronized snapshot."""

    source: str
    snapshot_date: date
    file_path: Path
    checksum_sha256: str
    record_count: int
    size_bytes: int
    mode: str = "full"

    def to_manifest_entry(self) -> dict[str, Any]:
        """Convert to a serializable manifest entry."""
        return {
            "date": self.snapshot_date.isoformat(),
            "file": str(self.file_path),
            "checksum": self.checksum_sha256,
            "records": self.record_count,
            "bytes": self.size_bytes,
            "mode": self.mode,
        }


class SnapshotSource(Protocol):
    """Protocol for snapshot-capable food data sources."""

    name: str

    def has_updates_since(self, last_snapshot: date) -> bool:
        """Return True when source has updates since last snapshot."""

    def download_delta(self, since: date, dest: Path) -> SnapshotMeta:
        """Download a delta snapshot into destination path."""

    def download_full(self, dest: Path) -> SnapshotMeta:
        """Download a full snapshot into destination path."""


class SnapshotIntegrityError(RuntimeError):
    """Raised when snapshot integrity checks fail."""


class SnapshotManager:
    """
    Local snapshot manager with immutable storage and manifest tracking.

    RU: Локальный менеджер снапшотов с манифестом и fail-closed валидацией.
    EN: Local snapshot manager with manifest tracking and fail-closed validation.
    """

    MANIFEST_FILE = "manifest.json"

    def __init__(self, base_path: Path | str, *, today_provider: Any | None = None) -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._today_provider = today_provider or date.today

    def _today(self) -> date:
        return self._today_provider()

    def _manifest_path(self, source: str) -> Path:
        return self.base_path / source / self.MANIFEST_FILE

    def _load_manifest(self, source: str) -> dict[str, Any]:
        manifest_path = self._manifest_path(source)
        if not manifest_path.exists():
            return {"source": source, "snapshots": []}
        with open(manifest_path, "r", encoding="utf-8") as manifest_file:
            loaded = json.load(manifest_file)
        if not isinstance(loaded, dict):
            raise SnapshotIntegrityError(
                f"Invalid manifest schema for source={source}: root object must be a dict"
            )
        data = cast(dict[str, Any], loaded)
        snapshots = data.get("snapshots")
        if not isinstance(snapshots, list):
            raise SnapshotIntegrityError(
                f"Invalid manifest schema for source={source}: snapshots must be a list"
            )
        return data

    def get_last_snapshot_date(self, source: str) -> date | None:
        """Return date of latest recorded snapshot for a source."""
        data = self._load_manifest(source)
        snapshots = data.get("snapshots", [])
        if not snapshots:
            return None
        try:
            return date.fromisoformat(snapshots[-1]["date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SnapshotIntegrityError(
                f"Invalid latest snapshot date for source={source}"
            ) from exc

    def validate_snapshot(self, meta: SnapshotMeta) -> None:
        """Fail-closed integrity validation before manifest update."""
        if not meta.file_path.exists():
            raise SnapshotIntegrityError(f"Snapshot file does not exist: {meta.file_path}")
        actual_checksum = sha256_file(meta.file_path)
        if actual_checksum != meta.checksum_sha256:
            raise SnapshotIntegrityError(
                "Checksum mismatch for snapshot "
                f"{meta.file_path}: expected={meta.checksum_sha256} actual={actual_checksum}"
            )

    def record_snapshot(self, meta: SnapshotMeta) -> None:
        """Persist snapshot metadata entry into source manifest."""
        self.validate_snapshot(meta)

        manifest_path = self._manifest_path(meta.source)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_manifest(meta.source)

        snapshots = data.setdefault("snapshots", [])
        entry = meta.to_manifest_entry()

        filtered = [
            snapshot
            for snapshot in snapshots
            if not (
                snapshot.get("date") == entry["date"]
                and snapshot.get("file") == entry["file"]
                and snapshot.get("mode") == entry["mode"]
            )
        ]
        filtered.append(entry)
        filtered.sort(key=lambda snapshot: (snapshot["date"], snapshot["file"], snapshot["mode"]))
        data["snapshots"] = filtered

        with open(manifest_path, "w", encoding="utf-8") as manifest_file:
            json.dump(data, manifest_file, indent=2)

    def sync_if_needed(self, source: SnapshotSource, force: bool = False) -> SnapshotMeta | None:
        """
        Sync a source snapshot if required.

        First run pulls full snapshot.
        Subsequent runs pull delta only when updates are available or force=True.
        """
        last_snapshot = self.get_last_snapshot_date(source.name)
        destination = self.base_path / source.name / self._today().isoformat()
        destination.mkdir(parents=True, exist_ok=True)

        if last_snapshot is None:
            meta = source.download_full(destination)
        elif force or source.has_updates_since(last_snapshot):
            meta = source.download_delta(last_snapshot, destination)
        else:
            return None

        self.record_snapshot(meta)
        return meta
