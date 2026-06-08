#!/usr/bin/env python3
"""PR risk-profile classifier for Tier 1 CI routing.

RU: Определяет, какие backend/shared CI-ветки должны запускаться для PR.
EN: Classifies changed files into deterministic CI routing outputs for PRs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import fnmatch
import json
from pathlib import Path
import subprocess  # nosec B404: subprocess is required for bounded local git diff execution (remove-by: 2026-09-30, ref: PR3-risk-topology)
import sys
import shutil

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_BINARY = shutil.which("git")
ALL_RISK_GROUPS: tuple[str, ...] = (
    "billing_entitlement",
    "insight_ai",
    "openapi_contract",
    "food_catalog",
    "route_contract_safety",
    "operator_plane_slack",
    "merge_governance",
)

# Root-level backend modules that influence shared runtime or security posture
# must route through backend-blocking CI even when they do not live under app/core.
ROOT_BACKEND_SHARED_MODULES: tuple[str, ...] = (
    "llm.py",
    "main.py",
    "secure_config.py",
    "settings.py",
    "signed_links.py",
)

BACKEND_SHARED_EXACT: tuple[str, ...] = (
    "Dockerfile",
    "Makefile",
    "constraints.txt",
    "legacy_app.py",
    *ROOT_BACKEND_SHARED_MODULES,
    "mcp_pulseplate_server.py",
    "pyproject.toml",
    "pytest.ini",
    "requirements-ci-lite.in",
    "requirements-ci-lite.txt",
    "requirements-docker-runtime.in",
    "requirements-docker-runtime.txt",
    "requirements-dev.txt",
    "requirements-rag-vector.in",
    "requirements-rag-vector.txt",
    "requirements-rag-vector-cpu.in",
    "requirements-rag-vector-cpu.txt",
    "requirements.txt",
)
# Provider implementations can change auth, network, or model routing behavior,
# so provider-path changes always go through backend-blocking and security CI.
BACKEND_SHARED_PREFIXES: tuple[str, ...] = (
    "app/",
    "core/",
    "providers/",
    "scripts/ci/",
    "scripts/orchestration/",
    "tests/",
)
DOCS_PREFIXES: tuple[str, ...] = ("docs/",)
FRONTEND_EXACT: tuple[str, ...] = ("package.json", "package-lock.json", ".nvmrc")
FRONTEND_PREFIXES: tuple[str, ...] = ("frontend/",)
IOS_PREFIXES: tuple[str, ...] = ("ios/", "fastlane/")
WORKFLOW_PRIVILEGED_EXACT: tuple[str, ...] = (
    ".github/pull_request_template.md",
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
    "scripts/orchestration/check_agent_consistency.py",
    "scripts/orchestration/check_merge_ready.py",
    "scripts/orchestration/check_review_threads_disposition.py",
)
WORKFLOW_PRIVILEGED_PREFIXES: tuple[str, ...] = (
    ".github/actions/",
    ".github/scripts/",
    ".github/workflows/",
    "docs/orchestration/",
    "scripts/ci/",
)
MAIN_CI_DIAGNOSTIC_EXACT: tuple[str, ...] = (
    ".github/workflows/ci.yml",
    "scripts/ci/ci_risk_profile.py",
    "scripts/ci/run_main_test_shards.py",
    "scripts/ci/run_py312_main_shards.py",
    "tests/test_ci_risk_profile.py",
    "tests/test_ci_workflow_pr_size_governance_contract.py",
    "tests/test_main_test_shards.py",
)
GIT_DIFF_TIMEOUT_SECONDS = 60
RISK_GROUP_PATTERNS: dict[str, tuple[str, ...]] = {
    "billing_entitlement": (
        "app/middleware/api_tiers.py",
        "app/routers/billing.py",
        "app/routers/pro_*.py",
        "app/services/payments_*.py",
        "core/billing*.py",
        "tests/test_api_tiers_db_lookup.py",
        "tests/test_billing_openapi_contract.py",
        "tests/test_ios_receipt_verification_api.py",
        "tests/test_paid_route_guards.py",
        "tests/test_payment_reconciliation_api.py",
        "tests/test_payment_source_contract_api.py",
        "tests/test_payment_webhook_signature_api.py",
        "tests/test_pro_payments_openapi_contract.py",
        "tests/test_subscription_activation_api.py",
    ),
    "insight_ai": (
        "app/routers/*insight*.py",
        "app/routers/fitchef_structured.py",
        "app/security/agent_input_guard.py",
        "app/security/rate_limit.py",
        "app/services/fitchef_runtime.py",
        "app/schemas/fitchef*.py",
        "core/insight/*.py",
        "core/rag/*.py",
        "legacy_app.py",
        "mcp_pulseplate_server.py",
        "tests/test_core_ai_insight_runtime.py",
        "tests/test_fitchef_insight_api.py",
        "tests/test_fitchef_companion_helpers.py",
        "tests/test_fitchef_structured_api.py",
        "tests/test_fitchef_structured_contracts.py",
        "tests/test_insight_error_hygiene.py",
        "tests/test_insight_vip_guard_api.py",
        "tests/test_insight_vip_monthly_quota_api.py",
        "tests/test_rag_orchestration.py",
        "tests/test_vector_rag.py",
        "tests/test_philosophy_validation_integration.py",
        "tests/test_rate_limit_llm_and_exports_api.py",
    ),
    "openapi_contract": (
        "app/main.py",
        "app/routers/*.py",
        "app/schemas/*.py",
        "frontend/src/api/*",
        "legacy_app.py",
        "scripts/generate_openapi.py",
        "tests/test_openapi_*.py",
    ),
    "food_catalog": (
        "app/schemas/food.py",
        "app/services/food_store.py",
        "core/food_apis/*.py",
        "core/food_merge.py",
        "core/food_provenance_verification.py",
        "core/off_nutrition/*.py",
        "scripts/build_food_db.py",
    ),
    "merge_governance": (
        ".github/actions/*",
        ".github/scripts/*",
        ".github/workflows/*",
        ".github/pull_request_template.md",
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "docs/orchestration/*",
        "scripts/ci/*",
        "scripts/orchestration/check_agent_consistency.py",
        "scripts/orchestration/check_merge_ready.py",
        "scripts/orchestration/check_review_threads_disposition.py",
        "tests/test_check_pr_size_governance.py",
        "tests/test_ci_risk_profile.py",
        "tests/test_orchestration_merge_ready.py",
        "tests/test_pr_body_phase2_gates.py",
        "tests/test_pr_merge_readiness_gate.py",
        "tests/test_review_threads_disposition_strict.py",
    ),
    "operator_plane_slack": (
        ".github/workflows/experiment-runner-*.yml",
        ".github/workflows/experiment-runner-*.yaml",
        "docs/orchestration/EXPERIMENT_RUNNER_SLACK_*",
        "docs/roadmap/BACKLOG_LEDGER.md",
        "scripts/orchestration/experiment_operator_ledger.py",
        "scripts/orchestration/experiment_slack*.py",
        "tests/test_experiment_operator_ledger.py",
        "tests/test_experiment_slack_kpp_renderer.py",
        "tests/test_experiment_slack_socket_bridge.py",
        "tests/test_runtime_toolchain_alignment.py",
    ),
}


@dataclass(frozen=True)
class RiskProfile:
    """Deterministic routing profile for backend/shared PR CI."""

    changed_files: tuple[str, ...]
    docs_only: bool
    frontend_only: bool
    ios_only: bool
    workflow_privileged: bool
    backend_shared: bool
    run_backend_blocking: bool
    run_main_ci_diagnostic: bool
    run_security: bool
    run_openapi_sync: bool
    billing_entitlement: bool
    insight_ai: bool
    openapi_contract: bool
    food_catalog: bool
    route_contract_safety: bool
    operator_plane_slack: bool
    merge_governance: bool
    contract_risk_groups: tuple[str, ...]

    def to_outputs(self) -> dict[str, str]:
        """Return GitHub Actions-friendly outputs."""
        outputs = {
            "docs_only": _bool_text(self.docs_only),
            "frontend_only": _bool_text(self.frontend_only),
            "ios_only": _bool_text(self.ios_only),
            "workflow_privileged": _bool_text(self.workflow_privileged),
            "backend_shared": _bool_text(self.backend_shared),
            "run_backend_blocking": _bool_text(self.run_backend_blocking),
            "run_main_ci_diagnostic": _bool_text(self.run_main_ci_diagnostic),
            "run_security": _bool_text(self.run_security),
            "run_openapi_sync": _bool_text(self.run_openapi_sync),
            "billing_entitlement": _bool_text(self.billing_entitlement),
            "insight_ai": _bool_text(self.insight_ai),
            "openapi_contract": _bool_text(self.openapi_contract),
            "food_catalog": _bool_text(self.food_catalog),
            "route_contract_safety": _bool_text(self.route_contract_safety),
            "operator_plane_slack": _bool_text(self.operator_plane_slack),
            "merge_governance": _bool_text(self.merge_governance),
            "contract_risk_groups": ",".join(self.contract_risk_groups),
            "changed_file_count": str(len(self.changed_files)),
        }
        return outputs


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _normalize_path(path: str) -> str:
    return path.strip().replace("\\", "/").removeprefix("./")


def _read_flag_value(argv: list[str], index: int, flag: str) -> str:
    """Return the next argv token for a flag or exit with a deterministic error."""
    value_index = index + 1
    if value_index >= len(argv):
        raise SystemExit(f"Missing value for {flag}.")
    value = argv[value_index]
    if value.startswith("--"):
        raise SystemExit(f"Missing value for {flag}.")
    return value


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _is_workflow_privileged(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in WORKFLOW_PRIVILEGED_EXACT or normalized.startswith(
        WORKFLOW_PRIVILEGED_PREFIXES,
    )


def _is_backend_shared(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in BACKEND_SHARED_EXACT or normalized.startswith(
        BACKEND_SHARED_PREFIXES,
    )


def _is_main_ci_diagnostic_surface(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in MAIN_CI_DIAGNOSTIC_EXACT


def _is_docs_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized.startswith(DOCS_PREFIXES) or normalized.endswith(".md")


def _is_frontend_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in FRONTEND_EXACT or normalized.startswith(FRONTEND_PREFIXES)


def _is_ios_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized.startswith(IOS_PREFIXES)


def _risk_group_hit(group_name: str, changed_files: tuple[str, ...]) -> bool:
    patterns = RISK_GROUP_PATTERNS[group_name]
    return any(_matches_any(path, patterns) for path in changed_files)


def _is_route_contract_surface(path: str) -> bool:
    normalized = _normalize_path(path)
    return (
        normalized == "legacy_app.py"
        # Shared root/provider backend modules participate in both CI-risk
        # classifications: they are backend-shared surfaces and route-contract
        # inputs that can change the routing/contract safety envelope.
        or normalized in ROOT_BACKEND_SHARED_MODULES
        or normalized.startswith(("app/", "core/", "providers/"))
    )


def build_risk_profile(changed_files: list[str] | tuple[str, ...]) -> RiskProfile:
    """Build a deterministic risk profile from normalized changed paths."""
    normalized_files = tuple(
        path for path in (_normalize_path(item) for item in changed_files) if path
    )
    if not normalized_files:
        return RiskProfile(
            changed_files=(),
            docs_only=False,
            frontend_only=False,
            ios_only=False,
            workflow_privileged=False,
            backend_shared=False,
            run_backend_blocking=False,
            run_main_ci_diagnostic=False,
            run_security=False,
            run_openapi_sync=False,
            billing_entitlement=False,
            insight_ai=False,
            openapi_contract=False,
            food_catalog=False,
            route_contract_safety=False,
            operator_plane_slack=False,
            merge_governance=False,
            contract_risk_groups=(),
        )

    workflow_privileged = any(_is_workflow_privileged(path) for path in normalized_files)
    backend_shared = any(_is_backend_shared(path) for path in normalized_files)
    docs_only = all(_is_docs_path(path) for path in normalized_files) and not workflow_privileged
    frontend_only = (
        all(_is_frontend_path(path) for path in normalized_files) and not workflow_privileged
    )
    ios_only = all(_is_ios_path(path) for path in normalized_files) and not workflow_privileged

    group_hits = {
        group_name: _risk_group_hit(group_name, normalized_files)
        for group_name in ALL_RISK_GROUPS
        if group_name != "route_contract_safety"
    }
    group_hits["route_contract_safety"] = any(
        _is_route_contract_surface(path) for path in normalized_files
    )
    if workflow_privileged:
        selected_groups = ALL_RISK_GROUPS
    else:
        selected_groups = tuple(
            group_name for group_name in ALL_RISK_GROUPS if group_hits[group_name]
        )

    run_backend_blocking = (
        workflow_privileged
        or backend_shared
        or group_hits["openapi_contract"]
        or group_hits["food_catalog"]
        or group_hits["operator_plane_slack"]
    )
    run_main_ci_diagnostic = any(_is_main_ci_diagnostic_surface(path) for path in normalized_files)
    run_security = run_backend_blocking
    run_openapi_sync = run_backend_blocking

    return RiskProfile(
        changed_files=normalized_files,
        docs_only=docs_only,
        frontend_only=frontend_only,
        ios_only=ios_only,
        workflow_privileged=workflow_privileged,
        backend_shared=backend_shared,
        run_backend_blocking=run_backend_blocking,
        run_main_ci_diagnostic=run_main_ci_diagnostic,
        run_security=run_security,
        run_openapi_sync=run_openapi_sync,
        billing_entitlement=group_hits["billing_entitlement"],
        insight_ai=group_hits["insight_ai"],
        openapi_contract=group_hits["openapi_contract"],
        food_catalog=group_hits["food_catalog"],
        route_contract_safety=group_hits["route_contract_safety"],
        operator_plane_slack=group_hits["operator_plane_slack"],
        merge_governance=group_hits["merge_governance"],
        contract_risk_groups=selected_groups,
    )


def collect_changed_files(*, base_sha: str, head_sha: str) -> tuple[str, ...]:
    """Return changed files between two git revisions."""
    if GIT_BINARY is None:
        raise RuntimeError("git executable not found in PATH")
    try:
        result = subprocess.run(  # nosec B603: fixed git argv without shell for local CI routing only (remove-by: 2026-09-30, ref: PR3-risk-topology)
            [
                GIT_BINARY,
                "diff",
                "--name-only",
                f"{base_sha}...{head_sha}",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=GIT_DIFF_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"git diff --name-only timed out after {GIT_DIFF_TIMEOUT_SECONDS} seconds"
        ) from exc
    return tuple(path for path in result.stdout.splitlines() if path.strip())


def _write_github_outputs(path: Path, outputs: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    argv = list(sys.argv[1:] if argv is None else argv)
    base_sha = ""
    head_sha = ""
    explicit_files: list[str] = []
    github_output_path: Path | None = None
    json_mode = False

    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--base-sha":
            index += 1
            base_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--head-sha":
            index += 1
            head_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--file":
            index += 1
            explicit_files.append(_read_flag_value(argv, index - 1, argument))
        elif argument == "--github-output":
            index += 1
            github_output_path = Path(_read_flag_value(argv, index - 1, argument))
        elif argument == "--as-json":
            json_mode = True
        else:
            raise SystemExit(f"Unknown argument: {argument}")
        index += 1

    if explicit_files:
        changed_files = tuple(explicit_files)
    else:
        if not base_sha or not head_sha:
            raise SystemExit(
                "Provide either repeated --file values or both --base-sha and --head-sha."
            )
        changed_files = collect_changed_files(base_sha=base_sha, head_sha=head_sha)

    profile = build_risk_profile(list(changed_files))
    outputs = profile.to_outputs()

    if github_output_path is not None:
        _write_github_outputs(github_output_path, outputs)

    if json_mode:
        print(json.dumps(asdict(profile), sort_keys=True))
    else:
        for key, value in outputs.items():
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
