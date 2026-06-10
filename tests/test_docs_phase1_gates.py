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
    companion_paths = sorted(
        set(gates.PHILOSOPHY_GATE_OPEN_PRECONDITIONS_INPUTS)
        | set(gates.PHILOSOPHY_SOURCE_CORPUS_INPUTS)
    )
    for relpath in companion_paths:
        if relpath in skipped:
            continue
        source = REPO_ROOT / relpath
        if not source.exists():
            continue
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

The runtime prerequisite train is closed by PR #1203 merge commit
831d62d8be0da7307e5a0f2673d8c33dbf53ca49, PR #1395 merge commit
2f8a9af461cec483aa81a774cce7496c6bf65a8a, and PR #1742 merge commit
cb1db8b40141817b3ca856de570b8fc02e2ae9fa. A reviewed gate-open PR must still
change the machine markers before runtime semantic-cache work can begin.

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
        "invalid marker SEMANTIC_CACHE_GATE_STATUS: expected closed, got open",
        "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md: "
        "roadmap marker SEMANTIC_CACHE_GATE_STATUS must be closed",
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


def test_phase1_guard_validates_context_compression_contract_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = gates.REPO_ROOT / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_DOC
    source_schema = gates.REPO_ROOT / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_SCHEMA
    contract = tmp_path / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_DOC
    schema_path = tmp_path / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_SCHEMA
    contract.parent.mkdir(parents=True)
    contract.write_text(
        source_contract.read_text(encoding="utf-8")
        + "\nContext compression permits provider calls.\n"
        + "Context compression permits runtime serving.\n",
        encoding="utf-8",
    )
    schema_path.write_text(source_schema.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_DOC]
    )

    assert any("forbidden context compression claim: provider calls" in error for error in errors)
    assert any("forbidden context compression claim: runtime serving" in error for error in errors)


def test_phase1_guard_validates_context_compression_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = gates.REPO_ROOT / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_DOC
    source_schema = gates.REPO_ROOT / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_SCHEMA
    contract = tmp_path / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_DOC
    schema_path = tmp_path / gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_SCHEMA
    contract.parent.mkdir(parents=True)
    contract.write_text(source_contract.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["provider_calls_allowed"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_CONTEXT_COMPRESSION_CONTRACT_SCHEMA]
    )

    assert any(
        "context compression schema provider_calls_allowed must be const false" in error
        for error in errors
    )


def test_phase1_guard_validates_provider_model_tier_routing_contract_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = (
        gates.REPO_ROOT / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_DOC
    )
    source_schema = (
        gates.REPO_ROOT / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_SCHEMA
    )
    contract = tmp_path / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_DOC
    schema_path = tmp_path / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_SCHEMA
    contract.parent.mkdir(parents=True)
    contract.write_text(
        source_contract.read_text(encoding="utf-8")
        + "\nProvider/model-tier routing performs provider calls.\n"
        + "Provider/model-tier routing allows model downgrade.\n",
        encoding="utf-8",
    )
    schema_path.write_text(source_schema.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_DOC]
    )

    assert any(
        "forbidden provider/model-tier routing claim: provider calls" in error for error in errors
    )
    assert any(
        "forbidden provider/model-tier routing claim: model downgrade" in error for error in errors
    )


def test_phase1_guard_validates_provider_model_tier_routing_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_contract = (
        gates.REPO_ROOT / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_DOC
    )
    source_schema = (
        gates.REPO_ROOT / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_SCHEMA
    )
    contract = tmp_path / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_DOC
    schema_path = tmp_path / gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_SCHEMA
    contract.parent.mkdir(parents=True)
    contract.write_text(source_contract.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["provider_calls_allowed"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_PROVIDER_MODEL_TIER_ROUTING_CONTRACT_SCHEMA]
    )

    assert any(
        "provider/model-tier routing schema provider_calls_allowed must be const false" in error
        for error in errors
    )


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


def test_phase1_guard_validates_verification_provenance_admission_report_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_verification_provenance_admission_report_validator",
        lambda: lambda **_kwargs: ["verification provenance validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT]
    )

    assert any("verification provenance validator called" in error for error in errors)


def test_phase1_guard_validates_verification_provenance_admission_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_report = gates.REPO_ROOT / gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT
    source_schema = gates.REPO_ROOT / gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT_SCHEMA
    report = tmp_path / gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT
    schema_path = tmp_path / gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT_SCHEMA
    report.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(source_report.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["generated_at"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT_SCHEMA]
    )

    assert any("schema const mismatch for generated_at" in error for error in errors)


def test_phase1_guard_validates_semantic_cache_offline_admission_report_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_semantic_cache_offline_admission_runner_report_validator",
        lambda: lambda **_kwargs: ["semantic cache offline validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT]
    )

    assert any("semantic cache offline validator called" in error for error in errors)


def test_phase1_guard_validates_semantic_cache_offline_admission_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_report = gates.REPO_ROOT / gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT
    source_schema = gates.REPO_ROOT / gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT_SCHEMA
    report = tmp_path / gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT
    schema_path = tmp_path / gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT_SCHEMA
    report.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(source_report.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["generated_at"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT_SCHEMA]
    )

    assert any("semantic cache offline admission runner schema drift" in error for error in errors)


def test_phase1_guard_validates_semantic_cache_shadow_admission_report_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_semantic_cache_shadow_admission_harness_report_validator",
        lambda: lambda **_kwargs: ["semantic cache shadow validator called"],
    )

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT]
    )

    assert any("semantic cache shadow validator called" in error for error in errors)


