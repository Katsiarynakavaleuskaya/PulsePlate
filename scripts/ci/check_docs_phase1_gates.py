from __future__ import annotations

import argparse
from collections.abc import Callable
import re
from pathlib import Path
from typing import Any, Protocol, cast

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

try:
    from scripts.ci.check_semantic_cache_gate import (
        validate_exact_fuzzy_scaffold_contract as _validate_exact_fuzzy_scaffold_contract,
        validate_philosophy_semantic_cache_admission_contract as _validate_philosophy_admission_contract,
        validate_philosophy_semantic_cache_admission_downstream_text as _validate_philosophy_admission_downstream_text,
        validate_philosophy_semantic_cache_admission_policy as _validate_philosophy_admission_policy,
        validate_philosophy_admission_oracle_fixture as _validate_philosophy_admission_oracle_fixture,
        validate_philosophy_semantic_cache_admission_schema as _validate_philosophy_admission_schema,
        validate_semantic_cache_backend_selection_contract as _validate_backend_selection_contract,
        validate_semantic_cache_backend_selection_schema as _validate_backend_selection_schema,
        validate_semantic_cache_bounded_insight_experiment_contract as _validate_bounded_insight_contract,
        validate_semantic_cache_gate as _validate_semantic_cache_gate,
        validate_semantic_cache_observability_contract as _validate_observability_contract,
        validate_semantic_cache_rollout_contract as _validate_rollout_contract,
    )
except ModuleNotFoundError:
    from check_semantic_cache_gate import (  # noqa: E402
        validate_exact_fuzzy_scaffold_contract as _validate_exact_fuzzy_scaffold_contract,
        validate_philosophy_semantic_cache_admission_contract as _validate_philosophy_admission_contract,
        validate_philosophy_semantic_cache_admission_downstream_text as _validate_philosophy_admission_downstream_text,
        validate_philosophy_semantic_cache_admission_policy as _validate_philosophy_admission_policy,
        validate_philosophy_admission_oracle_fixture as _validate_philosophy_admission_oracle_fixture,
        validate_philosophy_semantic_cache_admission_schema as _validate_philosophy_admission_schema,
        validate_semantic_cache_backend_selection_contract as _validate_backend_selection_contract,
        validate_semantic_cache_backend_selection_schema as _validate_backend_selection_schema,
        validate_semantic_cache_bounded_insight_experiment_contract as _validate_bounded_insight_contract,
        validate_semantic_cache_gate as _validate_semantic_cache_gate,
        validate_semantic_cache_observability_contract as _validate_observability_contract,
        validate_semantic_cache_rollout_contract as _validate_rollout_contract,
    )

SEMANTIC_CACHE_GATE_DOC = "docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md"
SEMANTIC_CACHE_ROLLOUT_CONTRACT_DOC = "docs/orchestration/contracts/SEMANTIC_CACHE_ROLLOUT_GATE.md"
EXACT_FUZZY_CACHE_SCAFFOLD_DOC = "docs/orchestration/contracts/EXACT_FUZZY_CACHE_SCAFFOLD.md"
SEMANTIC_CACHE_OBSERVABILITY_CONTRACT_DOC = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_OBSERVABILITY_FALSE_HIT_HARNESS.md"
)
SEMANTIC_CACHE_BOUNDED_INSIGHT_CONTRACT_DOC = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_BOUNDED_INSIGHT_EXPERIMENT.md"
)
SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_DOC = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md"
)
SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_SCHEMA = (
    "docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.schema.json"
)
PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_DOC = (
    "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md"
)
PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_SCHEMA = (
    "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.schema.json"
)
PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY = (
    "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.json"
)
PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA = (
    "docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY.schema.json"
)
PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE = (
    "tests/fixtures/orchestration/philosophy_admission_claim_oracle.json"
)
PHILOSOPHY_DOWNSTREAM_DOC_PREFIXES: tuple[str, ...] = (
    "docs/orchestration/PHILOSOPHY_",
    "docs/orchestration/contracts/PHILOSOPHY_",
    "docs/orchestration/contracts/LOGIC_PHILOSOPHY_",
)
PHILOSOPHY_DOWNSTREAM_DOC_NAME_SCOPES: tuple[tuple[str, str], ...] = (
    ("docs/insights/", "PHILOSOPH"),
    ("docs/orchestration/", "PHILOSOPH"),
)
PHILOSOPHY_DOWNSTREAM_DOCS: frozenset[str] = frozenset(
    {
        "docs/roadmap/BACKLOG_LEDGER.md",
        SEMANTIC_CACHE_GATE_DOC,
        SEMANTIC_CACHE_ROLLOUT_CONTRACT_DOC,
        EXACT_FUZZY_CACHE_SCAFFOLD_DOC,
        SEMANTIC_CACHE_OBSERVABILITY_CONTRACT_DOC,
        SEMANTIC_CACHE_BOUNDED_INSIGHT_CONTRACT_DOC,
        SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_DOC,
    }
)
SemanticCacheGateValidator = Callable[[str], list[str]]


class ContractSchemaValidator(Protocol):
    def __call__(self, *, schema_text: str, contract_text: str) -> list[str]: ...


class PolicySchemaValidator(Protocol):
    def __call__(self, *, policy_text: str, schema_text: str) -> list[str]: ...


def _as_semantic_cache_gate_validator(validator: Any) -> SemanticCacheGateValidator:
    return cast(SemanticCacheGateValidator, validator)


def _as_contract_schema_validator(
    validator: Any,
) -> ContractSchemaValidator:
    return cast(ContractSchemaValidator, validator)


def _load_semantic_cache_gate_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_semantic_cache_gate)


