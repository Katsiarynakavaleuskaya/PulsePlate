"""Deterministic guard tests for Phase 1 docs gates."""

from __future__ import annotations

import json
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
cache, and not user-account truth surfaces.

If the gate opens later, rollout order is fixed:
1. SC-G1 rollout gate contract
2. SC-G2 exact/fuzzy cache scaffold
3. SC-G3 observability and false-hit harness
4. SC-G4 bounded `/insight` semantic-cache experiment
5. SC-G5 backend selection
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


def test_phase1_guard_does_not_run_semantic_cache_gate_for_unrelated_roadmap_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roadmap_doc = tmp_path / "docs" / "roadmap" / "UNRELATED.md"
    roadmap_doc.parent.mkdir(parents=True)
    roadmap_doc.write_text("philosophical semantic-cache is live.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/roadmap/UNRELATED.md"])

    assert errors == []


def test_phase1_guard_still_scans_philosophy_downstream_ledger_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backlog_doc = tmp_path / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
    backlog_doc.parent.mkdir(parents=True)
    backlog_doc.write_text("philosophical semantic-cache is live.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/roadmap/BACKLOG_LEDGER.md"])

    assert errors == [
        "docs/roadmap/BACKLOG_LEDGER.md: forbidden philosophy admission contract claim: "
        "philosophical semantic cache live"
    ]


def test_phase1_guard_runs_semantic_cache_checker_for_rollout_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Contract\n\nSemantic cache is now open.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md"]
    )

    assert any("rollout contract missing anchor" in error for error in errors)
    assert any("forbidden semantic-cache claim" in error for error in errors)


def test_phase1_guard_runs_semantic_cache_checker_for_scaffold_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contract = tmp_path / "docs" / "orchestration" / "contracts" / "EXACT_FUZZY_CACHE_SCAFFOLD.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        "# Contract\n\nSC-G2 permits embeddings.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md"]
    )

    assert any("exact/fuzzy scaffold contract missing anchor" in error for error in errors)
    assert any("forbidden exact/fuzzy scaffold claim" in error for error in errors)


def test_phase1_guard_validates_semantic_cache_backend_selection_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = (
        gates.REPO_ROOT
        / "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
    )
    source_schema = source_contract.with_suffix(".schema.json")
    contract = (
        tmp_path / "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
    )
    schema_path = contract.with_suffix(".schema.json")
    contract.parent.mkdir(parents=True)
    contract.write_text(source_contract.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["runtime_allowed"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[
            "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.schema.json"
        ]
    )

    assert any(
        "backend selection schema const missing for runtime_allowed" in error for error in errors
    )


def test_phase1_guard_validates_semantic_cache_backend_selection_schema_for_contract_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = (
        gates.REPO_ROOT
        / "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
    )
    source_schema = source_contract.with_suffix(".schema.json")
    contract = (
        tmp_path / "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
    )
    schema_path = contract.with_suffix(".schema.json")
    contract.parent.mkdir(parents=True)
    contract.write_text(source_contract.read_text(encoding="utf-8"), encoding="utf-8")
    schema_path.write_text(source_schema.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        gates,
        "_load_semantic_cache_backend_selection_schema_validator",
        lambda: lambda *, schema_text, contract_text: ["schema validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"]
    )

    assert any("schema validator called" in error for error in errors)
