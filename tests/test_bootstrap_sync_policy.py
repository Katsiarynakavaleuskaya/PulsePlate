"""Tests for canonical bootstrap sync-policy helpers."""

from __future__ import annotations

from scripts.orchestration.bootstrap_sync_policy import (
    AGENT_CONTRACT_PATH_MARKERS,
    AGENTS_CONTRACT_FILE,
    AGENTS_CURSOR_PREFIX,
    ANALYSIS_ENVELOPE_MODE,
    BACKLOG_SIGNAL_TERMS,
    DOCS_ONLY_ENVELOPE_MODE,
    DOCS_ONLY_ROOT_FILES,
    IMPLEMENTATION_PATH_PREFIXES,
    PRIVILEGED_REVIEW_PATTERNS,
    PRIVILEGED_REVIEW_PREFIXES,
    SKILL_CONTRACT_FILE,
    is_docs_only_contract_path,
    matches_any_prefix,
    needs_agents_sync,
    needs_backlog_update,
    needs_docs_sync,
    privileged_review_surface_matches,
    requires_security_review,
    resolve_analysis_envelope_mode,
)


def test_bootstrap_sync_policy_freezes_backlog_signal_terms() -> None:
    """Backlog markers should stay deterministic across follow-on automation slices."""

    assert BACKLOG_SIGNAL_TERMS == (
        "backlog",
        "ledger",
        "roadmap",
        "defer",
        "deferred",
        "follow-up",
        "follow up",
    )


def test_bootstrap_sync_policy_freezes_implementation_roots() -> None:
    """Implementation roots must remain explicit until widened in a dedicated PR."""

    assert IMPLEMENTATION_PATH_PREFIXES == (
        "app/",
        "core/",
        "scripts/",
        "frontend/",
        "ios/",
    )


def test_bootstrap_sync_policy_freezes_privileged_review_prefixes() -> None:
    """Privileged review prefixes must remain canonical and reviewable."""

    assert PRIVILEGED_REVIEW_PREFIXES == (
        ".cursor/agents/",
        ".github/workflows/",
        ".github/actions/",
        "ios/fastlane/",
        "scripts/orchestration/",
        "scripts/ci/",
        "scripts/release/",
        "docs/orchestration/",
        "docs/review/",
        "tests/guards/",
        "trivy/",
    )


def test_bootstrap_sync_policy_freezes_privileged_review_patterns() -> None:
    """Privileged review glob patterns must stay canonical and reviewable."""

    assert PRIVILEGED_REVIEW_PATTERNS == (
        "AGENTS.md",
        "Dockerfile",
        "Makefile",
        "RUNBOOK_AGENT.md",
        ".bandit",
        ".bandit.yaml",
        ".coderabbit.yaml",
        ".dockerignore",
        ".nvmrc",
        ".secrets.baseline",
        ".sourcery.yaml",
        ".trivyignore",
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        ".devcontainer/Dockerfile",
        ".devcontainer/devcontainer.json",
        ".devcontainer/docker-compose*.yml",
        ".devcontainer/docker-compose*.yaml",
        ".github/CODEOWNERS",
        ".github/PULL_REQUEST_TEMPLATE/*.md",
        ".github/actionlint.yml",
        ".github/actionlint.yaml",
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
        ".github/pull_request_template.md",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "deploy/Caddyfile*",
        "deploy/docker-compose.production*.yaml",
        "deploy/docker-compose.staging.yaml",
        "frontend/.dockerignore",
        "frontend/Dockerfile.caddy-spa",
        "frontend/package*.json",
        "frontend/wrangler.toml",
        "ios/Gemfile*",
        "ios/Package.swift",
        "ios/Package.resolved",
        "ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
        "ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift",
        "ios/PulsePlate/PrivacyInfo.xcprivacy",
        "mcp-config.json",
        "opencode.json",
        "package*.json",
        "pyproject.toml",
        "requirements*.txt",
        "requirements*.in",
        "constraints*.txt",
        "scripts/deploy.sh",
        "scripts/diagnose_web.sh",
        "scripts/hooks/repo_python.sh",
        "scripts/ops/postgres_backup.sh",
        "scripts/ops/postgres_restore.sh",
        "scripts/redeploy_caddy.sh",
        "scripts/run-backend-tests-pre-commit.sh",
        "scripts/ci_*.sh",
        "scripts/deploy_*.sh",
        "tests/test_repo_policy_guards.py",
        "worker.js",
        "wrangler.toml",
    )


