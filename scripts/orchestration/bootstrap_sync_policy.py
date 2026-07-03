"""Canonical sync-policy helpers for task bootstrap.

RU: Централизует sync-policy константы и matcher-правила для bootstrap packet.
EN: Centralizes sync-policy constants and matcher rules for the bootstrap packet.
"""

from __future__ import annotations

import posixpath
from collections.abc import Sequence
from fnmatch import fnmatchcase

BACKLOG_SIGNAL_TERMS: tuple[str, ...] = (
    "backlog",
    "ledger",
    "roadmap",
    "defer",
    "deferred",
    "follow-up",
    "follow up",
)

IMPLEMENTATION_PATH_PREFIXES: tuple[str, ...] = (
    "app/",
    "core/",
    "scripts/",
    "frontend/",
    "ios/",
)

PRIVILEGED_REVIEW_PREFIXES: tuple[str, ...] = (
    ".agents/skills/",
    ".cursor/agents/",
    ".cursor/commands/",
    ".cursor/rules/",
    ".github/workflows/",
    ".github/actions/",
    ".github/scripts/",
    ".githooks/",
    "deploy/metatron-lab/",
    "ios/fastlane/",
    "scripts/metatron_lab/",
    "scripts/orchestration/",
    "scripts/ci/",
    "scripts/release/",
    "docs/orchestration/",
    "docs/review/",
    "tests/guards/",
    "tools/agentguard/",
    "tools/codex_skills/",
    "tools/cybersecurity_skills/",
    "trivy/",
)
PRIVILEGED_REVIEW_PATTERNS: tuple[str, ...] = (
    "AGENTS.md",
    "**/AGENTS.md",
    "Dockerfile",
    "Makefile",
    "RUNBOOK_AGENT.md",
    ".bandit",
    ".bandit.yaml",
    ".coveragerc",
    ".coderabbit.yaml",
    ".dockerignore",
    ".gitmodules",
    ".nvmrc",
    ".python-version",
    ".ruby-version",
    ".secrets.baseline",
    ".sourcery.yaml",
    ".tool-versions",
    ".trivyignore",
    ".yamllint",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
    ".cursor/mcp.json.example",
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
    "codecov.yml",
    "codecov.yaml",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    "deploy/Caddyfile*",
    "deploy/docker-compose.production*.yaml",
    "deploy/docker-compose.staging.yaml",
    "deploy/systemd/pulseplate-postgres-backup.*",
    "frontend/.dockerignore",
    "frontend/Dockerfile.caddy-spa",
    "frontend/package*.json",
    "frontend/wrangler.toml",
    "ios/Gemfile*",
    "ios/Package.swift",
    "ios/Package.resolved",
    "ios/PulsePlate.xcodeproj/project.pbxproj",
    "ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
    "ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift",
    "ios/PulsePlate/Info-Release.plist",
    "ios/PulsePlate/PulsePlate.entitlements",
    "ios/PulsePlate/PrivacyInfo.xcprivacy",
    "ios/PulsePlate/*/InfoPlist.strings",
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
    "scripts/install_codex_skills.sh",
    "scripts/ops/postgres_backup.sh",
    "scripts/ops/postgres_restore.sh",
    "scripts/redeploy_caddy.sh",
    "scripts/run-backend-tests-pre-commit.sh",
    "scripts/validate-ci-environment.sh",
    "scripts/ci_*.sh",
    "scripts/deploy_*.sh",
    "tests/security/_api_authz_contracts.py",
    "tests/security/test_api_authz_contract_static.py",
    "tests/test_repo_policy_guards.py",
    "worker.js",
    "wrangler.toml",
)

AGENTS_CONTRACT_FILE = "AGENTS.md"
AGENTS_CURSOR_PREFIX = ".cursor/agents/"
SKILL_CONTRACT_FILE = "SKILL.md"
AGENT_CONTRACT_PATH_MARKERS: tuple[str, ...] = (
    AGENTS_CONTRACT_FILE,
    AGENTS_CURSOR_PREFIX,
    SKILL_CONTRACT_FILE,
)

BACKLOG_LEDGER_PATH = "docs/roadmap/backlog_ledger.md"
DOCS_PATH_PREFIX = "docs/"
DOCS_ONLY_ROOT_FILES: tuple[str, ...] = (
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
    "README.md",
    "CLAUDE.md",
    "DEPLOYMENT.md",
)
ANALYSIS_ENVELOPE_MODE = "analysis"
DOCS_ONLY_ENVELOPE_MODE = "docs_only"


def matches_any_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    """Return True when a path matches a canonical prefix exactly or by subtree.

    RU: Совпадение считается валидным и для корня, и для вложенного пути.
    EN: A match is valid for both the root directory and any nested path.
    """

    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def normalize_policy_path(path: str) -> str:
    """Normalize a repo-relative policy path without resolving filesystem state."""

    normalized = path.strip().replace("\\", "/")
    normalized = posixpath.normpath(normalized)
    if normalized == ".":
        return ""
    return normalized


def matches_privileged_review_pattern(path: str, pattern: str) -> bool:
    """Return True when ``path`` matches a privileged pattern at its intended depth."""

    if pattern.startswith("**/"):
        suffix = pattern.removeprefix("**/")
        return path == suffix or path.endswith(f"/{suffix}")

    path_parts = path.split("/")
    pattern_parts = pattern.split("/")
    if len(path_parts) != len(pattern_parts):
        return False
    return all(
        fnmatchcase(path_part, pattern_part)
        for path_part, pattern_part in zip(path_parts, pattern_parts, strict=True)
    )


