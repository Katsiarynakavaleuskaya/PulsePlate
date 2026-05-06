from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_gate.py"
CONTRACT = REPO_ROOT / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"
SCHEMA = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.schema.json"
)


def _normalize(text: str) -> str:
    return " ".join(text.replace("`", "").lower().split())


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def _run_checker(contract: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER)]
    if contract is not None:
        args.extend(["--contract", str(contract)])
    return subprocess.run(args, check=False, text=True, capture_output=True)


def _write_contract(tmp_path: Path, text: str) -> Path:
    contract = tmp_path / "contract.md"
    contract.write_text(text, encoding="utf-8")
    return contract


def test_rollout_contract_exists_and_keeps_gate_closed() -> None:
    text = _normalize(_contract_text())

    assert CONTRACT.exists()
    assert "gate remains closed" in text
    assert "does not open the semantic-cache gate" in text
    assert "does not implement semantic cache" in text


def test_rollout_contract_includes_sc_g1_through_sc_g5_in_order() -> None:
    text = _normalize(_contract_text())
    phases = (
        "sc-g1 rollout gate contract",
        "sc-g2 exact/fuzzy cache scaffold",
        "sc-g3 observability and false-hit harness",
        "sc-g4 bounded /insight semantic-cache experiment",
        "sc-g5 backend selection",
    )

    positions = [text.index(phase) for phase in phases]

    assert positions == sorted(positions)


def test_exact_fuzzy_precedes_bounded_semantic_cache() -> None:
    text = _normalize(_contract_text())

    assert text.index("sc-g2 exact/fuzzy cache scaffold") < text.index(
        "sc-g4 bounded /insight semantic-cache experiment"
    )
    assert "no embeddings" in text
    assert "no redis" in text
    assert "no gptcache" in text


def test_bounded_insight_surface_is_feature_flagged_and_off_by_default() -> None:
    text = _normalize(_contract_text())

    assert "bounded, repetitive /insight-style product ai output" in text
    assert "feature-flagged" in text
    assert "off by default" in text
    assert "request-time disableable" in text


@pytest.mark.parametrize(
    "phrase",
    [
        "exact duplicate hit",
        "normalized fuzzy hit",
        "semantic false positive",
        "stale-source hit",
        "policy-version mismatch hit",
        "model-version mismatch hit",
        "user-context leakage hit",
        "false_hit_rate = unsafe_or_incorrect_cached_serves / semantic_cache_serves",
        "negative controls",
        "fresh_runtime_answer",
        "candidate_cached_answer",
    ],
)
def test_false_hit_risk_model_exists(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "metric",
    [
        "eligible_hit_rate",
        "served_hit_rate",
        "false_hit_rate",
        "cache_precision_proxy",
        "stale_answer_rate",
        "fallback_rate",
        "p50/p95 latency_saved",
        "provider_calls_avoided",
        "cost_saved",
        "quota_consumption_delta",
        "admission-blocked-cache-hit count",
    ],
)
def test_observability_metrics_exist(metric: str) -> None:
    assert _normalize(metric) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "kill switch",
        "environment flag",
        "runtime flag snapshot",
        "request-time disable",
        "cache bypass",
        "no-cache fallback path",
        "purge/invalidation path",
        "deterministic tests proving disabled state",
        "rollback runbook",
    ],
)
def test_kill_switch_and_rollback_requirements_exist(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "billing/auth/entitlement",
        "legal/compliance outputs",
        "user-account truth",
        "HealthKit-derived sensitive payloads",
        "raw prompts",
        "raw model responses",
        "secrets, tokens, credentials",
        "advisory wiki pages as product truth",
    ],
)
def test_blocked_surfaces_are_explicit(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "source fingerprints",
        "eval event IDs",
        "admission decision IDs",
        "promotion/replay lineage",
        "policy version",
        "model/provider key",
        "transparency notice id",
        "safety flags",
        "E4-compatible admission semantics",
    ],
)
def test_evidence_graph_and_admission_linkage_exists(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


def test_rollout_schema_has_required_keys() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    required = {
        "gate_status",
        "implementation_allowed",
        "runtime_allowed",
        "allowed_rail",
        "first_allowed_surface",
        "blocked_surfaces",
        "required_lineage_fields",
        "required_metrics",
        "required_kill_switches",
        "rollout_phases",
        "gate_open_requirements",
    }

    assert set(schema["required"]) == required
    assert set(schema["properties"]) == required
    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["runtime_allowed"]["const"] is False


def test_checker_passes_on_current_closed_rollout_contract() -> None:
    result = _run_checker()

    assert result.returncode == 0, result.stderr
    assert "semantic-cache rollout contract closed" in result.stdout


@pytest.mark.parametrize(
    "claim",
    [
        "Semantic cache is active.",
        "Semantic cache is implemented.",
        "Semantic-cache is enabled.",
        "Semantic cache is now open.",
        "Semantic cache is approved.",
        "Evidence Graph unlocks semantic cache.",
    ],
)
def test_checker_fails_if_contract_implies_cache_is_live(tmp_path: Path, claim: str) -> None:
    contract = _write_contract(tmp_path, _contract_text() + f"\n{claim}\n")

    result = _run_checker(contract)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim" in result.stderr


def test_checker_fails_if_contract_phase_is_missing(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        _contract_text().replace("3. SC-G3 observability and false-hit harness.\n", ""),
    )

    result = _run_checker(contract)

    assert result.returncode == 1
    assert (
        "rollout contract missing phase: SC-G3 observability and false-hit harness" in result.stderr
    )


def test_checker_has_no_runtime_provider_cache_or_eval_imports() -> None:
    tree = ast.parse(CHECKER.read_text(encoding="utf-8"))
    forbidden_prefixes = (
        "app",
        "legacy_app",
        "providers",
        "llm",
        "fastapi",
        "sqlalchemy",
        "redis",
        "cache",
        "semantic_cache",
        "gptcache",
        "scripts.evals",
        "evals",
        "core.rag",
    )
    imports: list[str] = []
    dynamic_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            dynamic_imports.append(node.args[0].value)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            dynamic_imports.append(node.args[0].value)

    offenders = [
        name
        for name in imports + dynamic_imports
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]
    assert offenders == []