def test_phase1_guard_validates_semantic_cache_shadow_admission_schema_only_edits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_report = gates.REPO_ROOT / gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT
    source_schema = gates.REPO_ROOT / gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT_SCHEMA
    report = tmp_path / gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT
    schema_path = tmp_path / gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT_SCHEMA
    report.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(source_report.read_text(encoding="utf-8"), encoding="utf-8")
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    del schema["properties"]["generated_at"]["const"]
    schema_path.write_text(json.dumps(schema, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(
        markdown_files=[gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT_SCHEMA]
    )

    assert any("semantic cache shadow admission harness schema drift" in error for error in errors)


def test_ci_docs_phase1_protected_json_targets_include_deletions() -> None:
    workflow_text = (gates.REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for relpath in (
        gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT,
        gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT,
        gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT,
    ):
        protected_target = f"'{relpath}' \\"
        target_index = workflow_text.index(protected_target)
        diff_index = workflow_text.rfind("git diff --name-only", 0, target_index)
        protected_diff_command = workflow_text[diff_index:target_index]

        assert '--diff-filter=ACDMRT "$BASE_REF"...HEAD -- \\' in protected_diff_command


@pytest.mark.parametrize(
    "relpath",
    [
        gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT,
        gates.VERIFICATION_PROVENANCE_ADMISSION_REPORT_SCHEMA,
        gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT,
        gates.SEMANTIC_CACHE_OFFLINE_ADMISSION_RUNNER_REPORT_SCHEMA,
        gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT,
        gates.SEMANTIC_CACHE_SHADOW_ADMISSION_HARNESS_REPORT_SCHEMA,
    ],
)
def test_phase1_guard_rejects_deleted_protected_contract(
    relpath: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=[relpath])

    assert errors == [f"{relpath}: protected contract file missing"]


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


def test_phase1_guard_validates_philosophy_gate_open_preconditions_for_alignment_schema(
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
    alignment_schema = tmp_path / gates.PHILOSOPHY_ALIGNMENT_RULE_SCHEMA
    alignment_schema.parent.mkdir(parents=True, exist_ok=True)
    alignment_schema.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)

    errors = gates.check_docs_phase1_guards(markdown_files=[gates.PHILOSOPHY_ALIGNMENT_RULE_SCHEMA])

    assert any("gate-open preconditions report drift" in error for error in errors)


def test_phase1_guard_validates_philosophy_alignment_rule_schema_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_philosophy_alignment_rule_validator",
        lambda: lambda **_kwargs: ["alignment validator called"],
    )

    errors = gates.check_docs_phase1_guards(markdown_files=[gates.PHILOSOPHY_ALIGNMENT_RULE_SCHEMA])

    assert any("alignment validator called" in error for error in errors)


def test_phase1_guard_validates_philosophy_alignment_rule_record_edits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_path = tmp_path / gates.PHILOSOPHY_ALIGNMENT_RULE_SCHEMA
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text("{}", encoding="utf-8")
    record_relpath = f"{gates.PHILOSOPHY_ALIGNMENT_RULE_RECORD_PREFIX}sample.json"
    record_path = tmp_path / record_relpath
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text('{"rule_id": "sample"}', encoding="utf-8")
    calls: list[dict[str, object]] = []

    def _fake_validator(**kwargs: object) -> list[str]:
        calls.append(kwargs)
        return ["record validator called"]

    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        gates,
        "_load_philosophy_alignment_rule_validator",
        lambda: _fake_validator,
    )

    errors = gates.check_docs_phase1_guards(markdown_files=[record_relpath])

    assert any("record validator called" in error for error in errors)
    assert calls
    assert calls[0]["schema_text"] == "{}"
    assert calls[0]["rule_texts"] == {record_relpath: '{"rule_id": "sample"}'}


def test_phase1_guard_collects_nested_philosophy_alignment_rule_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    schema_path = tmp_path / gates.PHILOSOPHY_ALIGNMENT_RULE_SCHEMA
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text("{}", encoding="utf-8")
    root_record_relpath = f"{gates.PHILOSOPHY_ALIGNMENT_RULE_RECORD_PREFIX}sample.json"
    nested_record_relpath = f"{gates.PHILOSOPHY_ALIGNMENT_RULE_RECORD_PREFIX}wellness/scope.json"
    root_record_path = tmp_path / root_record_relpath
    nested_record_path = tmp_path / nested_record_relpath
    root_record_path.parent.mkdir(parents=True, exist_ok=True)
    nested_record_path.parent.mkdir(parents=True, exist_ok=True)
    root_record_path.write_text('{"rule_id": "sample"}', encoding="utf-8")
    nested_record_path.write_text('{"rule_id": "scope"}', encoding="utf-8")
    calls: list[dict[str, object]] = []

    def _fake_validator(**kwargs: object) -> list[str]:
        calls.append(kwargs)
        return ["record validator called"]

    monkeypatch.setattr(gates, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(gates, "_load_philosophy_alignment_rule_validator", lambda: _fake_validator)

    errors = gates.check_docs_phase1_guards(markdown_files=[nested_record_relpath])

    assert any("record validator called" in error for error in errors)
    assert calls
    assert calls[0]["rule_texts"] == {
        root_record_relpath: '{"rule_id": "sample"}',
        nested_record_relpath: '{"rule_id": "scope"}',
    }
