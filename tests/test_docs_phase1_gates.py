"""Deterministic guard tests for Phase 1 docs gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.ci.check_docs_phase1_gates as gates

REPO_ROOT = Path(__file__).resolve().parents[1]


def _disable_gate_open_preconditions_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_gate_open_preconditions_validator",
        lambda: lambda **_kwargs: [],
    )


def _copy_gate_open_precondition_companions(
    tmp_path: Path,
    *,
    skip: set[str] | None = None,
) -> None:
    skipped = skip or set()
    for relpath in gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_INPUTS:
        if relpath in skipped:
            continue
        source = REPO_ROOT / relpath
        destination = tmp_path / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _expected_forbidden_philosophy_claim(path: str, claim: str) -> str:
    return (
        f"{path}: forbidden philosophy admission contract claim: "
        f"{claim.replace('-', ' ').replace(' is live', ' live').rstrip('.')}"
    )


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
    _disable_gate_open_preconditions_validator(monkeypatch)
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
    _copy_gate_open_precondition_companions(tmp_path, skip={gates.SEMANTIC_CACHE_GATE_DOC})
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
    _disable_gate_open_preconditions_validator(monkeypatch)
    claim = "philosophical semantic-cache is live"
    backlog_doc = tmp_path / "docs" / "roadmap" / "BACKLOG_LEDGER.md"
    backlog_doc.parent.mkdir(parents=True)
    backlog_doc.write_text(f"{claim}.\n", encoding="utf-8")
    _copy_gate_open_precondition_companions(
        tmp_path,
        skip={"docs/roadmap/BACKLOG_LEDGER.md"},
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=["docs/roadmap/BACKLOG_LEDGER.md"])

    assert errors == [_expected_forbidden_philosophy_claim("docs/roadmap/BACKLOG_LEDGER.md", claim)]


def test_phase1_guard_scans_comprehensive_philosophy_insight_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = "philosophical semantic-cache is live"
    insight_doc = (
        tmp_path / "docs" / "insights" / "COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md"
    )
    insight_doc.parent.mkdir(parents=True)
    insight_doc.write_text(f"{claim}.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md"]
    )

    assert errors == [
        _expected_forbidden_philosophy_claim(
            "docs/insights/COMPREHENSIVE_PHILOSOPHY_LOGIC_MATH_CBT_ANALYSIS.md",
            claim,
        )
    ]


def test_phase1_guard_scans_philosophical_orchestration_packet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = "philosophical semantic-cache is live"
    packet_path = "docs/orchestration/WAVE6_A6_PHILOSOPHICAL_ROLLOUT_W1_PACKET_2026-04-22.md"
    packet_doc = tmp_path / packet_path
    packet_doc.parent.mkdir(parents=True)
    packet_doc.write_text(f"{claim}.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=[packet_path])

    assert errors == [_expected_forbidden_philosophy_claim(packet_path, claim)]


def test_phase1_guard_scans_philosophy_contract_sibling_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = "philosophical semantic-cache is live"
    contract_path = "docs/orchestration/contracts/PHILOSOPHY_FUTURE_CONTRACT.md"
    contract_doc = tmp_path / contract_path
    contract_doc.parent.mkdir(parents=True)
    contract_doc.write_text(f"{claim}.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=[contract_path])

    assert errors == [_expected_forbidden_philosophy_claim(contract_path, claim)]


def test_phase1_guard_runs_philosophy_checker_for_semantic_cache_gate_doc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = "philosophical semantic-cache is live"
    gate_doc = tmp_path / "docs" / "roadmap" / "PulsePlate_Semantic_Cache_Gate_and_Plan.md"
    gate_doc.parent.mkdir(parents=True)
    gate_doc.write_text(f"# Gate\n\n{claim}.\n", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"]
    )

    assert (
        _expected_forbidden_philosophy_claim(
            "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md",
            claim,
        )
        in errors
    )


def test_phase1_guard_runs_semantic_cache_checker_for_rollout_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claim = "philosophical semantic-cache is live"
    contract = tmp_path / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"
    contract.parent.mkdir(parents=True)
    contract.write_text(
        f"# Contract\n\nSemantic cache is now open.\n\n{claim}.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=["docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md"]
    )

    assert any("rollout contract missing anchor" in error for error in errors)
    assert any("forbidden semantic-cache claim" in error for error in errors)
    assert (
        _expected_forbidden_philosophy_claim(
            "docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md",
            claim,
        )
        in errors
    )


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


def test_phase1_guard_validates_philosophy_admission_dry_run_report_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_admission_dry_run_report_validator",
        lambda: lambda **_kwargs: ["dry-run validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT]
    )

    assert any("dry-run validator called" in error for error in errors)


def test_phase1_guard_validates_philosophy_admission_dry_run_for_policy_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_admission_dry_run_report_validator",
        lambda: lambda **_kwargs: ["dry-run validator called for policy"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY]
    )

    assert any("dry-run validator called for policy" in error for error in errors)


def test_phase1_guard_validates_philosophy_admission_dry_run_for_oracle_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_admission_dry_run_report_validator",
        lambda: lambda **_kwargs: ["dry-run validator called for oracle"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE]
    )

    assert any("dry-run validator called for oracle" in error for error in errors)


def test_phase1_guard_validates_philosophy_admission_dry_run_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_report = gates.REPO_ROOT / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT
    source_schema = gates.REPO_ROOT / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT_SCHEMA
    source_policy = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY
    source_policy_schema = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA
    source_oracle = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE
    report = tmp_path / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT
    schema_path = tmp_path / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT_SCHEMA
    policy = tmp_path / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY
    policy_schema = tmp_path / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA
    oracle = tmp_path / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE
    for path in (report, schema_path, policy, policy_schema, oracle):
        path.parent.mkdir(parents=True, exist_ok=True)

    report.write_text(source_report.read_text(encoding="utf-8"), encoding="utf-8")
    policy.write_text(source_policy.read_text(encoding="utf-8"), encoding="utf-8")
    policy_schema.write_text(
        source_policy_schema.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    oracle.write_text(source_oracle.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["gate_status"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT_SCHEMA]
    )

    assert any("dry-run schema const missing for gate_status" in error for error in errors)


def test_phase1_guard_validates_philosophy_gate_open_preconditions_report_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_gate_open_preconditions_validator",
        lambda: lambda **_kwargs: ["gate-open preconditions validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT]
    )

    assert any("gate-open preconditions validator called" in error for error in errors)


def test_phase1_guard_validates_philosophy_gate_open_preconditions_for_roadmap_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_gate_open_preconditions_validator",
        lambda: lambda **_kwargs: ["gate-open preconditions validator called for roadmap"],
    )

    errors = gates.check_docs_phase1_guards(markdown_files=[gates.SEMANTIC_CACHE_GATE_DOC])

    assert any("gate-open preconditions validator called for roadmap" in error for error in errors)


def test_phase1_guard_validates_philosophy_gate_open_preconditions_schema_only_edits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_report = gates.REPO_ROOT / gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT
    source_schema = gates.REPO_ROOT / gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT_SCHEMA
    source_policy = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY
    source_policy_schema = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA
    source_oracle = gates.REPO_ROOT / gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE
    source_dry_run = gates.REPO_ROOT / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT
    source_dry_run_schema = gates.REPO_ROOT / gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT_SCHEMA
    source_roadmap = gates.REPO_ROOT / gates.SEMANTIC_CACHE_GATE_DOC
    source_ledger = gates.REPO_ROOT / "docs/roadmap/BACKLOG_LEDGER.md"

    targets = {
        gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT: source_report,
        gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT_SCHEMA: source_schema,
        gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY: source_policy,
        gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA: source_policy_schema,
        gates.PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE: source_oracle,
        gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT: source_dry_run,
        gates.PHILOSOPHY_ADMISSION_DRY_RUN_REPORT_SCHEMA: source_dry_run_schema,
        gates.SEMANTIC_CACHE_GATE_DOC: source_roadmap,
        "docs/roadmap/BACKLOG_LEDGER.md": source_ledger,
    }
    for relpath, source in targets.items():
        destination = tmp_path / relpath
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    schema_path = tmp_path / gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT_SCHEMA
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    del schema["properties"]["runtime_allowed"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_REPORT_SCHEMA]
    )

    assert any(
        "gate-open preconditions schema const missing for runtime_allowed" in error
        for error in errors
    )
