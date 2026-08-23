"""Tests for canonical bootstrap sync-policy helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.orchestration.bootstrap_sync_policy import (
    AGENT_CONTRACT_PATH_MARKERS,
    AGENTS_CONTRACT_FILE,
    AGENTS_CURSOR_PREFIX,
    ANALYSIS_ENVELOPE_MODE,
    BACKLOG_SIGNAL_TERMS,
    DOCS_ONLY_ENVELOPE_MODE,
    DOCS_ONLY_ROOT_FILES,
    IMPLEMENTATION_PATH_PREFIXES,
    INVARIANT_CHANGE_CLASSES,
    INVARIANT_REVIEW_COVERAGE_CLAIM,
    INVARIANT_REVIEW_REQUIRED_ROLES,
    PRIVILEGED_REVIEW_PREFIXES,
    PRIVILEGED_REVIEW_SURFACES,
    SKILL_CONTRACT_FILE,
    classify_invariant_review,
    is_docs_only_contract_path,
    matches_any_prefix,
    needs_agents_sync,
    needs_backlog_update,
    needs_docs_sync,
    privileged_review_surface_matches,
    requires_security_review,
    resolve_analysis_envelope_mode,
)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "orchestration"


def test_invariant_review_classifier_freezes_closed_contract() -> None:
    """The pre-fix gate must keep a small explicit class and role surface."""

    assert INVARIANT_CHANGE_CLASSES == (
        "parser",
        "validator",
        "guard",
        "authority",
    )
    assert INVARIANT_REVIEW_REQUIRED_ROLES == (
        "logic-agent",
        "philosophy-agent",
    )
    assert INVARIANT_REVIEW_COVERAGE_CLAIM == "explicit_plus_bounded_positive_triggers_only"


def test_invariant_review_classifier_merges_explicit_and_bounded_hints() -> None:
    """Explicit classes stay authoritative while hints add bounded evidence."""

    decision = classify_invariant_review(
        candidate_paths=[
            "scripts/ci/guard_actions_pin.py",
            "scripts/orchestration/check_merge_ready.py",
        ],
        explicit_classes=["authority", "parser", "parser"],
    )

    assert decision.change_classes == (
        "parser",
        "validator",
        "guard",
        "authority",
    )
    assert decision.fingerprint == "parser,validator,guard,authority"
    assert [row.to_mapping() for row in decision.trigger_evidence] == [
        {"change_class": "parser", "source": "explicit"},
        {"change_class": "authority", "source": "explicit"},
        {
            "change_class": "guard",
            "source": "bounded_path_hint",
            "path": "scripts/ci/guard_actions_pin.py",
        },
        {
            "change_class": "validator",
            "source": "bounded_path_hint",
            "path": "scripts/orchestration/check_merge_ready.py",
        },
        {
            "change_class": "authority",
            "source": "bounded_path_hint",
            "path": "scripts/orchestration/check_merge_ready.py",
        },
    ]


@pytest.mark.parametrize(
    "path",
    [
        "./scripts/ci/check_policy.py",
        str(Path(__file__).resolve().parents[1] / "scripts/ci/check_policy.py"),
    ],
)
def test_invariant_review_classifier_requires_canonical_wire_paths(path: str) -> None:
    """Producer aliases must be normalized before strict policy consumers run."""

    with pytest.raises(ValueError, match="invariant review paths"):
        classify_invariant_review(candidate_paths=[path])


def test_invariant_review_root_scope_activates_all_closed_classes() -> None:
    decision = classify_invariant_review(candidate_paths=["."])

    assert decision.change_classes == INVARIANT_CHANGE_CLASSES
    assert [row.to_mapping() for row in decision.trigger_evidence] == [
        {
            "change_class": change_class,
            "source": "bounded_path_hint",
            "path": ".",
        }
        for change_class in INVARIANT_CHANGE_CLASSES
    ]


@pytest.mark.parametrize(
    ("path", "expected_classes"),
    [
        ("scripts/orchestration/json_parser.py", ("parser",)),
        ("scripts/ci/policy_validator.py", ("validator",)),
        ("scripts/orchestration/schema_validation.py", ("validator",)),
        ("scripts/ci/check_policy.py", ("validator",)),
        ("scripts/ci/guard_actions_pin.py", ("guard",)),
        ("scripts/orchestration/scope_guard.py", ("guard",)),
        ("tests/guards/test_agent_consistency_guard.py", ("guard",)),
        ("scripts/orchestration/task_bootstrap.py", ("authority",)),
        (
            "scripts/ci/check_pr_merge_readiness.py",
            ("validator", "authority"),
        ),
    ],
)
def test_invariant_review_classifier_bounded_positive_matrix(
    path: str,
    expected_classes: tuple[str, ...],
) -> None:
    """Only reviewed control-plane naming patterns create automatic hints."""

    decision = classify_invariant_review(candidate_paths=[path])

    assert decision.change_classes == expected_classes
    assert all(row.source == "bounded_path_hint" for row in decision.trigger_evidence)


@pytest.mark.parametrize(
    "path",
    [
        "core/rag/simple_rag.py",
        ".python-version",
        "Dockerfile",
        "app/check_policy.py",
        "docs/orchestration/check_policy.py",
        "scripts/orchestration/fixtures/check_policy.py",
        "tests/fixtures/guards/test_scope_guard.py",
        "scripts/ci/Check_policy.py",
        "scripts/ci/check_policy.md",
    ],
)
def test_invariant_review_classifier_rejects_decoy_hints(path: str) -> None:
    """A negative match means only that no configured bounded hint matched."""

    decision = classify_invariant_review(candidate_paths=[path])

    assert decision.required is False
    assert decision.change_classes == ()
    assert decision.trigger_evidence == ()


@pytest.mark.parametrize(
    "change_class",
    ["", "Parser", " parser", "parser ", "pаrser", "unknown"],
)
def test_invariant_review_classifier_rejects_malformed_explicit_classes(
    change_class: str,
) -> None:
    """Python callers cannot bypass the exact argparse enum contract."""

    with pytest.raises(ValueError, match="Unsupported invariant change class"):
        classify_invariant_review(
            candidate_paths=[],
            explicit_classes=[change_class],
        )


@pytest.mark.parametrize(
    "path",
    [
        "../scripts/ci/check_policy.py",
        "scripts/../scripts/ci/check_policy.py",
        "scripts\\ci\\check_policy.py",
        "scripts//ci/check_policy.py",
        "scripts/ci/check_policy.py\nignored",
        "/tmp/check_policy.py",
        "C:/repo/scripts/ci/check_policy.py",
    ],
)
def test_invariant_review_classifier_rejects_unsafe_paths(path: str) -> None:
    """Ambiguous or out-of-repo matcher inputs fail closed."""

    with pytest.raises(ValueError, match="invariant review paths"):
        classify_invariant_review(candidate_paths=[path])


def _privileged_surface_cases() -> list[dict[str, object]]:
    fixture = json.loads((FIXTURE_DIR / "privileged_review_surfaces.json").read_text())
    return list(fixture["cases"])


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
        ".github/workflows/",
        ".github/actions/",
        ".github/agents/",
        ".github/prompts/",
        ".github/scripts/",
        ".agents/skills/",
        ".cursor/agents/",
        ".cursor/commands/",
        ".cursor/rules/",
        ".githooks/",
        "tests/guards/",
        "tools/agentguard/",
        "tools/codex_skills/",
        "tools/cybersecurity_skills/",
        "ios/fastlane/",
        "scripts/orchestration/",
        "scripts/ci/",
        "scripts/metatron_lab/",
        "scripts/release/",
        "docs/orchestration/",
        "docs/review/",
        "deploy/",
        ".devcontainer/",
        "appstore/fitchef/",
        "deploy/metatron-lab/",
        "trivy/",
    )
    assert tuple(surface.surface_class for surface in PRIVILEGED_REVIEW_SURFACES) == (
        "repo_agent_contracts",
        "github_workflows",
        "github_actions",
        "github_agent_control",
        "github_prompt_control",
        "github_support_scripts",
        "github_codeowners",
        "cursor_and_local_hook_control",
        "ios_fastlane",
        "orchestration_scripts",
        "merge_governance_scripts",
        "metatron_lab_scripts",
        "release_scripts",
        "orchestration_governance_docs",
        "review_governance_docs",
        "deploy_and_image_config",
        "security_scan_policy",
        "dependency_and_hook_config",
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
    assert needs_agents_sync([f"{AGENTS_CURSOR_PREFIX}agent-coordinator.md"]) is True
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


def test_bootstrap_sync_policy_rejects_whitespace_padded_paths() -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        resolve_analysis_envelope_mode(
            [
                " CONTRIBUTING.md ",
                "\tDEPLOYMENT.md\n",
            ]
        )


def test_bootstrap_sync_policy_root_scope_is_conservative() -> None:
    assert requires_security_review(["."]) is True
    assert privileged_review_surface_matches(["."]) == ()
    assert needs_docs_sync(["."]) is True
    assert needs_agents_sync(["."]) is True
    assert (
        needs_backlog_update(
            goal="ordinary task",
            task_class="Orchestration",
            candidate_paths=["."],
        )
        is True
    )
    assert resolve_analysis_envelope_mode(["."]) == ANALYSIS_ENVELOPE_MODE


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
    assert requires_security_review([".agents/skills/pulseplate-gates/SKILL.md"]) is True
    assert requires_security_review([".cursor/agents/security-auditor.md"]) is True
    assert requires_security_review([".cursor/commands/init.md"]) is True
    assert requires_security_review([".cursor/rules/cybersecurity-skills-index.md"]) is True
    assert requires_security_review([".github/actions/setup/action.yml"]) is True
    assert requires_security_review([".github/agents/my-agent.md"]) is True
    assert requires_security_review([".github/prompts/vibecoder.prompt.md"]) is True
    assert requires_security_review([".github/scripts/parse-safety-report.py"]) is True
    assert requires_security_review([".githooks/pre-push"]) is True
    assert requires_security_review(["appstore/fitchef/appstore_review_checklist.md"]) is True
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
    assert requires_security_review(["scripts/AGENTS.md"]) is True
    assert requires_security_review(["tests/AGENTS.md"]) is True
    assert requires_security_review(["Dockerfile"]) is True
    assert requires_security_review(["Makefile"]) is True
    assert requires_security_review(["RUNBOOK_AGENT.md"]) is True
    assert requires_security_review([".env.example"]) is True
    assert requires_security_review([".bandit"]) is True
    assert requires_security_review([".bandit.yaml"]) is True
    assert requires_security_review([".coveragerc"]) is True
    assert requires_security_review([".coderabbit.yaml"]) is True
    assert requires_security_review([".dockerignore"]) is True
    assert requires_security_review([".gitmodules"]) is True
    assert requires_security_review([".flake8"]) is True
    assert requires_security_review([".markdownlint.json"]) is True
    assert requires_security_review([".nvmrc"]) is True
    assert requires_security_review([".python-version"]) is True
    assert requires_security_review([".ruby-version"]) is True
    assert requires_security_review([".secrets.baseline"]) is True
    assert requires_security_review([".sourcery.yaml"]) is True
    assert requires_security_review([".tool-versions"]) is True
    assert requires_security_review([".trivyignore"]) is True
    assert requires_security_review([".yamllint"]) is True
    assert requires_security_review([".pre-commit-config.yaml"]) is True
    assert requires_security_review([".pre-commit-config.yml"]) is True
    assert requires_security_review([".vscode/extensions.json"]) is True
    assert requires_security_review([".cursor/mcp.json.example"]) is True
    assert requires_security_review([".kimi/mcp.json.example"]) is True
    assert requires_security_review([".devcontainer/Dockerfile"]) is True
    assert requires_security_review([".devcontainer/devcontainer.json"]) is True
    assert requires_security_review([".devcontainer/docker-compose.devcontainer.yml"]) is True
    assert requires_security_review([".github/CODEOWNERS"]) is True
    assert requires_security_review([".github/PULL_REQUEST_TEMPLATE/design.md"]) is True
    assert requires_security_review([".github/actionlint.yaml"]) is True
    assert requires_security_review([".github/dependabot.yml"]) is True
    assert requires_security_review([".github/dependabot.yaml"]) is True
    assert requires_security_review([".github/pull_request_template.md"]) is True
    assert requires_security_review(["alembic.ini"]) is True
    assert requires_security_review(["codecov.yml"]) is True
    assert requires_security_review(["codecov.yaml"]) is True
    assert requires_security_review(["docker-compose.yaml"]) is True
    assert requires_security_review(["docker-compose.prod.yml"]) is True
    assert requires_security_review(["deploy/Caddyfile"]) is True
    assert requires_security_review(["deploy/Caddyfile.production"]) is True
    assert requires_security_review(["deploy/docker-compose.production.yaml"]) is True
    assert requires_security_review(["deploy/docker-compose.production.selfhosted.yaml"]) is True
    assert requires_security_review(["deploy/docker-compose.staging.yaml"]) is True
    assert requires_security_review(["deploy/metatron-lab/docker-compose.yaml"]) is True
    assert (
        requires_security_review(["deploy/systemd/pulseplate-postgres-backup.service.example"])
        is True
    )
    assert (
        requires_security_review(["deploy/systemd/pulseplate-postgres-backup.timer.example"])
        is True
    )
    assert requires_security_review(["docs/security/TOOLING_SURFACE_POLICY.md"]) is True
    assert requires_security_review(["docs/security/vscode_extensions_allowlist.txt"]) is True
    assert requires_security_review(["frontend/.dockerignore"]) is True
    assert requires_security_review(["frontend/Dockerfile.caddy-spa"]) is True
    assert requires_security_review(["frontend/package.json"]) is True
    assert requires_security_review(["frontend/package-lock.json"]) is True
    assert requires_security_review(["frontend/wrangler.toml"]) is True
    assert requires_security_review(["ios/Gemfile"]) is True
    assert requires_security_review(["ios/Gemfile.lock"]) is True
    assert requires_security_review(["ios/Package.swift"]) is True
    assert requires_security_review(["ios/Package.resolved"]) is True
    assert requires_security_review(["ios/PulsePlate.xcodeproj/project.pbxproj"]) is True
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"]
        )
        is True
    )
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcodeproj/xcshareddata/xcschemes/PulsePlate.xcscheme"]
        )
        is True
    )
    assert (
        requires_security_review(["ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift"])
        is True
    )
    assert requires_security_review(["ios/PulsePlate/Info-Release.plist"]) is True
    assert requires_security_review(["ios/PulsePlate/PulsePlate.entitlements"]) is True
    assert requires_security_review(["ios/PulsePlate/PrivacyInfo.xcprivacy"]) is True
    assert requires_security_review(["ios/PulsePlate/en.lproj/InfoPlist.strings"]) is True
    assert requires_security_review(["mcp-config.json"]) is True
    assert requires_security_review(["mcp-setup.sh"]) is True
    assert requires_security_review(["mcp_pulseplate_server.py"]) is True
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
    assert requires_security_review(["scripts/devcontainer/smoke.sh"]) is True
    assert requires_security_review(["scripts/install_codex_skills.sh"]) is True
    assert requires_security_review(["scripts/opencode/run_pulseplate_mcp.sh"]) is True
    assert requires_security_review(["scripts/ops/postgres_backup.sh"]) is True
    assert requires_security_review(["scripts/ops/postgres_restore.sh"]) is True
    assert requires_security_review(["scripts/redeploy_caddy.sh"]) is True
    assert requires_security_review(["scripts/run-backend-tests-pre-commit.sh"]) is True
    assert requires_security_review(["scripts/validate-ci-environment.sh"]) is True
    assert requires_security_review(["scripts/verify_codex_skills_install.py"]) is True
    assert requires_security_review(["scripts/ci_bandit.sh"]) is True
    assert requires_security_review(["scripts/ci_pip_audit.sh"]) is True
    assert requires_security_review(["scripts/deploy_production.sh"]) is True
    assert requires_security_review(["setup_custom_mcp.py"]) is True
    assert requires_security_review(["scripts/metatron_lab/compose_guard.py"]) is True
    assert requires_security_review(["tests/security/_api_authz_contracts.py"]) is True
    assert requires_security_review(["tests/security/test_api_authz_contract_static.py"]) is True
    assert requires_security_review(["tests/test_install_codex_skills.py"]) is True
    assert requires_security_review(["tests/test_repo_policy_guards.py"]) is True
    assert requires_security_review(["tools/agentguard/scan_text.mjs"]) is True
    assert requires_security_review(["tools/codex_skills/pulseplate-gates/SKILL.md"]) is True
    assert requires_security_review(["tools/cybersecurity_skills/index.json"]) is True
    assert requires_security_review(["update_api_key.py"]) is True
    assert requires_security_review(["worker.js"]) is True
    assert requires_security_review(["wrangler.toml"]) is True
    assert requires_security_review(["script/orchestration/config.yml"]) is False
    assert requires_security_review(["tests/test_task_bootstrap.py"]) is False
    assert requires_security_review(["tests/guarded/test_nosec_policy_guard.py"]) is False
    assert requires_security_review(["docs/pyproject.toml"]) is True
    assert requires_security_review(["requirements_docs.md"]) is False
    assert requires_security_review(["requirements/dev.txt"]) is False
    assert requires_security_review(["requirements-notes/dev.txt"]) is False
    assert requires_security_review(["constraints/dev.txt"]) is False
    assert requires_security_review(["docker-compose/sandbox.yaml"]) is False
    assert requires_security_review(["docker-compose-notes/prod.yaml"]) is False
    assert requires_security_review(["deploy/nested/docker-compose.production.yaml"]) is True
    assert requires_security_review(["deploy/docker-compose.production/archive.yaml"]) is True
    assert requires_security_review(["deploy/nested/Caddyfile.production"]) is True
    assert requires_security_review(["deploy/metatron_lab/docker-compose.yaml"]) is True
    assert requires_security_review(["deploy/metatron-lab-notes/docker-compose.yaml"]) is True
    assert (
        requires_security_review(
            ["deploy/systemd/archive/pulseplate-postgres-backup.service.example"]
        )
        is True
    )
    assert requires_security_review(["deploy/systemd/pulseplate-postgres-backup-notes.md"]) is True
    assert requires_security_review([".cursor/agent_notes/security-auditor.md"]) is False
    assert requires_security_review([".cursor/command/init.md"]) is False
    assert requires_security_review([".cursor/rules-notes/cybersecurity-skills-index.md"]) is False
    assert requires_security_review([".cursor/mcp.json"]) is False
    assert requires_security_review([".devcontainer/nested/Dockerfile"]) is True
    assert requires_security_review([".devcontainer/docker-compose/archive.yml"]) is True
    assert requires_security_review([".github/config/CODEOWNERS"]) is False
    assert requires_security_review([".github/PULL_REQUEST_TEMPLATE/nested/design.md"]) is False
    assert requires_security_review([".github/pull_request_template/archive.md"]) is False
    assert requires_security_review([".github/actionlint/rules.yaml"]) is False
    assert requires_security_review([".github/agent/my-agent.md"]) is False
    assert requires_security_review([".github/agents-notes/my-agent.md"]) is False
    assert requires_security_review([".github/prompt/vibecoder.prompt.md"]) is False
    assert requires_security_review([".github/prompts-notes/vibecoder.prompt.md"]) is False
    assert requires_security_review([".github/script/parse-safety-report.py"]) is False
    assert requires_security_review([".github/scripts-notes/parse-safety-report.py"]) is False
    assert requires_security_review([".githooks-notes/pre-push"]) is False
    assert (
        requires_security_review(["appstore/fitchef-notes/appstore_review_checklist.md"]) is False
    )
    assert requires_security_review(["AGENTS.md.backup"]) is False
    assert requires_security_review(["docs/AGENTS.md.backup"]) is False
    assert requires_security_review(["docs/.coveragerc"]) is False
    assert requires_security_review(["docs/.env.example"]) is False
    assert requires_security_review(["docs/.flake8"]) is False
    assert requires_security_review(["docs/.vscode/extensions.json"]) is False
    assert requires_security_review(["docs/codecov.yml"]) is False
    assert requires_security_review(["docs/.gitmodules"]) is False
    assert requires_security_review(["docs/.markdownlint.json"]) is False
    assert requires_security_review(["docs/.yamllint"]) is False
    assert requires_security_review(["docs/security/archive/TOOLING_SURFACE_POLICY.md"]) is False
    assert (
        requires_security_review(["docs/security/archive/vscode_extensions_allowlist.txt"]) is False
    )
    assert requires_security_review(["frontend/nested/Dockerfile.caddy-spa"]) is False
    assert requires_security_review(["frontend/nested/.dockerignore"]) is False
    assert requires_security_review(["frontend/packages/package-lock.json"]) is False
    assert requires_security_review(["frontend/.nvmrc"]) is False
    assert requires_security_review(["frontend/nested/wrangler.toml"]) is False
    assert requires_security_review(["ios/vendor/Gemfile.lock"]) is False
    assert requires_security_review(["ios/vendor/Package.resolved"]) is False
    assert requires_security_review(["ios/Archive/PulsePlate.xcodeproj/project.pbxproj"]) is False
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcodeproj/xcshareddata/xcschemes/archive/PulsePlate.xcscheme"]
        )
        is False
    )
    assert (
        requires_security_review(
            ["ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/archive/Package.swift"]
        )
        is False
    )
    assert requires_security_review(["ios/PulsePlate/Archive/PrivacyInfo.xcprivacy"]) is False
    assert requires_security_review(["ios/PulsePlate/Archive/PulsePlate.entitlements"]) is False
    assert requires_security_review(["ios/PulsePlate/en.lproj/archive/InfoPlist.strings"]) is False
    assert requires_security_review(["ios/PulsePlate/en.lproj/InfoPlist.strings.backup"]) is False
    assert requires_security_review(["packages/package-lock.json"]) is False
    assert requires_security_review([".github/dependabot/nested.yaml"]) is False
    assert requires_security_review(["docs/alembic.ini"]) is False
    assert requires_security_review([".kimi/mcp.json"]) is False
    assert requires_security_review([".kimi/mcp.json.example.backup"]) is False
    assert requires_security_review(["mcp-setup/archive.sh"]) is False
    assert requires_security_review(["docs/mcp_pulseplate_server.py"]) is False
    assert requires_security_review(["scripts/mcp-setup.sh"]) is False
    assert requires_security_review(["scripts/hooks/nested/repo_python.sh"]) is False
    assert requires_security_review(["scripts/devcontainer/archive/smoke.sh"]) is False
    assert requires_security_review(["scripts/deploy/archive.sh"]) is False
    assert requires_security_review(["scripts/ops/archive/postgres_backup.sh"]) is False
    assert requires_security_review(["scripts/install_codex_skills/archive.sh"]) is False
    assert requires_security_review(["scripts/opencode/archive/run_pulseplate_mcp.sh"]) is False
    assert requires_security_review(["scripts/run-backend-tests-pre-commit.d/runner.sh"]) is False
    assert requires_security_review(["scripts/validate-ci-environment/archive.sh"]) is False
    assert requires_security_review(["scripts/tools/verify_codex_skills_install.py"]) is False
    assert requires_security_review(["scripts/ci-tools/bandit.sh"]) is False
    assert requires_security_review(["scripts/deploy/production.sh"]) is False
    assert requires_security_review(["scripts/setup_custom_mcp.py"]) is False
    assert requires_security_review(["scripts/cicd_notes.sh"]) is False
    assert requires_security_review(["scripts/metatron_lab_notes/compose_guard.py"]) is False
    assert requires_security_review(["tests/test_repo_policy_guard_notes.py"]) is False
    assert requires_security_review(["tests/security/_api_authz_contracts_notes.py"]) is False
    assert requires_security_review(["tests/security/contracts/_api_authz_contracts.py"]) is False
    assert requires_security_review(["tests/install/test_install_codex_skills.py"]) is False
    assert requires_security_review(["tools/agentguard-notes/scan_text.mjs"]) is False
    assert requires_security_review(["tools/codex_skillz/pulseplate-gates/SKILL.md"]) is False
    assert requires_security_review(["tools/cybersecurity_skillz/index.json"]) is False
    assert requires_security_review(["scripts/update_api_key.py"]) is False
    assert requires_security_review(["workers/worker.js"]) is False
    assert requires_security_review(["deploy/wrangler.toml"]) is True


@pytest.mark.parametrize(
    "path",
    (
        "../Dockerfile",
        "../.github/workflows/ci.yml",
        "docs/../.github/workflows/ci.yml",
        "build/../Dockerfile",
    ),
)
def test_security_review_classifier_rejects_noncanonical_paths(path: str) -> None:
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        requires_security_review([path])


def test_bootstrap_sync_policy_returns_stable_privileged_review_labels() -> None:
    """Shared matcher labels must be stable because skill-router reasons expose them."""

    assert privileged_review_surface_matches(
        sorted(
            [
                ".github/actions/setup/action.yml",
                ".github/workflows/ci.yml",
                ".github/actions/cache/action.yml",
                ".github/agents/my-agent.md",
                ".github/prompts/vibecoder.prompt.md",
                ".github/scripts/parse-safety-report.py",
                ".vscode/extensions.json",
                "scripts/AGENTS.md",
                "Dockerfile",
                ".env.example",
                ".flake8",
                ".markdownlint.json",
                ".coveragerc",
                ".kimi/mcp.json.example",
                "alembic.ini",
                ".gitmodules",
                "codecov.yml",
                ".yamllint",
                "appstore/fitchef/appstore_review_checklist.md",
                "deploy/docker-compose.production.selfhosted.yaml",
                "deploy/metatron-lab/docker-compose.yaml",
                "deploy/systemd/pulseplate-postgres-backup.timer.example",
                "docs/security/vscode_extensions_allowlist.txt",
                "frontend/package-lock.json",
                "ios/PulsePlate.xcodeproj/xcshareddata/xcschemes/PulsePlate.xcscheme",
                "ios/PulsePlate/PulsePlate.entitlements",
                "ios/PulsePlate/en.lproj/InfoPlist.strings",
                "mcp_pulseplate_server.py",
                "scripts/devcontainer/smoke.sh",
                "scripts/metatron_lab/compose_guard.py",
                "scripts/opencode/run_pulseplate_mcp.sh",
                "scripts/validate-ci-environment.sh",
                "scripts/verify_codex_skills_install.py",
                "setup_custom_mcp.py",
                "tests/test_install_codex_skills.py",
                "tests/guards/test_nosec_policy_guard.py",
                "tools/agentguard/scan_text.mjs",
                "tools/codex_skills/pulseplate-gates/SKILL.md",
                "update_api_key.py",
                "mcp-setup.sh",
                "requirements-ci-lite.txt",
                "docs/review/PR_1325_FIXED_MAPPING.md",
            ]
        )
    ) == (
        "agent-contract",
        ".github/workflows/",
        ".github/actions/",
        ".github/agents/",
        ".github/prompts/",
        ".github/scripts/",
        "local-agent-tooling-control",
        "scripts/metatron_lab/",
        "scripts/release/",
        "docs/review/",
        "deploy-or-image-config",
        "dependency-or-hook-config",
    )


@pytest.mark.parametrize("case", _privileged_surface_cases(), ids=lambda case: case["case_id"])
def test_bootstrap_sync_policy_uses_reviewed_privileged_surface_matrix(
    case: dict[str, object],
) -> None:
    """Shared matrix must drive exact, suffix, prefix, and negative matching."""

    path = str(case["path"])
    is_privileged = bool(case["privileged"])
    assert requires_security_review([path]) is is_privileged

    matches = privileged_review_surface_matches([path])
    if is_privileged:
        assert case["reason"] in matches
    else:
        assert matches == ()


def test_bootstrap_sync_policy_fails_closed_to_analysis_for_privileged_docs() -> None:
    """Privileged orchestration docs must stay in analysis mode."""

    candidate_paths = ["docs/orchestration/AGENT_MESSAGE_PROTOCOL.md"]

    assert resolve_analysis_envelope_mode(candidate_paths) == ANALYSIS_ENVELOPE_MODE
    assert requires_security_review(candidate_paths) is True


def test_bootstrap_sync_policy_rejects_whitespace_padded_privileged_docs() -> None:
    """Strict policy consumers reject producer spelling aliases."""

    candidate_paths = ["  docs/orchestration/AGENT_MESSAGE_PROTOCOL.md  "]

    with pytest.raises(ValueError, match="canonical task candidate paths"):
        resolve_analysis_envelope_mode(candidate_paths)
    with pytest.raises(ValueError, match="canonical task candidate paths"):
        requires_security_review(candidate_paths)
