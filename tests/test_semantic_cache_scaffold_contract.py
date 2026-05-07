from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ci.check_semantic_cache_gate import validate_exact_fuzzy_scaffold_contract
from tests.helpers.semantic_cache_import_guard import (
    assert_no_forbidden_semantic_cache_calls,
    assert_no_forbidden_semantic_cache_imports,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_gate.py"
DOCS_PHASE1 = REPO_ROOT / "scripts" / "ci" / "check_docs_phase1_gates.py"
SCAFFOLD_CONTRACT = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "EXACT_FUZZY_CACHE_SCAFFOLD.md"
)
SCAFFOLD_SCHEMA = (
    REPO_ROOT / "docs" / "orchestration" / "contracts" / "EXACT_FUZZY_CACHE_SCAFFOLD.schema.json"
)
SCAFFOLD_MODULE = REPO_ROOT / "core" / "ai" / "exact_fuzzy_cache.py"
CORE_AI_INIT = REPO_ROOT / "core" / "ai" / "__init__.py"


def _normalize(text: str) -> str:
    return " ".join(text.replace("`", "").lower().split())


def _contract_text() -> str:
    return SCAFFOLD_CONTRACT.read_text(encoding="utf-8")


def _run_checker(scaffold_contract: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER)]
    if scaffold_contract is not None:
        args.extend(["--scaffold-contract", str(scaffold_contract)])
    return subprocess.run(args, check=False, text=True, capture_output=True)


def test_scaffold_contract_exists_and_keeps_gate_closed() -> None:
    text = _normalize(_contract_text())

    assert SCAFFOLD_CONTRACT.exists()
    assert "sc-g2 defines a deterministic exact/fuzzy cache scaffold" in text
    assert "does not open the semantic-cache gate" in text
    assert "does not enable runtime caching" in text
    assert "does not serve cached output" in text
    assert "gate status: closed" in text
    assert "runtime allowed: false" in text
    assert "implementation allowed: false" in text


def test_scaffold_contract_is_exact_fuzzy_only_and_precedes_future_phases() -> None:
    text = _normalize(_contract_text())

    assert text.index("sc-g2 is deterministic exact/fuzzy only") < text.index(
        "sc-g3 observability and false-hit harness is still required"
    )
    assert text.index("sc-g3 observability and false-hit harness is still required") < text.index(
        "sc-g4 bounded /insight semantic-cache experiment"
    )


@pytest.mark.parametrize(
    "phrase",
    [
        "stdlib only",
        "no stemming",
        "synonym table",
        "no semantic proxy",
        "exact",
        "fuzzy_reordered_tokens",
        "fuzzy_near_duplicate",
        "integer basis-point scoring",
    ],
)
def test_scaffold_contract_defines_deterministic_lexical_matching(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "surface",
        "context fingerprint",
        "source fingerprints",
        "policy version",
        "provider key",
        "model key",
        "user tier",
        "transparency notice id",
        "Any mismatch is a hard miss",
    ],
)
def test_scaffold_contract_defines_partition_hard_misses(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "embeddings",
        "semantic similarity",
        "vector search",
        "Redis",
        "GPTCache",
        "provider calls",
        "runtime wiring",
        "FastAPI or OpenAPI changes",
        "DB writes or storage backend",
        "raw prompts",
        "raw model responses",
    ],
)
def test_scaffold_contract_blocks_semantic_runtime_and_payload_scope(phrase: str) -> None:
    text = _normalize(_contract_text())

    assert _normalize(phrase) in text


