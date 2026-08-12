"""Canonical sync-policy helpers for task bootstrap.

RU: Централизует sync-policy константы и matcher-правила для bootstrap packet.
EN: Centralizes sync-policy constants and matcher rules for the bootstrap packet.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Literal, cast

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration.context_pack import compute_task_packet_id
from scripts.orchestration.design_lane_contract import canonicalize_design_blockers

REPO_ROOT = Path(__file__).resolve().parents[2]

InvariantChangeClass = Literal["parser", "validator", "guard", "authority"]

INVARIANT_CHANGE_CLASSES: tuple[InvariantChangeClass, ...] = (
    "parser",
    "validator",
    "guard",
    "authority",
)
INVARIANT_REVIEW_REQUIRED_ROLES: tuple[str, ...] = (
    "logic-agent",
    "philosophy-agent",
)
INVARIANT_REVIEW_COVERAGE_CLAIM = "explicit_plus_bounded_positive_triggers_only"
INVARIANT_REVIEW_BOUNDARY_CLASSES: tuple[str, ...] = (
    "finite_closed_world",
    "bounded_surface",
    "delegated_recognizer",
    "open_world_stop",
)
INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS: tuple[str, ...] = (
    "invariant_statement",
    "boundary_class",
    "canonical_sot",
    "completeness_claim",
    "counterexample_families",
    "fail_closed_behavior",
    "stop_condition",
    "residual_risk",
)
INVARIANT_REVIEW_V2_REQUIRED_OUTPUT_FIELDS: tuple[str, ...] = (
    *INVARIANT_REVIEW_REQUIRED_OUTPUT_FIELDS,
    "family_membership_assessment",
    "set_relation_interpretation",
    "abstraction_level",
    "root_cause_hypothesis",
    "recommended_resolution",
    "evidence_refs",
)
INVARIANT_REVIEW_RECOMMENDED_RESOLUTIONS: tuple[str, ...] = (
    "bounded_object_fix",
    "family_fix",
    "mechanism_fix",
    "authority_rescope",
    "no_change_required",
    "unknown_requires_human",
)
INVARIANT_REVIEW_STOP_CONDITION = (
    "second_materially_novel_carrier_same_open_world_invariant_requires_rescope"
)
INVARIANT_FAMILY_REPEAT_TRIGGER_RULE = "explicit_family_cardinality_gte_2"
INVARIANT_FAMILY_REVIEW_IDENTITY_SCHEMA = "task_packet_id.invariant_review.v2"
INVARIANT_REVIEW_V1_FIELDS = frozenset(
    {
        "schema_version",
        "state",
        "change_classes",
        "trigger_evidence",
        "coverage_claim",
        "required_roles",
        "boundary_classes",
        "required_output_fields",
        "stop_condition",
        "implementation_authority",
        "merge_authority",
    }
)
INVARIANT_REVIEW_V2_FIELDS = frozenset(
    {
        "schema_version",
        "state",
        "coverage_claim",
        "required_roles",
        "boundary_classes",
        "required_output_fields",
        "stop_condition",
        "family_repeat",
        "implementation_authority",
        "merge_authority",
    }
)
INVARIANT_REVIEW_FAMILY_REPEAT_FIELDS = frozenset(
    {
        "source_schema_version",
        "source_policy_version",
        "snapshot_fingerprint",
        "artifact_fingerprint",
        "idempotency_key",
        "trigger_rule",
        "membership_source",
        "repeated_families",
        "relations_touching_repeated_families",
        "unknown_findings_present",
    }
)
INVARIANT_REVIEW_AUTHORITY_PATHS: tuple[str, ...] = (
    "scripts/orchestration/task_bootstrap.py",
    "scripts/orchestration/check_merge_ready.py",
    "scripts/orchestration/check_review_threads_disposition.py",
    "scripts/orchestration/pr_review_closeout.py",
    "scripts/ci/check_pr_merge_readiness.py",
)
_INVARIANT_REVIEW_CONTROL_ROOTS: tuple[str, ...] = (
    "scripts/ci/",
    "scripts/orchestration/",
)
_INVARIANT_REVIEW_EXCLUDED_COMPONENTS = frozenset(
    {
        "artifacts",
        "build",
        "dist",
        "docs",
        "examples",
        "fixtures",
        "generated",
        "node_modules",
        "worktrees",
    }
)


@dataclass(frozen=True)
class InvariantReviewEvidence:
    """One deterministic reason for requiring an invariant review."""

    change_class: InvariantChangeClass
    source: Literal["explicit", "bounded_path_hint"]
    path: str | None = None

    def to_mapping(self) -> dict[str, str]:
        """Return a stable JSON-ready evidence row."""

        row: dict[str, str] = {
            "change_class": self.change_class,
            "source": self.source,
        }
        if self.path is not None:
            row["path"] = self.path
        return row


@dataclass(frozen=True)
class InvariantReviewDecision:
    """Bounded invariant-review classification for one task scope."""

    change_classes: tuple[InvariantChangeClass, ...]
    trigger_evidence: tuple[InvariantReviewEvidence, ...]

    @property
    def required(self) -> bool:
        """Return whether the bounded classifier found any review class."""

        return bool(self.change_classes)

    @property
    def fingerprint(self) -> str:
        """Return the stable identity input for the normalized class set."""

        return ",".join(self.change_classes)


def compute_invariant_family_review_packet_id(
    *,
    goal: str,
    task_class: str,
    domain: str,
    candidate_paths: list[str] | tuple[str, ...],
    requested_agents: list[str] | tuple[str, ...],
    pr_phase: str,
    design_lane_mode: str,
    design_lane_contract: dict[str, Any],
    creative_learning_hints_fingerprint: str,
    artifact_fingerprint: str,
    invariant_review_projection: dict[str, Any],
) -> str:
    """Bind the exact closed v2 projection into the existing packet-id frame."""

    canonical_design_contract = dict(design_lane_contract)
    canonical_design_contract["blockers"] = canonicalize_design_blockers(
        list(design_lane_contract.get("blockers", ()))
    )
    design_fingerprint = json.dumps(
        {
            "design_lane_mode": design_lane_mode,
            "design_lane_contract": canonical_design_contract,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    base_packet_id = compute_task_packet_id(
        goal=goal,
        task_class=task_class,
        domain=domain,
        candidate_paths=candidate_paths,
        requested_agents=requested_agents,
        pr_phase=pr_phase,
        design_fingerprint=design_fingerprint,
        creative_learning_hints_fingerprint=creative_learning_hints_fingerprint,
    )
    framed_fingerprint = str(
        fingerprint_payload(
            {
                "base_task_packet_id": base_packet_id,
                "identity_schema": INVARIANT_FAMILY_REVIEW_IDENTITY_SCHEMA,
                "artifact_fingerprint": artifact_fingerprint,
                "trigger_rule": INVARIANT_FAMILY_REPEAT_TRIGGER_RULE,
                "invariant_review_projection_fingerprint": fingerprint_payload(
                    invariant_review_projection
                ),
            }
        )
    )
    return framed_fingerprint.removeprefix("sha256:")[:12]


def _normalize_invariant_review_path(raw_path: str) -> str:
    """Return a strict repo-relative POSIX path for bounded matching."""

    if not isinstance(raw_path, str):
        raise ValueError("invariant review paths must be strings")
    candidate_text = raw_path.strip()
    if not candidate_text:
        return ""
    if any(ord(character) < 32 or ord(character) == 127 for character in candidate_text):
        raise ValueError("invariant review paths must not contain control characters")
    if "\\" in candidate_text or "//" in candidate_text:
        raise ValueError("invariant review paths must use unambiguous POSIX separators")
    if candidate_text.startswith("~") or re.match(r"^[A-Za-z]:/", candidate_text):
        raise ValueError("invariant review paths must stay under the repository root")

    candidate = Path(candidate_text)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError as exc:
            raise ValueError("invariant review paths must stay under the repository root") from exc

    normalized = PurePosixPath(candidate_text)
    if ".." in normalized.parts:
        raise ValueError(
            "invariant review paths: path must stay inside repo; parent traversal is forbidden"
        )
    normalized_text = normalized.as_posix()
    while normalized_text.startswith("./"):
        normalized_text = normalized_text[2:]
    return "" if normalized_text == "." else normalized_text


def _bounded_invariant_classes_for_path(
    normalized_path: str,
) -> tuple[InvariantChangeClass, ...]:
    """Return bounded positive matches without claiming semantic completeness."""

    path = PurePosixPath(normalized_path)
    if any(component in _INVARIANT_REVIEW_EXCLUDED_COMPONENTS for component in path.parts):
        return ()

    matches: set[InvariantChangeClass] = set()
    if normalized_path in INVARIANT_REVIEW_AUTHORITY_PATHS:
        matches.add("authority")

    if normalized_path.startswith("tests/guards/"):
        if path.suffix == ".py" and path.name != "__init__.py":
            matches.add("guard")
    elif any(normalized_path.startswith(prefix) for prefix in _INVARIANT_REVIEW_CONTROL_ROOTS):
        if path.suffix == ".py":
            stem = path.stem
            if stem.startswith("parser_") or stem.endswith("_parser"):
                matches.add("parser")
            if (
                stem.startswith("validator_")
                or stem.endswith("_validator")
                or stem.endswith("_validation")
                or stem.startswith("check_")
            ):
                matches.add("validator")
            if stem.startswith("guard_") or stem.endswith("_guard"):
                matches.add("guard")

    return tuple(
        change_class for change_class in INVARIANT_CHANGE_CLASSES if change_class in matches
    )


def classify_invariant_review(
    *,
    candidate_paths: Sequence[str],
    explicit_classes: Sequence[str] = (),
) -> InvariantReviewDecision:
    """Classify the closed enum plus bounded path hints for pre-fix review."""

    explicit_set: set[InvariantChangeClass] = set()
    for raw_change_class in explicit_classes:
        if (
            not isinstance(raw_change_class, str)
            or raw_change_class not in INVARIANT_CHANGE_CLASSES
        ):
            supported = ", ".join(INVARIANT_CHANGE_CLASSES)
            raise ValueError(
                f"Unsupported invariant change class: {raw_change_class!r}. Supported: {supported}"
            )
        explicit_set.add(cast(InvariantChangeClass, raw_change_class))

    normalized_paths = sorted(
        {
            normalized_path
            for raw_path in candidate_paths
            if (normalized_path := _normalize_invariant_review_path(raw_path))
        }
    )
    evidence: list[InvariantReviewEvidence] = [
        InvariantReviewEvidence(change_class=change_class, source="explicit")
        for change_class in INVARIANT_CHANGE_CLASSES
        if change_class in explicit_set
    ]
    for normalized_path in normalized_paths:
        for change_class in _bounded_invariant_classes_for_path(normalized_path):
            evidence.append(
                InvariantReviewEvidence(
                    change_class=change_class,
                    source="bounded_path_hint",
                    path=normalized_path,
                )
            )

    matched_classes = {evidence_row.change_class for evidence_row in evidence}
    return InvariantReviewDecision(
        change_classes=tuple(
            change_class
            for change_class in INVARIANT_CHANGE_CLASSES
            if change_class in matched_classes
        ),
        trigger_evidence=tuple(evidence),
    )


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


@dataclass(frozen=True)
class PrivilegedReviewSurface:
    """Reviewed privileged-surface matcher row."""

    surface_class: str
    reason: str
    prefixes: tuple[str, ...] = ()
    exact_paths: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    regexes: tuple[str, ...] = ()


PRIVILEGED_REVIEW_SURFACES: tuple[PrivilegedReviewSurface, ...] = (
    PrivilegedReviewSurface(
        surface_class="repo_agent_contracts",
        reason="agent-contract",
        exact_paths=("AGENTS.md", "RUNBOOK_AGENT.md"),
        suffixes=("/AGENTS.md",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_workflows",
        reason=".github/workflows/",
        prefixes=(".github/workflows/",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_actions",
        reason=".github/actions/",
        prefixes=(".github/actions/",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_agent_control",
        reason=".github/agents/",
        prefixes=(".github/agents/",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_prompt_control",
        reason=".github/prompts/",
        prefixes=(".github/prompts/",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_support_scripts",
        reason=".github/scripts/",
        prefixes=(".github/scripts/",),
    ),
    PrivilegedReviewSurface(
        surface_class="github_codeowners",
        reason="CODEOWNERS",
        exact_paths=(".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"),
    ),
    PrivilegedReviewSurface(
        surface_class="cursor_and_local_hook_control",
        reason="local-agent-tooling-control",
        prefixes=(
            ".agents/skills/",
            ".cursor/agents/",
            ".cursor/commands/",
            ".cursor/rules/",
            ".githooks/",
            "tests/guards/",
            "tools/agentguard/",
            "tools/codex_skills/",
            "tools/cybersecurity_skills/",
        ),
        exact_paths=(
            ".cursor/mcp.json.example",
            ".github/pull_request_template.md",
            ".kimi/mcp.json.example",
            ".vscode/extensions.json",
            "docs/security/TOOLING_SURFACE_POLICY.md",
            "docs/security/vscode_extensions_allowlist.txt",
            "mcp-config.json",
            "mcp-setup.sh",
            "mcp_pulseplate_server.py",
            "opencode.json",
            "setup_custom_mcp.py",
            "tests/test_install_codex_skills.py",
            "update_api_key.py",
        ),
        regexes=(r"\.github/PULL_REQUEST_TEMPLATE/[^/]+\.md",),
    ),
    PrivilegedReviewSurface(
        surface_class="ios_fastlane",
        reason="ios/fastlane/",
        prefixes=("ios/fastlane/",),
    ),
    PrivilegedReviewSurface(
        surface_class="orchestration_scripts",
        reason="scripts/orchestration/",
        prefixes=("scripts/orchestration/",),
    ),
    PrivilegedReviewSurface(
        surface_class="merge_governance_scripts",
        reason="scripts/ci/",
        prefixes=("scripts/ci/",),
    ),
    PrivilegedReviewSurface(
        surface_class="metatron_lab_scripts",
        reason="scripts/metatron_lab/",
        prefixes=("scripts/metatron_lab/",),
    ),
    PrivilegedReviewSurface(
        surface_class="release_scripts",
        reason="scripts/release/",
        prefixes=("scripts/release/",),
        exact_paths=(
            "scripts/deploy.sh",
            "scripts/diagnose_web.sh",
            "scripts/devcontainer/smoke.sh",
            "scripts/hooks/repo_python.sh",
            "scripts/install_codex_skills.sh",
            "scripts/opencode/run_pulseplate_mcp.sh",
            "scripts/ops/postgres_backup.sh",
            "scripts/ops/postgres_restore.sh",
            "scripts/redeploy_caddy.sh",
            "scripts/run-backend-tests-pre-commit.sh",
            "scripts/validate-ci-environment.sh",
            "scripts/verify_codex_skills_install.py",
        ),
        regexes=(r"scripts/(?:ci|deploy)_[A-Za-z0-9_.-]+\.sh",),
    ),
    PrivilegedReviewSurface(
        surface_class="orchestration_governance_docs",
        reason="docs/orchestration/",
        prefixes=("docs/orchestration/",),
    ),
    PrivilegedReviewSurface(
        surface_class="review_governance_docs",
        reason="docs/review/",
        prefixes=("docs/review/",),
    ),
    PrivilegedReviewSurface(
        surface_class="deploy_and_image_config",
        reason="deploy-or-image-config",
        prefixes=("deploy/", ".devcontainer/", "appstore/fitchef/", "deploy/metatron-lab/"),
        exact_paths=(
            "Dockerfile",
            ".dockerignore",
            "docker-compose.yaml",
            "docker-compose.yml",
            "frontend/.dockerignore",
            "frontend/Dockerfile.caddy-spa",
            "frontend/wrangler.toml",
            "worker.js",
            "wrangler.toml",
        ),
        regexes=(
            r"Dockerfile(?:\.[A-Za-z0-9_.-]+)?$",
            r"docker-compose(?:\.[A-Za-z0-9_.-]+)?\.ya?ml$",
        ),
    ),
    PrivilegedReviewSurface(
        surface_class="security_scan_policy",
        reason="security-scan-policy",
        prefixes=("trivy/",),
        exact_paths=(".trivyignore",),
    ),
    PrivilegedReviewSurface(
        surface_class="dependency_and_hook_config",
        reason="dependency-or-hook-config",
        exact_paths=(
            ".pre-commit-config.yaml",
            ".pre-commit-config.yml",
            ".github/dependabot.yaml",
            ".github/dependabot.yml",
            ".github/actionlint.yaml",
            ".github/actionlint.yml",
            ".github/pull_request_template.md",
            ".bandit",
            ".bandit.yaml",
            ".coveragerc",
            ".coderabbit.yaml",
            ".env.example",
            ".flake8",
            ".gitmodules",
            ".markdownlint.json",
            ".nvmrc",
            ".python-version",
            ".ruby-version",
            ".secrets.baseline",
            ".sourcery.yaml",
            ".tool-versions",
            ".yamllint",
            "Makefile",
            "alembic.ini",
            "codecov.yml",
            "codecov.yaml",
            "constraints.txt",
            "constraints-dev.txt",
            "frontend/package.json",
            "frontend/package-lock.json",
            "Gemfile",
            "Gemfile.lock",
            "ios/Gemfile",
            "ios/Gemfile.lock",
            "ios/Package.swift",
            "ios/Package.resolved",
            "ios/PulsePlate.xcodeproj/project.pbxproj",
            "ios/PulsePlate.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved",
            "ios/PulsePlate.xcodeproj/xcshareddata/swiftpm/Package.resolved",
            "ios/PulsePlate.xcodeproj/xcshareddata/xcschemes/PulsePlate.xcscheme",
            "ios/PulsePlate.xcworkspace/xcshareddata/swiftpm/Package.swift",
            "ios/PulsePlate/Info-Release.plist",
            "ios/PulsePlate/PulsePlate.entitlements",
            "ios/PulsePlate/PrivacyInfo.xcprivacy",
            "package.json",
            "package-lock.json",
            "Package.resolved",
            "Package.swift",
            "Pipfile",
            "Pipfile.lock",
            "pnpm-lock.yaml",
            "poetry.lock",
            "pyproject.toml",
            "requirements.in",
            "requirements.txt",
            "requirements-dev.txt",
            "scripts/business_collateral/package.json",
            "tests/security/_api_authz_contracts.py",
            "tests/security/test_api_authz_contract_static.py",
            "tests/test_repo_policy_guards.py",
            "skills-lock.json",
            "uv.lock",
            "yarn.lock",
        ),
        suffixes=(
            "/.pre-commit-config.yaml",
            "/.pre-commit-config.yml",
            "/.github/dependabot.yaml",
            "/.github/dependabot.yml",
            "/constraints.txt",
            "/Pipfile",
            "/Pipfile.lock",
            "/pnpm-lock.yaml",
            "/poetry.lock",
            "/pyproject.toml",
            "/skills-lock.json",
            "/uv.lock",
            "/yarn.lock",
        ),
        regexes=(
            r"(^|.*/)requirements[-A-Za-z0-9_]*\.(in|txt)$",
            r"(^|.*/)constraints[-A-Za-z0-9_]*\.txt$",
            r"ios/PulsePlate/[^/]+/InfoPlist\.strings",
        ),
    ),
)

PRIVILEGED_REVIEW_PREFIXES: tuple[str, ...] = tuple(
    prefix for surface in PRIVILEGED_REVIEW_SURFACES for prefix in surface.prefixes
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


def _normalize_review_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _contains_parent_traversal(path: str) -> bool:
    return any(part == ".." for part in path.split("/"))


def matches_any_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    """Return True when a path matches a canonical prefix exactly or by subtree.

    RU: Совпадение считается валидным и для корня, и для вложенного пути.
    EN: A match is valid for both the root directory and any nested path.
    """

    normalized = _normalize_review_path(path)
    if _contains_parent_traversal(normalized):
        return False
    return any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in prefixes
    )


def _matches_privileged_surface(path: str, surface: PrivilegedReviewSurface) -> bool:
    normalized = _normalize_review_path(path)
    if not normalized or _contains_parent_traversal(normalized):
        return False
    if normalized in surface.exact_paths:
        return True
    if any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in surface.prefixes
    ):
        return True
    if any(re.fullmatch(pattern, normalized) for pattern in surface.regexes):
        return True
    return any(normalized.endswith(suffix) for suffix in surface.suffixes)


def privileged_review_surface_matches(candidate_paths: Sequence[str]) -> tuple[str, ...]:
    """Return stable privileged-surface reason labels matched by candidate paths."""

    matches: list[str] = []
    for surface in PRIVILEGED_REVIEW_SURFACES:
        if any(_matches_privileged_surface(path, surface) for path in candidate_paths):
            matches.append(surface.reason)
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
