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


def test_phase1_guard_flags_list_style_pr_tbd_in_audit_docs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_doc = tmp_path / "docs" / "audit" / "sample.md"
    audit_doc.parent.mkdir(parents=True)
    audit_doc.write_text("- **PR:** TBD\nEvidence: docs/audit/sample.md:1\n", encoding="utf-8")
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


def test_phase1_guard_rejects_host_port_as_evidence_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    security_doc = tmp_path / "docs" / "security" / "sample.md"
    security_doc.parent.mkdir(parents=True)
    security_doc.write_text("Endpoint check: example.com:443\n", encoding="utf-8")
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


def test_phase1_guard_accepts_dot_prefixed_file_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    audit_doc = tmp_path / "docs" / "audit" / "sample.md"
    audit_doc.parent.mkdir(parents=True)
    audit_doc.write_text("Evidence: .github/workflows/ci.yml:140\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/audit/sample.md"])
    assert errors == []


def test_phase1_guard_runs_semantic_cache_gate_for_gate_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gate_doc = tmp_path / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate_doc.parent.mkdir(parents=True)
    gate_doc.write_text(
        """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: open -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

Semantic cache remains gate-closed until a reviewed gate-open PR changes these
markers and documents current-head CI governance.

Semantic cache belongs only to the product AI runtime rail.

Semantic cache is not advisory wiki, not workforce memory, not a second source
of truth, not billing/auth/entitlement truth, and not a compliance/legal output
cache.

If the gate opens later, rollout order is fixed:
1. docs contract
2. exact/fuzzy cache
3. bounded semantic cache for `/insight`
4. observability / false-hit guardrails
5. Redis/GPTCache backend only later
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"]
    )

    assert errors == [
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md: "
        "invalid marker SEMANTIC_CACHE_GATE_STATUS: expected closed, got open"
    ]
