"""Deterministic guard tests for Phase 1 docs gates."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.ci.check_docs_phase1_gates as gates


def test_phase1_guard_flags_pr_tbd_in_audit_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_doc = tmp_path / "docs" / "audit" / "sample.md"
    audit_doc.parent.mkdir(parents=True)
    audit_doc.write_text("PR: TBD\nEvidence: app/main.py:10\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/audit/sample.md"])
    assert any("PR: TBD" in err for err in errors)


def test_phase1_guard_rejects_missing_evidence_anchor_in_security_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    security_doc = tmp_path / "docs" / "security" / "sample.md"
    security_doc.parent.mkdir(parents=True)
    security_doc.write_text("Remediation implemented without anchors.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/security/sample.md"])
    assert any("missing `file:line` evidence anchor" in err for err in errors)


def test_phase1_guard_accepts_docs_with_evidence_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_doc = tmp_path / "docs" / "audit" / "sample.md"
    audit_doc.parent.mkdir(parents=True)
    audit_doc.write_text(
        "PR: #999\nEvidence: tests/test_repo_policy_guards.py:264\n", encoding="utf-8"
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/audit/sample.md"])
    assert errors == []