def test_bootstrap_sync_policy_matches_prefixes_for_root_and_nested_paths() -> None:
    """Prefix matching should work for both exact roots and nested paths."""

    prefixes = ("scripts/", "docs/orchestration/")

    assert matches_any_prefix("scripts", prefixes) is True
    assert matches_any_prefix("scripts/orchestration/task_bootstrap.py", prefixes) is True
    assert matches_any_prefix("docs/orchestration/workflow.md", prefixes) is True
    assert matches_any_prefix("tests/test_bootstrap_sync_policy.py", prefixes) is False


def test_bootstrap_sync_policy_detects_backlog_update_markers() -> None:
    """Backlog update signals should fire for both text markers and ledger paths."""

    assert (
        needs_backlog_update(
            goal="Track deferred roadmap follow-up",
            task_class="Documentation",
            candidate_paths=["docs/orchestration/workflow.md"],
        )
        is True
    )
    assert (
        needs_backlog_update(
            goal="Refresh docs",
            task_class="Documentation",
            candidate_paths=["docs/roadmap/BACKLOG_LEDGER.md"],
        )
        is True
    )
    assert (
        needs_backlog_update(
            goal="Implement feature X in core service",
            task_class="Engineering",
            candidate_paths=["src/core/service.py"],
        )
        is False
    )


def test_bootstrap_sync_policy_detects_docs_and_agents_sync_signals() -> None:
    """Docs and agent sync signals should remain narrowly scoped and deterministic."""

    assert AGENT_CONTRACT_PATH_MARKERS == (
        AGENTS_CONTRACT_FILE,
        AGENTS_CURSOR_PREFIX,
        SKILL_CONTRACT_FILE,
    )
    assert needs_docs_sync(["app/security/auth.py"]) is True
    assert needs_docs_sync(["app/security/auth.py", "docs/security/AUTH.md"]) is False
    assert needs_agents_sync([AGENTS_CONTRACT_FILE]) is True
    assert needs_agents_sync([AGENTS_CURSOR_PREFIX]) is True
    assert needs_agents_sync(["frontend/AGENTS.md"]) is True
    assert needs_agents_sync([f"skills/bootstrap/{SKILL_CONTRACT_FILE}"]) is True
    assert needs_agents_sync(["docs/orchestration/workflow.md"]) is False


def test_bootstrap_sync_policy_freezes_docs_only_roots() -> None:
    """Docs-only roots must remain explicit until widened in a dedicated PR."""

    assert DOCS_ONLY_ROOT_FILES == (
        "AGENTS.md",
        "RUNBOOK_AGENT.md",
        "README.md",
        "CLAUDE.md",
        "DEPLOYMENT.md",
    )


def test_bootstrap_sync_policy_detects_docs_only_contract_paths() -> None:
    """Docs-only detection should stay limited to canonical markdown/contract files."""

    assert is_docs_only_contract_path("CONTRIBUTING.md") is True
    assert is_docs_only_contract_path("DEPLOYMENT.md") is True
    assert is_docs_only_contract_path("docs/orchestration/AGENT_MESSAGE_PROTOCOL.md") is True
    assert is_docs_only_contract_path(".github/PULL_REQUEST_TEMPLATE.md") is True
    assert is_docs_only_contract_path("frontend/AGENTS.md") is True
    assert is_docs_only_contract_path("skills/bootstrap/SKILL.md") is True
    assert is_docs_only_contract_path("docs/orchestration/schema.json") is False
    assert is_docs_only_contract_path("scripts/orchestration/task_bootstrap.py") is False
    assert is_docs_only_contract_path("app/internal_notes.md") is False
    assert is_docs_only_contract_path("core/README.md") is False