def privileged_review_surface_matches(candidate_paths: Sequence[str]) -> tuple[str, ...]:
    """Return stable privileged-surface match labels for candidate paths.

    RU: Возвращает канонические labels, которые используют bootstrap и skill router.
    EN: Returns canonical labels shared by bootstrap and skill routing.
    """

    matches: list[str] = []
    seen: set[str] = set()
    for raw_path in candidate_paths:
        path = normalize_policy_path(raw_path)
        if not path:
            continue
        label = ""
        for prefix in PRIVILEGED_REVIEW_PREFIXES:
            if matches_any_prefix(path, (prefix,)):
                label = prefix
                break
        if not label:
            for pattern in PRIVILEGED_REVIEW_PATTERNS:
                if matches_privileged_review_pattern(path, pattern):
                    label = pattern
                    break
        if label and label not in seen:
            seen.add(label)
            matches.append(label)
    return tuple(matches)


def requires_security_review(candidate_paths: Sequence[str]) -> bool:
    """Return True when the task touches privileged review surfaces.

    RU: Привилегированные поверхности всегда тянут security-review path.
    EN: Privileged surfaces always force the security-review path.
    """

    return bool(privileged_review_surface_matches(candidate_paths))


def needs_backlog_update(
    *,
    goal: str,
    task_class: str,
    candidate_paths: Sequence[str],
) -> bool:
    """Return True when backlog bookkeeping markers are present.

    RU: Сигнал определяется по текстовым маркерам и explicit backlog ledger path.
    EN: The signal is derived from text markers plus the explicit backlog ledger path.
    """

    haystack = " ".join(
        [
            goal.strip().lower(),
            task_class.strip().lower(),
            *(path.lower() for path in candidate_paths),
        ]
    )
    if any(term in haystack for term in BACKLOG_SIGNAL_TERMS):
        return True
    return any(BACKLOG_LEDGER_PATH in path.lower() for path in candidate_paths)


def needs_docs_sync(candidate_paths: Sequence[str]) -> bool:
    """Return True when implementation paths changed without a docs path.

    RU: Кодовые изменения без docs-path должны поднять deterministic docs sync flag.
    EN: Code changes without a docs path must raise the deterministic docs sync flag.
    """

    has_implementation_path = any(
        matches_any_prefix(path, IMPLEMENTATION_PATH_PREFIXES) for path in candidate_paths
    )
    has_docs_path = any(
        path == "docs" or path.startswith(DOCS_PATH_PREFIX) for path in candidate_paths
    )
    return has_implementation_path and not has_docs_path


def needs_agents_sync(candidate_paths: Sequence[str]) -> bool:
    """Return True when AGENTS or SKILL contract files are in scope.

    RU: Сигнал ограничен каноническими agent-contract путями и не шире.
    EN: The signal is intentionally limited to canonical agent-contract paths.
    """

    return any(
        path == AGENTS_CONTRACT_FILE
        or path.endswith(f"/{AGENTS_CONTRACT_FILE}")
        or path.startswith(AGENTS_CURSOR_PREFIX)
        or path == SKILL_CONTRACT_FILE
        or path.endswith(f"/{SKILL_CONTRACT_FILE}")
        for path in candidate_paths
    )


def is_docs_only_contract_path(path: str) -> bool:
    """Return True when the path is a canonical docs/contract surface.

    RU: Произвольный ``*.md`` под ``app/``/``core/``/и т.д. не считается docs-only
    контрактом (fail-closed в ``analysis``), чтобы не занижать envelope на runtime-деревьях.
    EN: A bare ``*.md`` under implementation trees is not a docs-only contract path
    (stays fail-closed to ``analysis``) so envelope mode cannot downshift on app/core notes.
    """

    normalized = path.strip()
    if not normalized:
        return False

    if normalized in DOCS_ONLY_ROOT_FILES:
        return True

    if normalized.startswith(DOCS_PATH_PREFIX) and normalized.endswith(".md"):
        return True

    if normalized.startswith(".github/") and normalized.endswith(".md"):
        return True

    if normalized.endswith(f"/{AGENTS_CONTRACT_FILE}") or normalized == AGENTS_CONTRACT_FILE:
        return True

    if normalized.endswith(f"/{SKILL_CONTRACT_FILE}") or normalized == SKILL_CONTRACT_FILE:
        return True

    if "/" not in normalized and normalized.endswith(".md"):
        return True

    return False


def resolve_analysis_envelope_mode(candidate_paths: Sequence[str]) -> str:
    """Return the additive envelope-mode hint for the canonical bootstrap packet.

    RU: Смешанный или runtime scope всегда fail-closed в analysis.
    EN: Mixed or runtime scope always fails closed to analysis.
    """

    normalized_paths = [path.strip() for path in candidate_paths if path.strip()]
    if not normalized_paths or requires_security_review(normalized_paths):
        return ANALYSIS_ENVELOPE_MODE
    if all(is_docs_only_contract_path(path) for path in normalized_paths):
        return DOCS_ONLY_ENVELOPE_MODE
    return ANALYSIS_ENVELOPE_MODE