@pytest.mark.parametrize(
    "phrase",
    [
        "Evidence Graph lineage required",
        "admission linkage required",
        "replay linkage required",
        "admission decision ID",
        "eval event IDs",
        "promotion IDs",
        "replay entry IDs",
        "safety flags",
    ],
)
def test_scaffold_contract_requires_evidence_graph_linkage(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


@pytest.mark.parametrize(
    "phrase",
    [
        "advisory wiki",
        "workforce memory",
        "billing/auth/entitlement",
        "legal/compliance outputs",
        "account truth",
        "HealthKit-derived sensitive payloads",
        "secrets or credentials",
        "highly personalized coaching state",
    ],
)
def test_scaffold_contract_blocks_sensitive_surfaces(phrase: str) -> None:
    assert _normalize(phrase) in _normalize(_contract_text())


def test_scaffold_schema_has_required_keys_and_closed_values() -> None:
    schema = json.loads(SCAFFOLD_SCHEMA.read_text(encoding="utf-8"))
    required = {
        "gate_status",
        "runtime_allowed",
        "implementation_allowed",
        "scaffold_phase",
        "allowed_match_modes",
        "blocked_match_modes",
        "blocked_backends",
        "blocked_surfaces",
        "required_inputs",
        "required_outputs",
        "required_followups",
    }

    assert set(schema["required"]) == required
    assert set(schema["properties"]) == required
    assert schema["properties"]["gate_status"]["const"] == "closed"
    assert schema["properties"]["runtime_allowed"]["const"] is False
    assert schema["properties"]["implementation_allowed"]["const"] is False
    assert schema["properties"]["scaffold_phase"]["const"] == "SC-G2"


def test_checker_passes_on_current_closed_scaffold_contract() -> None:
    result = _run_checker()

    assert result.returncode == 0, result.stderr
    assert "exact/fuzzy scaffold contract closed" in result.stdout


@pytest.mark.parametrize(
    "claim",
    [
        "Semantic cache is active.",
        "Semantic cache is implemented.",
        "Semantic cache is enabled.",
        "Semantic cache is now open.",
        "Semantic cache is approved.",
        "Semantic cache is production-ready.",
        "Semantic cache serving is available.",
    ],
)
def test_checker_fails_if_scaffold_contract_implies_cache_is_live(
    tmp_path: Path,
    claim: str,
) -> None:
    contract = tmp_path / "scaffold.md"
    contract.write_text(_contract_text() + f"\n{claim}\n", encoding="utf-8")

    result = _run_checker(contract)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim" in result.stderr


@pytest.mark.parametrize(
    "claim",
    [
        "SC-G2 permits embeddings.",
        "SC-G2 supports embeddings.",
        "Embeddings are available for SC-G2.",
        "Embeddings are allowed in SC-G2.",
        "SC-G2 allows semantic similarity.",
        "SC-G2 can use semantic similarity.",
        "Semantic similarity is supported in SC-G2.",
        "SC-G2 enables vector search.",
        "SC-G2 can use vector search.",
        "Vector search is allowed in SC-G2.",
        "SC-G2 allows Redis.",
        "Redis is available for SC-G2.",
        "Redis is supported in SC-G2.",
        "SC-G2 permits GPTCache.",
        "GPTCache is approved for SC-G2.",
        "GPTCache is allowed in SC-G2.",
        "SC-G2 bypasses SC-G3.",
        "Advisory wiki can seed product cache.",
    ],
)
def test_checker_fails_if_scaffold_contract_permits_blocked_scope(
    tmp_path: Path,
    claim: str,
) -> None:
    contract = tmp_path / "scaffold.md"
    contract.write_text(_contract_text() + f"\n{claim}\n", encoding="utf-8")

    result = _run_checker(contract)

    assert result.returncode == 1
    assert (
        "forbidden exact/fuzzy scaffold claim" in result.stderr
        or "forbidden semantic-cache claim" in result.stderr
    )


def test_checker_fails_if_scaffold_phase_order_is_wrong(tmp_path: Path) -> None:
    contract = tmp_path / "scaffold.md"
    contract.write_text(
        _contract_text().replace(
            "SC-G3 observability and false-hit harness is still required before any\n"
            "semantic-cache serving. SC-G4 bounded `/insight` semantic-cache experiment",
            "SC-G4 bounded `/insight` semantic-cache experiment is future. "
            "SC-G3 observability and false-hit harness is still required before any "
            "semantic-cache serving",
        ),
        encoding="utf-8",
    )

    result = _run_checker(contract)

    assert result.returncode == 1
    assert "exact/fuzzy scaffold phase out of order" in result.stderr


def test_direct_validator_reports_missing_scaffold_anchor() -> None:
    errors = validate_exact_fuzzy_scaffold_contract(
        _contract_text().replace("admission linkage required;", "")
    )

    assert "exact/fuzzy scaffold contract missing anchor: admission linkage required" in errors


def test_direct_validator_reports_missing_sc_g3_once() -> None:
    errors = validate_exact_fuzzy_scaffold_contract(
        _contract_text().replace(
            "SC-G3 observability and false-hit harness is still required before any\n"
            "semantic-cache serving. ",
            "",
        )
    )

    assert errors.count("exact/fuzzy scaffold contract missing phase: SC-G3") == 1
    assert "exact/fuzzy scaffold contract omits SC-G3" not in errors


def test_docs_phase1_integration_passes_for_scaffold_contract() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(DOCS_PHASE1),
            "--files",
            "docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md",
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert "phase1-docs-gates: passed" in result.stdout


def test_checker_and_scaffold_have_no_forbidden_imports_or_nondeterministic_calls() -> None:
    for path in (CHECKER, DOCS_PHASE1, SCAFFOLD_MODULE):
        assert_no_forbidden_semantic_cache_imports(path)
        assert_no_forbidden_semantic_cache_calls(path)


def test_core_ai_facade_does_not_eagerly_export_scaffold() -> None:
    content = CORE_AI_INIT.read_text(encoding="utf-8")

    assert "exact_fuzzy_cache" not in content
    assert "ExactFuzzy" not in content
