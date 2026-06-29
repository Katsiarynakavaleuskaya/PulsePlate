"""Tests for private-proxy parity of the emergency wheel manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ci import check_emergency_wheel_mirror_parity as parity

APPROVED_INDEX_URL = "https://packages.pulseplate.app/root/pulseplate/+simple/"
WHEEL_FILENAME = "example_pkg-1.0.0-py3-none-any.whl"


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    manifest = tmp_path / "emergency_python_wheels.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    return manifest


def _active_payload(filename: str = WHEEL_FILENAME) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": "2026-06-29",
        "expires_at": "2099-12-31",
        "reason": "test active manifest",
        "artifacts": [
            {
                "package": "example-pkg",
                "version": "1.0.0",
                "filename": filename,
                "url": f"https://files.pythonhosted.org/packages/example/{filename}",
                "sha256": "a" * 64,
            }
        ],
    }


def test_retired_manifest_succeeds_without_fetching_proxy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(
        tmp_path,
        {
            "schema_version": 1,
            "generated_at": "2026-06-29",
            "reason": "Retired: all active emergency artifacts are mirrored privately.",
            "artifacts": [],
        },
    )

    monkeypatch.setattr(
        parity.proxy_health,
        "fetch_project_page",
        lambda **_kwargs: pytest.fail("retired manifest must not fetch project pages"),
    )

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311", "cp312", "cp313"),
    )

    assert summary.ok is True
    assert summary.retired is True
    assert summary.results == ()


def test_active_manifest_requires_exact_filename_on_private_project_page(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _active_payload()
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    artifacts.append(
        {
            "package": "example-pkg",
            "version": "1.0.0",
            "filename": "example_pkg-1.0.0-cp311-cp311-manylinux_2_17_x86_64.whl",
            "url": (
                "https://files.pythonhosted.org/packages/example/"
                "example_pkg-1.0.0-cp311-cp311-manylinux_2_17_x86_64.whl"
            ),
            "sha256": "b" * 64,
        }
    )
    manifest = _write_manifest(tmp_path, payload)
    observed_urls: list[str] = []

    def fake_fetch(url: str, **_kwargs: object) -> tuple[int, bytes]:
        observed_urls.append(url)
        return (
            200,
            (
                f'<html><a href="{WHEEL_FILENAME}#sha256={"a" * 64}">wheel</a>'
                '<a href="example_pkg-1.0.0-cp311-cp311-manylinux_2_17_x86_64.whl'
                f'#sha256={"b" * 64}">'
                "wheel</a></html>"
            ).encode(),
        )

    monkeypatch.setattr(parity.proxy_health, "fetch_project_page", fake_fetch)

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311",),
    )

    assert summary.ok is True
    assert summary.retired is False
    assert [result.reason for result in summary.results] == ["ok", "ok"]
    assert observed_urls == [APPROVED_INDEX_URL + "example-pkg/"]


def test_active_manifest_fails_when_exact_filename_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, _active_payload())

    def fake_fetch(_url: str, **_kwargs: object) -> tuple[int, bytes]:
        return (200, b'<html><a href="example_pkg-1.0.0-py3-none-any.whl">old</a></html>')

    monkeypatch.setattr(parity.proxy_health, "fetch_project_page", fake_fetch)
    payload = _active_payload(filename="example_pkg-1.0.0.post1-py3-none-any.whl")
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311",),
    )

    assert summary.ok is False
    assert [result.reason for result in summary.results] == ["mirror_lag_exact_filename_missing"]


def test_active_manifest_fails_when_simple_page_hash_mismatches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, _active_payload())

    def fake_fetch(_url: str, **_kwargs: object) -> tuple[int, bytes]:
        return (
            200,
            f'<html><a href="{WHEEL_FILENAME}#sha256={"b" * 64}">wheel</a></html>'.encode(),
        )

    monkeypatch.setattr(parity.proxy_health, "fetch_project_page", fake_fetch)

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311",),
    )

    assert summary.ok is False
    assert [result.reason for result in summary.results] == ["mirror_sha256_mismatch"]


def test_active_manifest_fails_when_simple_page_hash_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, _active_payload())

    def fake_fetch(_url: str, **_kwargs: object) -> tuple[int, bytes]:
        return (200, f'<html><a href="{WHEEL_FILENAME}">wheel</a></html>'.encode())

    monkeypatch.setattr(parity.proxy_health, "fetch_project_page", fake_fetch)

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311",),
    )

    assert summary.ok is False
    assert [result.reason for result in summary.results] == ["simple_page_sha256_missing"]


def test_active_manifest_fails_when_simple_page_hash_is_malformed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest = _write_manifest(tmp_path, _active_payload())

    def fake_fetch(_url: str, **_kwargs: object) -> tuple[int, bytes]:
        return (
            200,
            f'<html><a href="{WHEEL_FILENAME}#sha256=not-a-digest">wheel</a></html>'.encode(),
        )

    monkeypatch.setattr(parity.proxy_health, "fetch_project_page", fake_fetch)

    summary = parity.check_parity(
        manifest=manifest,
        index_url=APPROVED_INDEX_URL,
        timeout_seconds=1.0,
        max_bytes=10_000,
        target_python_versions=("cp311",),
    )

    assert summary.ok is False
    assert [result.reason for result in summary.results] == ["simple_page_sha256_invalid"]


def test_active_manifest_rejects_expired_artifacts(tmp_path: Path) -> None:
    manifest = _write_manifest(tmp_path, _active_payload())
    payload = _active_payload()
    payload["expires_at"] = "2000-01-01"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="active emergency artifact is expired"):
        parity.load_manifest_artifacts(manifest)


def test_empty_manifest_must_be_retired_marker(tmp_path: Path) -> None:
    manifest = _write_manifest(
        tmp_path,
        {
            "schema_version": 1,
            "generated_at": "2026-06-29",
            "reason": "not retired",
            "artifacts": [],
        },
    )

    with pytest.raises(ValueError, match="retired marker"):
        parity.load_manifest_artifacts(manifest)


def test_active_manifest_rejects_wrong_artifact_host(tmp_path: Path) -> None:
    payload = _active_payload()
    artifacts = payload["artifacts"]
    assert isinstance(artifacts, list)
    artifact = artifacts[0]
    assert isinstance(artifact, dict)
    artifact["url"] = f"https://pypi.org/packages/example/{WHEEL_FILENAME}"
    manifest = _write_manifest(tmp_path, payload)

    with pytest.raises(ValueError, match="artifact URL host"):
        parity.load_manifest_artifacts(manifest)