def test_bootstrap_sync_policy_fails_closed_for_implementation_tree_markdown() -> None:
    """Markdown under implementation roots must not alone justify docs-only envelope."""

    assert resolve_analysis_envelope_mode(["app/internal_notes.md"]) == ANALYSIS_ENVELOPE_MODE
    assert resolve_analysis_envelope_mode(["core/README.md"]) == ANALYSIS_ENVELOPE_MODE


def test_bootstrap_sync_policy_derives_docs_only_envelope_mode_for_contract_scope() -> None:
    """Pure docs/contract scopes may downshift to docs-only envelope mode."""

    assert (
        resolve_analysis_envelope_mode(
            [
                "CONTRIBUTING.md",
                "DEPLOYMENT.md",
            ]
        )
        == DOCS_ONLY_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_normalizes_whitespace_padded_docs_only_paths() -> None:
    """Whitespace-only padding must not change docs-only envelope derivation."""

    assert (
        resolve_analysis_envelope_mode(
            [
                " CONTRIBUTING.md ",
                "\tDEPLOYMENT.md\n",
            ]
        )
        == DOCS_ONLY_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_fails_closed_to_analysis_for_mixed_scope() -> None:
    """Mixed or runtime scopes must resolve to analysis mode."""

    assert resolve_analysis_envelope_mode([]) == ANALYSIS_ENVELOPE_MODE
    assert (
        resolve_analysis_envelope_mode(
            [
                "docs/orchestration/AGENT_MESSAGE_PROTOCOL.md",
                "scripts/orchestration/task_bootstrap.py",
            ]
        )
        == ANALYSIS_ENVELOPE_MODE
    )


def test_bootstrap_sync_policy_detects_privileged_review_surfaces() -> None:
    """Privileged review detection should stay aligned with the canonical prefix set."""

    assert requires_security_review([".github/workflows"]) is True
    assert requires_security_review([".cursor/agents/security-auditor.md"]) is True
    assert requires_security_review([".github/actions/setup/action.yml"]) is True
    assert requires_security_review(["scripts/ci"]) is True
    assert requires_security_review(["scripts/orchestration/task_bootstrap.py"]) is True
    assert requires_security_review(["scripts/release/publish.py"]) is True
    assert requires_security_review(["docs/review/PR_1325_FIXED_MAPPING.md"]) is True
    assert requires_security_review(["tests/guards/test_nosec_policy_guard.py"]) is True
    assert (
        requires_security_review(["tests/guards/test_subprocess_uses_absolute_binaries.py"]) is True
    )
    assert requires_security_review(["trivy/policy.rego"]) is True
    assert requires_security_review(["AGENTS.md"]) is True
    assert requires_security_review(["Dockerfile"]) is True
    assert requires_security_review(["Makefile"]) is True
    assert requires_security_review(["RUNBOOK_AGENT.md"]) is True
    assert requires_security_review([".bandit"]) is True
    assert requires_security_review([".bandit.yaml"]) is True
    assert requires_security_review([".coderabbit.yaml"]) is True
    assert requires_security_review([".dockerignore"]) is True
    assert requires_security_review([".nvmrc"]) is True
    assert requires_security_review([".secrets.baseline"]) is True
    assert requires_security_review([".sourcery.yaml"]) is True
    assert requires_security_review([".trivyignore"]) is True
    assert requires_security_review([".pre-commit-config.yaml"]) is True
    assert requires_security_review([".pre-commit-config.yml"]) is True
    assert requires_security_review([".devcontainer/Dockerfile"]) is True
    assert requires_security_review([".devcontainer/devcontainer.json"]) is True
    assert requires_security_review([".devcontainer/docker-compose.devcontainer.yml"]) is True
    assert requires_security_review([".github/CODEOWNERS"]) is True
    assert requires_security_review([".github/PULL_REQUEST_TEMPLATE/design.md"]) is True
    assert requires_security_review([".github/actionlint.yaml"]) is True
    assert requires_security_review([".github/dependabot.yml"]) is True
    assert requires_security_review([".github/dependabot.yaml"]) is True
    assert requires_security_review([".github/pull_request_template.md"]) is True
    assert requires_security_review(["docker-compose.yaml"]) is True
    assert requires_security_review(["docker-compose.prod.yml"]) is True
    assert requires_security_review(["deploy/Caddyfile"]) is True
    assert requires_security_review(["deploy/Caddyfile.production"]) is True
    assert requires_security_review(["deploy/docker-compose.production.yaml"]) is True
    assert requires_security_review(["deploy/docker-compose.production.selfhosted.yaml"]) is True
    assert requires_security_review(["deploy/docker-compose.staging.yaml"]) is True
    assert requires_security_review(["frontend/.dockerignore"]) is True
    assert requires_security_review(["frontend/Dockerfile.caddy-spa"]) is True
    assert requires_security_review(["frontend/package.json"]) is True
    assert requires_security_review(["frontend/package-lock.json"]) is True
    assert requires_security_review(["frontend/wrangler.toml"]) is True
    assert requires_security_review(["ios/Gemfile"]) is True
    assert requires_security_review(["ios/Gemfile.lock"]) is True
    assert requires_security_review(["ios/Package.swift"]) is True
    assert requires_security_review(["ios/Package.resolved"]) is True
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"]
        )
        is True
    )
    assert (
        requires_security_review(["ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift"])
        is True
    )
    assert requires_security_review(["ios/PulsePlate/PrivacyInfo.xcprivacy"]) is True
    assert requires_security_review(["mcp-config.json"]) is True
    assert requires_security_review(["opencode.json"]) is True
    assert requires_security_review(["package.json"]) is True
    assert requires_security_review(["package-lock.json"]) is True
    assert requires_security_review(["pyproject.toml"]) is True
    assert requires_security_review(["requirements.txt"]) is True
    assert requires_security_review(["requirements-ci-lite.txt"]) is True
    assert requires_security_review(["requirements.in"]) is True
    assert requires_security_review(["constraints.txt"]) is True
    assert requires_security_review(["scripts/deploy.sh"]) is True
    assert requires_security_review(["scripts/diagnose_web.sh"]) is True
    assert requires_security_review(["scripts/hooks/repo_python.sh"]) is True
    assert requires_security_review(["scripts/ops/postgres_backup.sh"]) is True
    assert requires_security_review(["scripts/ops/postgres_restore.sh"]) is True
    assert requires_security_review(["scripts/redeploy_caddy.sh"]) is True
    assert requires_security_review(["scripts/run-backend-tests-pre-commit.sh"]) is True
    assert requires_security_review(["scripts/ci_bandit.sh"]) is True
    assert requires_security_review(["scripts/ci_pip_audit.sh"]) is True
    assert requires_security_review(["scripts/deploy_production.sh"]) is True
    assert requires_security_review(["tests/test_repo_policy_guards.py"]) is True
    assert requires_security_review(["worker.js"]) is True
    assert requires_security_review(["wrangler.toml"]) is True
    assert requires_security_review(["script/orchestration/config.yml"]) is False
    assert requires_security_review(["tests/test_task_bootstrap.py"]) is False
    assert requires_security_review(["tests/guarded/test_nosec_policy_guard.py"]) is False
    assert requires_security_review(["docs/pyproject.toml"]) is False
    assert requires_security_review(["requirements_docs.md"]) is False
    assert requires_security_review(["requirements/dev.txt"]) is False
    assert requires_security_review(["requirements-notes/dev.txt"]) is False
    assert requires_security_review(["constraints/dev.txt"]) is False
    assert requires_security_review(["docker-compose/sandbox.yaml"]) is False
    assert requires_security_review(["docker-compose-notes/prod.yaml"]) is False
    assert requires_security_review(["deploy/nested/docker-compose.production.yaml"]) is False
    assert requires_security_review(["deploy/docker-compose.production/archive.yaml"]) is False
    assert requires_security_review(["deploy/nested/Caddyfile.production"]) is False
    assert requires_security_review([".cursor/agent_notes/security-auditor.md"]) is False
    assert requires_security_review([".devcontainer/nested/Dockerfile"]) is False
    assert requires_security_review([".devcontainer/docker-compose/archive.yml"]) is False
    assert requires_security_review([".github/config/CODEOWNERS"]) is False
    assert requires_security_review([".github/PULL_REQUEST_TEMPLATE/nested/design.md"]) is False
    assert requires_security_review([".github/pull_request_template/archive.md"]) is False
    assert requires_security_review([".github/actionlint/rules.yaml"]) is False
    assert requires_security_review(["frontend/nested/Dockerfile.caddy-spa"]) is False
    assert requires_security_review(["frontend/nested/.dockerignore"]) is False
    assert requires_security_review(["frontend/packages/package-lock.json"]) is False
    assert requires_security_review(["frontend/.nvmrc"]) is False
    assert requires_security_review(["frontend/nested/wrangler.toml"]) is False
    assert requires_security_review(["ios/vendor/Gemfile.lock"]) is False
    assert requires_security_review(["ios/vendor/Package.resolved"]) is False
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/archive/Package.swift"]
        )
        is False
    )
    assert requires_security_review(["ios/PulsePlate/Archive/PrivacyInfo.xcprivacy"]) is False
    assert requires_security_review(["packages/package-lock.json"]) is False
    assert requires_security_review([".github/dependabot/nested.yaml"]) is False
    assert requires_security_review(["scripts/hooks/nested/repo_python.sh"]) is False
    assert requires_security_review(["scripts/deploy/archive.sh"]) is False
    assert requires_security_review(["scripts/ops/archive/postgres_backup.sh"]) is False
    assert requires_security_review(["scripts/run-backend-tests-pre-commit.d/runner.sh"]) is False
    assert requires_security_review(["scripts/ci-tools/bandit.sh"]) is False
    assert requires_security_review(["scripts/deploy/production.sh"]) is False
    assert requires_security_review(["scripts/cicd_notes.sh"]) is False
    assert requires_security_review(["tests/test_repo_policy_guard_notes.py"]) is False
    assert requires_security_review(["workers/worker.js"]) is False
    assert requires_security_review(["deploy/wrangler.toml"]) is False


