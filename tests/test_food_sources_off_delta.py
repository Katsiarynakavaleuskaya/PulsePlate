"""Tests for OFF snapshot delta source contracts."""

from __future__ import annotations

import gzip
import io
from datetime import date
from pathlib import Path
from types import TracebackType

import pytest

from core.food_sources.off_delta import HttpxOFFTransport, OpenFoodFactsDeltaSource
from core.food_sources.snapshot_manager import SnapshotIntegrityError


def _gzip_payload(text: str) -> bytes:
    raw_buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=raw_buffer, mode="wb", mtime=0) as gzip_file:
        gzip_file.write(text.encode("utf-8"))
    return raw_buffer.getvalue()


class _StubTransport:
    def __init__(
        self,
        *,
        payload_map: dict[str, bytes] | None = None,
        full_chunks: list[bytes] | None = None,
    ) -> None:
        self.payload_map = payload_map or {}
        self.full_chunks = full_chunks or []

    def fetch(self, url: str, timeout_seconds: int) -> bytes | None:
        _ = timeout_seconds
        return self.payload_map.get(url)

    def iter_bytes(self, url: str, timeout_seconds: int, chunk_size: int) -> list[bytes]:
        _ = (url, timeout_seconds, chunk_size)
        return self.full_chunks


class _FakeResponse:
    def __init__(self, status_code: int, content: bytes = b"") -> None:
        self.status_code = status_code
        self.content = content
        self._raise_called = False

    def raise_for_status(self) -> None:
        self._raise_called = True
        raise RuntimeError("boom")


class _FakeStreamResponse:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def __enter__(self) -> "_FakeStreamResponse":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        _ = (exc_type, exc, tb)
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_bytes(self, chunk_size: int) -> list[bytes]:
        _ = chunk_size
        return self._chunks


def test_off_delta_is_deterministic_and_counts_records(tmp_path: Path) -> None:
    day_21 = "https://static.openfoodfacts.org/data/delta/2026-02-21.jsonl.gz"
    day_22 = "https://static.openfoodfacts.org/data/delta/2026-02-22.jsonl.gz"
    transport = _StubTransport(
        payload_map={
            day_21: _gzip_payload('{"code":"1"}\n{"code":"2"}\n'),
            day_22: _gzip_payload('{"code":"3"}'),
        }
    )

    source = OpenFoodFactsDeltaSource(
        transport=transport,
        today_provider=lambda: date(2026, 2, 22),
    )

    meta_1 = source.download_delta(since=date(2026, 2, 20), dest=tmp_path / "run1")
    meta_2 = source.download_delta(since=date(2026, 2, 20), dest=tmp_path / "run2")

    assert meta_1.record_count == 3
    assert meta_2.record_count == 3
    assert meta_1.checksum_sha256 == meta_2.checksum_sha256

    with gzip.open(meta_1.file_path, "rt", encoding="utf-8") as gzip_file:
        lines = [line.strip() for line in gzip_file if line.strip()]
    assert lines == ['{"code":"1"}', '{"code":"2"}', '{"code":"3"}']


def test_off_delta_ignores_missing_day_payload(tmp_path: Path) -> None:
    day_21 = "https://static.openfoodfacts.org/data/delta/2026-02-21.jsonl.gz"
    transport = _StubTransport(payload_map={day_21: _gzip_payload('{"code":"1"}\n')})

    source = OpenFoodFactsDeltaSource(
        transport=transport,
        today_provider=lambda: date(2026, 2, 22),
    )
    meta = source.download_delta(since=date(2026, 2, 20), dest=tmp_path)

    assert meta.record_count == 1


def test_off_delta_malformed_payload_fails_closed(tmp_path: Path) -> None:
    day_21 = "https://static.openfoodfacts.org/data/delta/2026-02-21.jsonl.gz"
    transport = _StubTransport(payload_map={day_21: b"not-a-gzip-stream"})

    source = OpenFoodFactsDeltaSource(
        transport=transport,
        today_provider=lambda: date(2026, 2, 21),
    )

    with pytest.raises(SnapshotIntegrityError):
        source.download_delta(since=date(2026, 2, 20), dest=tmp_path)


def test_off_delta_update_policy_weekly_threshold() -> None:
    source = OpenFoodFactsDeltaSource(today_provider=lambda: date(2026, 2, 24))
    assert source.has_updates_since(date(2026, 2, 16)) is True
    assert source.has_updates_since(date(2026, 2, 18)) is False


def test_off_full_download_counts_records(tmp_path: Path) -> None:
    full_payload = _gzip_payload('{"code":"1"}\n{"code":"2"}\n')
    transport = _StubTransport(full_chunks=[full_payload])

    source = OpenFoodFactsDeltaSource(
        transport=transport,
        today_provider=lambda: date(2026, 2, 24),
    )

    meta = source.download_full(dest=tmp_path)
    assert meta.mode == "full"
    assert meta.record_count == 2
    assert meta.file_path.exists()


def test_off_full_malformed_payload_fails_closed(tmp_path: Path) -> None:
    transport = _StubTransport(full_chunks=[b"not-a-gzip-stream"])
    source = OpenFoodFactsDeltaSource(
        transport=transport,
        today_provider=lambda: date(2026, 2, 24),
    )

    with pytest.raises(SnapshotIntegrityError):
        source.download_full(dest=tmp_path)


def test_httpx_transport_fetch_and_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = HttpxOFFTransport()

    def _httpx_get_ok(url: str, timeout: int, follow_redirects: bool) -> _FakeResponse:
        _ = (url, timeout, follow_redirects)
        return _FakeResponse(200, b"ok")

    monkeypatch.setattr(
        "core.food_sources.off_delta.httpx.get",
        _httpx_get_ok,
    )
    assert transport.fetch("https://example.com", timeout_seconds=1) == b"ok"

    def _httpx_get_404(url: str, timeout: int, follow_redirects: bool) -> _FakeResponse:
        _ = (url, timeout, follow_redirects)
        return _FakeResponse(404)

    monkeypatch.setattr(
        "core.food_sources.off_delta.httpx.get",
        _httpx_get_404,
    )
    assert transport.fetch("https://example.com", timeout_seconds=1) is None

    failing_response = _FakeResponse(500)

    def _httpx_get_500(url: str, timeout: int, follow_redirects: bool) -> _FakeResponse:
        _ = (url, timeout, follow_redirects)
        return failing_response

    monkeypatch.setattr(
        "core.food_sources.off_delta.httpx.get",
        _httpx_get_500,
    )
    with pytest.raises(RuntimeError):
        transport.fetch("https://example.com", timeout_seconds=1)
    assert failing_response._raise_called is True

    def _httpx_stream_ok(
        method: str, url: str, timeout: int, follow_redirects: bool
    ) -> _FakeStreamResponse:
        _ = (method, url, timeout, follow_redirects)
        return _FakeStreamResponse([b"a", b"b"])

    monkeypatch.setattr(
        "core.food_sources.off_delta.httpx.stream",
        _httpx_stream_ok,
    )
    chunks = list(transport.iter_bytes("https://example.com", timeout_seconds=1, chunk_size=2))
    assert chunks == [b"a", b"b"]
