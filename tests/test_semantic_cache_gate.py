from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPO_ROOT / "scripts" / "ci" / "check_semantic_cache_gate.py"


def _valid_doc() -> str:
    return """# PulsePlate Semantic Cache Gate and Plan

<!-- SEMANTIC_CACHE_GATE_STATUS: closed -->
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
"""


def _run_checker(doc: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(CHECKER)]
    if doc is not None:
        args.extend(["--doc", str(doc)])
    return subprocess.run(args, check=False, text=True, capture_output=True)


def _write_doc(tmp_path: Path, text: str) -> Path:
    doc = tmp_path / "semantic_cache_gate.md"
    doc.write_text(text, encoding="utf-8")
    return doc


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
    assert "forbidden semantic-cache claim: semantic cache is implemented" in result.stderr


@pytest.mark.parametrize("claim", ["Semantic cache is active.", "Semantic cache is enabled."])
def test_checker_fails_if_doc_says_semantic_cache_is_active_or_enabled(
    tmp_path: Path, claim: str
) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + f"\n{claim}\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim" in result.stderr


def test_checker_fails_if_e1_e5_automatically_unlock_semantic_cache(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + "\nE1-E5 unlock semantic cache.\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim: e1-e5 unlock semantic cache" in result.stderr


def test_checker_fails_if_advisory_wiki_is_product_cache_source(tmp_path: Path) -> None:
    doc = _write_doc(tmp_path, _valid_doc() + "\nAdvisory wiki feeds product cache.\n")

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "forbidden semantic-cache claim: advisory wiki feeds product cache" in result.stderr


def test_checker_fails_if_rollout_order_is_missing(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc().replace("3. bounded semantic cache for `/insight`\n", ""),
    )

    result = _run_checker(doc)

    assert result.returncode == 1
    assert "missing rollout order item: bounded semantic cache for `/insight`" in result.stderr


def test_checker_accepts_rollout_order_case_variation(tmp_path: Path) -> None:
    doc = _write_doc(
        tmp_path,
        _valid_doc()
        .replace("observability / false-hit guardrails", "Observability / false-hit guardrails")
        .replace("Redis/GPTCache backend only later", "redis/gptcache backend only later"),
    )

    result = _run_checker(doc)

    assert result.returncode == 0, result.stderr


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
