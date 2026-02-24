"""
Open Food Facts snapshot source with deterministic weekly delta ingestion.

RU: Источник OFF со snapshot-first контрактом и детерминированным delta-слиянием.
EN: OFF source implementing snapshot-first and deterministic delta merge.
"""

from __future__ import annotations

import gzip
import io
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Protocol

import httpx

from .snapshot_manager import SnapshotIntegrityError, SnapshotMeta, sha256_file

OFF_DELTA_URL = "https://static.openfoodfacts.org/data/delta/{year}-{month:02d}-{day:02d}.jsonl.gz"
OFF_FULL_URL = "https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz"


class OFFTransport(Protocol):
    """Transport abstraction to keep ingestion testable and deterministic."""

    def fetch(self, url: str, timeout_seconds: int) -> bytes | None:
        """Return raw payload bytes for URL, or None for non-existing resources."""

    def iter_bytes(self, url: str, timeout_seconds: int, chunk_size: int) -> Iterable[bytes]:
        """Stream payload bytes for URL."""


class HttpxOFFTransport:
    """Default transport using httpx."""

    def fetch(self, url: str, timeout_seconds: int) -> bytes | None:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        if response.status_code == 200:
            return response.content
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return None

    def iter_bytes(self, url: str, timeout_seconds: int, chunk_size: int) -> Iterable[bytes]:
        with httpx.stream("GET", url, timeout=timeout_seconds, follow_redirects=True) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                yield chunk


class OpenFoodFactsDeltaSource:
    """OFF source implementation for SnapshotManager protocol."""

    name = "off"

    @staticmethod
    def _utc_today() -> date:
        """Return UTC calendar date to avoid local-time drift."""
        return datetime.now(timezone.utc).date()

    def __init__(
        self,
        *,
        transport: OFFTransport | None = None,
        today_provider: Callable[[], date] | None = None,
        full_url: str = OFF_FULL_URL,
        delta_url_template: str = OFF_DELTA_URL,
    ) -> None:
        self.transport = transport or HttpxOFFTransport()
        self._today_provider = today_provider or self._utc_today
        self.full_url = full_url
        self.delta_url_template = delta_url_template

    def _today(self) -> date:
        return self._today_provider()

    def has_updates_since(self, last_snapshot: date) -> bool:
        """OFF policy: sync delta weekly or later."""
        return (self._today() - last_snapshot).days >= 7

    def _iter_delta_days(self, since: date) -> Iterable[date]:
        current = since + timedelta(days=1)
        end_date = self._today()
        while current <= end_date:
            yield current
            current = current + timedelta(days=1)

    def _decode_delta_payload(self, payload: bytes, source_url: str) -> bytes:
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as gzip_file:
                return gzip_file.read()
        except (OSError, EOFError, zlib.error) as exc:
            raise SnapshotIntegrityError(f"Malformed OFF delta payload: {source_url}") from exc

    def download_delta(self, since: date, dest: Path) -> SnapshotMeta:
        """Download and merge daily OFF delta payloads into one deterministic gzip snapshot."""
        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / "openfoodfacts-delta.jsonl.gz"

        record_count = 0
        with open(output_path, "wb") as output_file:
            # mtime=0 keeps gzip output deterministic across runs for identical input.
            with gzip.GzipFile(fileobj=output_file, mode="wb", mtime=0) as gzip_out:
                for day in self._iter_delta_days(since):
                    url = self.delta_url_template.format(
                        year=day.year,
                        month=day.month,
                        day=day.day,
                    )
                    payload = self.transport.fetch(url=url, timeout_seconds=120)
                    if payload is None:
                        continue
                    decoded = self._decode_delta_payload(payload=payload, source_url=url)
                    if decoded and not decoded.endswith(b"\n"):
                        decoded += b"\n"
                    record_count += decoded.count(b"\n")
                    gzip_out.write(decoded)

        checksum = sha256_file(output_path)
        return SnapshotMeta(
            source=self.name,
            snapshot_date=self._today(),
            file_path=output_path,
            checksum_sha256=checksum,
            record_count=record_count,
            size_bytes=output_path.stat().st_size,
            mode="delta",
        )

    def download_full(self, dest: Path) -> SnapshotMeta:
        """Download full OFF dump snapshot."""
        dest.mkdir(parents=True, exist_ok=True)
        output_path = dest / "openfoodfacts-products.jsonl.gz"

        with open(output_path, "wb") as output_file:
            for chunk in self.transport.iter_bytes(
                url=self.full_url, timeout_seconds=3600, chunk_size=1024 * 1024
            ):
                output_file.write(chunk)

        try:
            with gzip.open(output_path, "rb") as gzip_file:
                record_count = sum(1 for _ in gzip_file)
        except (OSError, EOFError, zlib.error) as exc:
            raise SnapshotIntegrityError(f"Malformed OFF full snapshot: {output_path}") from exc

        checksum = sha256_file(output_path)
        return SnapshotMeta(
            source=self.name,
            snapshot_date=self._today(),
            file_path=output_path,
            checksum_sha256=checksum,
            record_count=record_count,
            size_bytes=output_path.stat().st_size,
            mode="full",
        )
