from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_gate.py"
CONTRACT = REPO_ROOT / "docs" / "orchestration" / "contracts" / "SEMANTIC_CACHE_ROLLOUT_GATE.md"


def _valid_doc() -> str:
    return """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->
<!-- SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false -->
<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->

Semantic cache remains gate-closed until a reviewed gate-open PR changes these
markers and documents current-head CI governance.

Semantic cache belongs only to the product AI runtime rail.

Semantic cache is not advisory wiki, not workforce memory, not a second source of truth, not billing/auth/entitlement truth, not a compliance/legal output cache, and not user-account truth surfaces.

If the gate opens later, rollout order is fixed:
1. SC-G1 rollout gate contract
2. SC-G2 exact/fuzzy cache scaffold
3. SC-G3 observability and false-hit harness
4. SC-G4 bounded `/insight` semantic-cache experiment
5. SC-G5 backend selection
"""


def _run_checker(
    doc: Path | None = None, contract: Path | None = None
) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER)]
    if doc is not None:
        args.extend(["--doc", str(doc)])
    if contract is not None:
        args.extend(["--contract", str(contract)])
    return subprocess.run(args, check=False, text=True, capture_output=True)


def _write_doc(tmp_path: Path, text: str) -> Path:
    doc = tmp_path / "semantic_cache_gate.md"
    doc.write_text(text, encoding="utf-8")
    return doc


def _write_contract(tmp_path: Path, text: str) -> Path:
    contract = tmp_path / "semantic_cache_rollout_contract.md"
    contract.write_text(text, encoding="utf-8")
    return contract


def test_checker_passes_on_current_gate_closed_document() -> None:
    result = _run_checker()

    assert result.returncode == 0, result.stderr
    assert "semantic-cache gate closed" in result.stdout


def test_checker_fails_if_gate_status_marker_missing(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace("<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->\n", ""),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "missing marker: SEMANTIC_CACHE_GATE_STATUS" in result.stderr


def test_checker_fails_if_marker_is_duplicated(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace(
            "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
            "<!-- SEMANTIC_CACHE_GATE_STATUS: open -->\n"
            "<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->",
        ),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "duplicate marker: SEMANTIC_CACHE_GATE_STATUS" in result.stderr


def test_checker_fails_if_implementation_allowed_marker_true(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace(
            "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: false",
            "SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED: true",
        ),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "invalid marker SEMANTIC_CACHE_IMPLEMENTATION_ALLOWED" in result.stderr


def test_checker_fails_if_runtime_allowed_marker_true(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace(
            "SEMANTIC_CACHE_ALLOWED_RUNTIME: false",
            "SEMANTIC_CACHE_ALLOWED_RUNTIME: true",
        ),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "invalid marker SEMANTIC_CACHE_ALLOWED_RUNTIME" in result.stderr


def test_checker_fails_if_runtime_allowed_marker_missing(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace("<!-- SEMANTIC_CACHE_ALLOWED_RUNTIME: false -->\n", ""),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "missing marker: SEMANTIC_CACHE_ALLOWED_RUNTIME" in result.stderr


def test_checker_reports_full_hyphenated_marker_value(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace(
            "SEMANTIC_CACHE_GATE_STATUS: closed",
            "SEMANTIC_CACHE_GATE_STATUS: fail-closed",
        ),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "invalid marker SEMANTIC_CACHE_GATE_STATUS" in result.stderr
    assert "got fail-closed" in result.stderr


@pytest.mark.parametrize(
    "replacement,expected",
    [
        ("", "missing marker: SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE"),
        (
            "<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: false -->\n",
            "invalid marker SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE",
        ),
    ],
)
def test_checker_fails_if_dedicated_gate_marker_missing_or_false(
    tmp_path: Path, replacement: str, expected: str
) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace(
            "<!-- SEMANTIC_CACHE_REQUIRES_DEDICATED_GATE: true -->\n",
            replacement,
        ),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert expected in result.stderr


def test_checker_fails_if_doc_says_semantic_cache_is_implemented(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + "\nSemantic cache is implemented.\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim: semantic cache implemented/active" in result.stderr


@pytest.mark.parametrize(
    "claim",
    [
        "Semantic cache is active.",
        "Semantic cache is enabled.",
        "Semantic-cache is enabled.",
        "Semantic cache has been enabled.",
    ],
)
def test_checker_fails_if_doc_says_semantic_cache_is_active_or_enabled(
    tmp_path: Path, claim: str
) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + f"\n{claim}\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim" in result.stderr


def test_checker_fails_if_e1_e5_automatically_unlock_semantic_cache(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + "\nE1–E5 unlock semantic cache.\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim: E1-E5 unlock semantic cache" in result.stderr


def test_checker_fails_if_e1_through_e5_satisfy_cache_prerequisites(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path, _valid_doc() + "\nE1 through E5 satisfy semantic cache prerequisites.\n"
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert (
        "forbidden semantic-cache claim: E1-E5 satisfy semantic cache prerequisites"
        in result.stderr
    )


def test_checker_fails_if_advisory_wiki_is_product_cache_source(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + "\nAdvisory wiki can seed product cache.\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim: advisory wiki feeds product cache" in result.stderr


def test_checker_fails_if_rollout_order_is_missing(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace("3. SC-G3 observability and false-hit harness\n", ""),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "missing rollout order item: SC-G3 observability and false-hit harness" in result.stderr


def test_checker_accepts_rollout_order_case_variation(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc()
        .replace(
            "SC-G3 observability and false-hit harness", "SC-G3 Observability and false-hit harness"
        )
        .replace("SC-G5 backend selection", "SC-G5 Backend Selection"),
    )

    result = _run_checker(doc)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "phrase",
    [
        "gate-closed",
        "reviewed gate-open PR",
        "product AI runtime rail",
        "not advisory wiki",
        "not workforce memory",
        "not a second source of truth",
        "not billing/auth/entitlement truth",
        "not a compliance/legal output cache",
        "not user-account truth surfaces",
    ],
)
def test_checker_fails_if_required_phrase_is_missing(tmp_path: Path, phrase: str) -> None:
    doc = _write_doc(tmp_path, _valid_doc().replace(phrase, ""))

    result = _run_checker(doc)

    assert result.returncode == 1
    assert f"missing required phrase: {phrase}" in result.stderr


def test_checker_fails_if_rollout_contract_contains_dangerous_claim(tmp_path: Path) -> None:
    contract = _write_contract(
        tmp_path,
        CONTRACT.read_text(encoding="utf-8") + "\nSemantic cache is now open.\n",
    )

    result = _run_checker(contract=contract)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim" in result.stderr


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
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    offenders = [
        name
        for name in imports
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]
    assert offenders == []

    dynamic_imports: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "__import__"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            dynamic_imports.append(node.args[0].value)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "import_module"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            dynamic_imports.append(node.args[0].value)

    dynamic_offenders = [
        name
        for name in dynamic_imports
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]
    assert dynamic_offenders == []
