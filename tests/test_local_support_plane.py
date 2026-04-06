"""Deterministic tests for experimental local support-plane storage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.security import agent_control_plane as cp
from scripts.orchestration import local_support_plane as lsp


@pytest.fixture
def allowlist() -> set[tuple[str, str]]:
    return {lsp.default_allowlist_pair()}


@pytest.fixture
def audit_signing_material(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_AUTO_SAFE)
    material = "unit-test-hmac-key-local-support-plane-2026"  # pragma: allowlist secret
    monkeypatch.setenv(cp.AUDIT_SIGNING_KEY_ENV, material)
    return material


def test_normalize_key_rejects_empty_and_oversized() -> None:
    with pytest.raises(ValueError, match="support_plane_key_invalid_length"):
        lsp.normalize_key("")
    with pytest.raises(ValueError, match="support_plane_key_invalid_length"):
        lsp.normalize_key("a" * 129)


def test_normalize_key_rejects_path_like() -> None:
    with pytest.raises(ValueError, match="support_plane_key_invalid_chars"):
        lsp.normalize_key("../etc/passwd")
    with pytest.raises(ValueError, match="support_plane_key_invalid_chars"):
        lsp.normalize_key("foo/bar")


def test_resolve_support_plane_root_env_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(lsp.SUPPORT_PLANE_ROOT_ENV, str(tmp_path))
    assert lsp.resolve_support_plane_root() == tmp_path.resolve()


def test_put_get_delete_roundtrip(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    audit_log = tmp_path / "audit.jsonl"
    root = tmp_path / "store"
    lsp.put_record(
        "session.note",
        {"hello": "world"},
        allowlist=allowlist,
        root_override=root,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    loaded = lsp.get_record("session.note", root_override=root)
    assert loaded == {"hello": "world"}
    assert audit_log.is_file()
    line = audit_log.read_text(encoding="utf-8").strip()
    payload = json.loads(line)
    assert payload["envelope"]["action"] == lsp.POLICY_ACTION
    assert payload["metadata"]["op"] == "put"

    removed = lsp.delete_record(
        "session.note",
        allowlist=allowlist,
        root_override=root,
        audit_secret=audit_signing_material,
        audit_log_path=audit_log,
    )
    assert removed is True
    assert lsp.get_record("session.note", root_override=root) is None


def test_put_record_denied_without_allowlist(
    tmp_path: Path,
    audit_signing_material: str,
) -> None:
    with pytest.raises(PermissionError, match="Policy denied"):
        lsp.put_record(
            "x",
            {"a": 1},
            allowlist=set(),
            root_override=tmp_path,
            audit_secret=audit_signing_material,
            write_audit=False,
        )


def test_put_record_blocked_execution_mode(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(cp.EXECUTION_MODE_ENV, cp.EXECUTION_MODE_BLOCKED)
    with pytest.raises(PermissionError, match="Execution mode blocked"):
        lsp.put_record(
            "x",
            {"a": 1},
            allowlist=allowlist,
            root_override=tmp_path,
            write_audit=False,
        )


def test_put_record_value_size_limit(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    huge = {"k": "x" * lsp.MAX_VALUE_BYTES}
    with pytest.raises(ValueError, match="support_plane_value_too_large"):
        lsp.put_record(
            "big",
            huge,
            allowlist=allowlist,
            root_override=tmp_path,
            audit_secret=audit_signing_material,
            write_audit=False,
        )


def test_delete_record_returns_false_when_missing(
    tmp_path: Path,
    allowlist: set[tuple[str, str]],
    audit_signing_material: str,
) -> None:
    audit_log = tmp_path / "audit.jsonl"
    assert (
        lsp.delete_record(
            "missing",
            allowlist=allowlist,
            root_override=tmp_path,
            audit_secret=audit_signing_material,
            audit_log_path=audit_log,
        )
        is False
    )
    assert not audit_log.exists()