def _load_semantic_cache_rollout_contract_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_rollout_contract)


def _load_exact_fuzzy_scaffold_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_exact_fuzzy_scaffold_contract)


def _load_semantic_cache_observability_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_observability_contract)


def _load_semantic_cache_bounded_insight_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_bounded_insight_contract)


def _load_semantic_cache_backend_selection_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_backend_selection_contract)


def _load_semantic_cache_backend_selection_schema_validator() -> ContractSchemaValidator:
    return _as_contract_schema_validator(
        _validate_backend_selection_schema,
    )


def _load_philosophy_admission_contract_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_philosophy_admission_contract)


def _load_philosophy_admission_downstream_validator() -> SemanticCacheGateValidator:
    return _as_semantic_cache_gate_validator(_validate_philosophy_admission_downstream_text)


def _load_philosophy_admission_schema_validator() -> ContractSchemaValidator:
    return _as_contract_schema_validator(
        _validate_philosophy_admission_schema,
    )


def _load_philosophy_admission_policy_validator() -> PolicySchemaValidator:
    return cast(PolicySchemaValidator, _validate_philosophy_admission_policy)


class OracleFixtureValidator(Protocol):
    def __call__(self, *, policy_text: str, fixture_text: str) -> list[str]: ...


def _load_philosophy_admission_oracle_fixture_validator() -> OracleFixtureValidator:
    return cast(OracleFixtureValidator, _validate_philosophy_admission_oracle_fixture)


def _read_text(relpath: str) -> str:
    return (REPO_ROOT / relpath).read_text(encoding="utf-8", errors="replace")


def _is_audit_path(relpath: str) -> bool:
    return relpath.startswith("docs/audit/") and relpath.endswith(".md")


def _is_security_or_audit_path(relpath: str) -> bool:
    return (
        relpath.startswith("docs/audit/") or relpath.startswith("docs/security/")
    ) and relpath.endswith(".md")


def _is_philosophy_downstream_doc_path(relpath: str) -> bool:
    basename = Path(relpath).name
    return (
        relpath.endswith(".md")
        and (
            relpath in PHILOSOPHY_DOWNSTREAM_DOCS
            or relpath.startswith(PHILOSOPHY_DOWNSTREAM_DOC_PREFIXES)
            or any(
                relpath.startswith(scope_root) and token in basename
                for scope_root, token in PHILOSOPHY_DOWNSTREAM_DOC_NAME_SCOPES
            )
        )
        and relpath != PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_DOC
        and not relpath.startswith("docs/review/")
    )


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

        if _is_philosophy_downstream_doc_path(relpath):
            validate_philosophy_admission_downstream = (
                _load_philosophy_admission_downstream_validator()
            )
            errors.extend(
                f"{relpath}: {error}" for error in validate_philosophy_admission_downstream(content)
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

        if relpath == SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_DOC:
            validate_backend_selection_contract = _load_semantic_cache_backend_selection_validator()
            errors.extend(
                f"{relpath}: {error}" for error in validate_backend_selection_contract(content)
            )
            validate_backend_selection_schema = (
                _load_semantic_cache_backend_selection_schema_validator()
            )
            try:
                schema_text = _read_text(SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_SCHEMA)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_SCHEMA}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_backend_selection_schema(
                        schema_text=schema_text,
                        contract_text=content,
                    )
                )

        if relpath == SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_SCHEMA:
            validate_backend_selection_schema = (
                _load_semantic_cache_backend_selection_schema_validator()
            )
            try:
                contract_text = _read_text(SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_DOC)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT_DOC}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_backend_selection_schema(
                        schema_text=content,
                        contract_text=contract_text,
                    )
                )

        if relpath == PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_DOC:
            validate_philosophy_admission_contract = _load_philosophy_admission_contract_validator()
            errors.extend(
                f"{relpath}: {error}" for error in validate_philosophy_admission_contract(content)
            )
            validate_philosophy_admission_schema = _load_philosophy_admission_schema_validator()
            try:
                schema_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_SCHEMA)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_SCHEMA}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_philosophy_admission_schema(
                        schema_text=schema_text,
                        contract_text=content,
                    )
                )

        if relpath == PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_SCHEMA:
            validate_philosophy_admission_schema = _load_philosophy_admission_schema_validator()
            try:
                contract_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_DOC)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT_DOC}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_philosophy_admission_schema(
                        schema_text=content,
                        contract_text=contract_text,
                    )
                )

        if relpath == PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY:
            validate_philosophy_admission_policy = _load_philosophy_admission_policy_validator()
            try:
                schema_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_philosophy_admission_policy(
                        schema_text=schema_text,
                        policy_text=content,
                    )
                )
            validate_oracle_fixture = _load_philosophy_admission_oracle_fixture_validator()
            try:
                fixture_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_oracle_fixture(
                        policy_text=content,
                        fixture_text=fixture_text,
                    )
                )

        if relpath == PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY_SCHEMA:
            validate_philosophy_admission_policy = _load_philosophy_admission_policy_validator()
            try:
                policy_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_philosophy_admission_policy(
                        schema_text=content,
                        policy_text=policy_text,
                    )
                )

        if relpath == PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_ORACLE:
            validate_oracle_fixture = _load_philosophy_admission_oracle_fixture_validator()
            try:
                policy_text = _read_text(PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY)
            except FileNotFoundError:
                errors.append(
                    f"{relpath}: missing companion file "
                    f"{PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_POLICY}"
                )
            else:
                errors.extend(
                    f"{relpath}: {error}"
                    for error in validate_oracle_fixture(
                        policy_text=policy_text,
                        fixture_text=content,
                    )
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