def test_bootstrap_sync_policy_returns_stable_privileged_review_labels() -> None:
    """Shared matcher labels must be stable because skill-router reasons expose them."""

    assert privileged_review_surface_matches(
        [
            "./.github/actions/setup/action.yml",
            ".github/actions/cache/action.yml",
            " Dockerfile ",
            "deploy/docker-compose.production.selfhosted.yaml",
            "frontend/package-lock.json",
            "requirements-ci-lite.txt",
            "docs/review/PR_1325_FIXED_MAPPING.md",
        ]
    ) == (
        ".github/actions/",
        "Dockerfile",
        "deploy/docker-compose.production*.yaml",
        "frontend/package*.json",
        "requirements*.txt",
        "docs/review/",
    )


def test_bootstrap_sync_policy_fails_closed_to_analysis_for_privileged_docs() -> None:
    """Privileged orchestration docs must stay in analysis mode."""

    candidate_paths = ["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"]

    assert resolve_analysis_envelope_mode(candidate_paths) == ANALYSIS_ENVELOPE_MODE
    assert requires_security_review(candidate_paths) is True


def test_bootstrap_sync_policy_fails_closed_for_whitespace_padded_privileged_docs() -> None:
    """Privileged docs must stay in analysis mode even when input paths contain padding."""

    candidate_paths = ["  docs/orchestration/AGENT_MESSAGE_PROTOCOL.md  "]

    assert resolve_analysis_envelope_mode(candidate_paths) == ANALYSIS_ENVELOPE_MODE
