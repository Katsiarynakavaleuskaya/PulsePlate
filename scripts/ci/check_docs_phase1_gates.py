from __future__ import annotations

import argparse
from collections.abc import Callable
import importlib.util
import re
from pathlib import Path
from typing import cast

PR_TBD_RE = re.compile(r"(?im)^\s*(?:[-*+]\s+)?(?:\*\*PR:\*\*|PR:)\s*TBD\b")
EVIDENCE_ANCHOR_RE = re.compile(
    r"(?:^|(?<=\s)|(?<=`)|(?<=\())"
    r"(?:"
    r"(?:\.github|docs|tests|app|core|scripts|frontend|ios|providers|deploy|alembic)"
    r"/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+"
    r"|(?:AGENTS\.md|RUNBOOK_AGENT\.md|README\.md)"
    r"):\d+\b"
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = Path(__file__).resolve().with_name("check_semantic_cache_gate.py")
SEMANTIC_CACHE_GATE_DOC = "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
SEMANTIC_CACHE_ROLLOUT_CONTRACT_DOC = "docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md"
EXACT_FUZZY_CACHE_SCAFFOLD_DOC = "docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md"
SEMANTIC_CACHE_OBSERVABILITY_CONTRACT_DOC = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md"
)
SEMANTIC_CACHE_BOUNDED_INSIGHT_CONTRACT_DOC = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md"
)
SemanticCacheGateValidator = Callable[[str], list[str]]


def _load_validator(symbol: str) -> SemanticCacheGateValidator:
    spec = importlib.util.spec_from_file_location("check_semantic_cache_gate", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load semantic-cache gate checker: {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, symbol, None)
    if not callable(validator):
        raise RuntimeError(f"semantic-cache gate checker missing {symbol}")
    return cast(SemanticCacheGateValidator, validator)


def _load_semantic_cache_gate_validator() -> SemanticCacheGateValidator:
    return _load_validator("validate_semantic_cache_gate")


def _load_semantic_cache_rollout_contract_validator() -> SemanticCacheGateValidator:
    return _load_validator("validate_semantic_cache_rollout_contract")


def _load_exact_fuzzy_scaffold_validator() -> SemanticCacheGateValidator:
    return _load_validator("validate_exact_fuzzy_scaffold_contract")


def _load_semantic_cache_observability_validator() -> SemanticCacheGateValidator:
    return _load_validator("validate_semantic_cache_observability_contract")


def _load_semantic_cache_bounded_insight_validator() -> SemanticCacheGateValidator:
    return _load_validator("validate_semantic_cache_bounded_insight_experiment_contract")


def _read_text(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _is_audit_path(relpath: str) -> bool:
    return relpath.startswith("docs/audit/") and relpath.endswith(".md")


def _is_security_or_audit_path(relpath: str) -> bool:
    return (
        relpath.startswith("docs/audit/") or relpath.startswith("docs/security/")
    ) and relpath.endswith(".md")


def check_docs_phase1_guards(markdown_files: list[str]) -> list[str]:
    errors: list[str] = []
    for relpath in markdown_files:
        fullpath = REPO_ROOT / relpath
        if not fullpath.exists():
            continue
        content = _read_text(relpath)

        if _is_audit_path(relpath) and PR_TBD_RE.search(content):
            errors.append(
                f"{relpath}: contains unresolved placeholder `PR: TBD` "
                "(replace with final PR number or commit SHA)."
            )

        if _is_security_or_audit_path(relpath) and not EVIDENCE_ANCHOR_RE.search(content):
            errors.append(
                f"{relpath}: missing `file:line` evidence anchor "
                "(example: `tests/test_repo_policy_guards.py:264`)."
            )

        if relpath == SEMANTIC_CACHE_GATE_DOC:
            validate_semantic_cache_gate = _load_semantic_cache_gate_validator()
            errors.extend(f"{relpath}: {error}" for error in validate_semantic_cache_gate(content))

        if relpath == SEMANTIC_CACHE_ROLLOUT_CONTRACT_DOC:
            validate_rollout_contract = _load_semantic_cache_rollout_contract_validator()
            errors.extend(f"{relpath}: {error}" for error in validate_rollout_contract(content))

        if relpath == EXACT_FUZZY_CACHE_SCAFFOLD_DOC:
            validate_scaffold_contract = _load_exact_fuzzy_scaffold_validator()
            errors.extend(f"{relpath}: {error}" for error in validate_scaffold_contract(content))

        if relpath == SEMANTIC_CACHE_OBSERVABILITY_CONTRACT_DOC:
            validate_observability_contract = _load_semantic_cache_observability_validator()
            errors.extend(
                f"{relpath}: {error}" for error in validate_observability_contract(content)
            )

        if relpath == SEMANTIC_CACHE_BOUNDED_INSIGHT_CONTRACT_DOC:
            validate_bounded_insight_contract = _load_semantic_cache_bounded_insight_validator()
            errors.extend(
                f"{relpath}: {error}" for error in validate_bounded_insight_contract(content)
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 1 docs quality gates.")
    parser.add_argument(
        "--files",
        nargs="*",
        default=[],
        help="Explicit markdown files to check (relative paths).",
    )
    args = parser.parse_args()

    markdown_files = [path for path in args.files if path]
    if not markdown_files:
        print("phase1-docs-gates: no markdown files provided; skipping.")
        return 0

    errors = check_docs_phase1_guards(markdown_files=markdown_files)
    if errors:
        print("ERROR: phase1 docs gates failed:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("phase1-docs-gates: passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
