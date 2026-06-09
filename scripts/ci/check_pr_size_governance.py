#!/usr/bin/env python3
"""PR-size governance gate for Tier 1 CI/CD.

RU: Проверяет размер PR по текущей tiered file-count policy.
EN: Enforces the tiered PR-scope policy using changed-file counts and PR-body proof.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess  # nosec B404: subprocess is required for bounded local git diff execution (remove-by: 2026-09-30, ref: PR3-risk-topology)
import sys
import re
import shutil
import os
import urllib.error
import urllib.parse
import urllib.request

_REPO_ROOT_OVERRIDE = os.environ.get("PULSEPLATE_SIZE_GOVERNANCE_REPO_ROOT", "").strip()
REPO_ROOT = Path(_REPO_ROOT_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
MICRO_MAX_FILES = 5
STANDARD_MAX_FILES = 20
STANDARD_SPLIT_JUSTIFICATION_FILES = 15
FRONTEND_MVP_MAX_FILES = 30
PRIVILEGED_TARGET_FILES = 10
PRIVILEGED_HARD_CAP_FILES = 15
EMERGENCY_MAX_FILES = 30
GIT_BINARY = shutil.which("git")
SPLIT_JUSTIFICATION_INLINE_PATTERN = re.compile(
    r"(?im)^(?:[-*]\s*)?(?:\*\*)?split justification:\s*(\S.+)$",
)
SPLIT_JUSTIFICATION_HEADING_PATTERN = re.compile(
    r"(?im)^(?:##+\s*|[*]{0,2})?(?:pr size justification|split justification)\s*$",
)
SPLIT_JUSTIFICATION_TEMPLATE_PLACEHOLDERS = {
    "why this pr cannot be split safely:",
    "what invariant, contract, or rollout constraint requires one pr:",
    "what follow-up prs remain after this large change:",
    "n/a",
    "na",
    "none",
    "placeholder",
    "tbd",
    "todo",
}
NEGATED_APPROVAL_PATTERN = re.compile(
    r"(?im)\b(no|not|without)\s+[^\n]{0,40}(approved|approval|exception)\b"
)
APPROVED_LINE_SUFFIX_RE = r"(?:\s+(?:for|because|due to|to)\s+[^\n.;]*)?\s*[.;]?\s*$"
REQUIRED_STANDARD_SECTIONS = ("scope", "out of scope", "tests")
PRIVILEGED_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
    "scripts/ci/",
    "scripts/orchestration/",
    "trivy/",
    "docs/security/",
)
PRIVILEGED_EXACT_PATHS = {
    ".trivyignore",
    "Dockerfile",
    "Makefile",
    "AGENTS.md",
    "RUNBOOK_AGENT.md",
}
BACKEND_API_AI_PREFIXES = (
    "app/",
    "core/",
    "providers/",
    "alembic/",
)
BACKEND_API_AI_EXACT_PATHS = {
    "legacy_app.py",
    "mcp_pulseplate_server.py",
}

TRUSTED_APPROVAL_LABELS_RAW = {
    "operator": ("scope/operator-approved", "operator-approved"),
    "emergency": ("scope/emergency-approved",),
    "privileged": ("scope/privileged-approved",),
    "frontend_mvp": ("scope/frontend-mvp-approved",),
    "frontend_backend_mix": ("scope/frontend-backend-mix-approved",),
}


def _normalize_approval_label(label: str) -> str:
    """Return canonical lowercase label text for trusted approval matching."""
    return re.sub(r"\s+", " ", label.strip().casefold())


TRUSTED_APPROVAL_LABELS = {
    approval_key: frozenset(_normalize_approval_label(label) for label in labels)
    for approval_key, labels in TRUSTED_APPROVAL_LABELS_RAW.items()
}


def _fetch_pr_metadata_from_api(pr_number: int, repo_full_name: str) -> dict[str, object]:
    """Fetch PR metadata from GitHub API with optional token fallback.

    Local CI execution should prefer payload body, but event payloads can omit this field
    or labels after certain synchronization/edit events. API fallback preserves deterministic
    size governance checks without changing gate semantics.
    """

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        return {}

    owner, repo = repo_full_name.split("/", maxsplit=1)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/pulls/{pr_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pulseplate-size-governance",
        },
    )

    with urllib.request.urlopen(  # nosec B310: fallback PR body fetch is read-only API access for size governance; remove-by: 2026-10-31, ref: PR3-risk-topology
        request,
        timeout=10,
    ) as response:
        payload = response.read().decode("utf-8")
    pull_request = json.loads(payload)
    if not isinstance(pull_request, dict):
        return {}
    return pull_request


def parse_numstat_output(numstat_output: str) -> tuple[int, int]:
    """Return total changed lines and counted files from git --numstat output."""
    total_changed_lines, counted_files, _changed_files = parse_numstat_details(numstat_output)
    return total_changed_lines, counted_files


def parse_numstat_details(numstat_output: str) -> tuple[int, int, list[str]]:
    """Return changed-line count, counted-file count, and changed file paths."""
    total_changed_lines = 0
    counted_files = 0
    changed_files: list[str] = []
    for raw_line in numstat_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", maxsplit=2)
        if len(parts) != 3:
            continue
        added_raw, deleted_raw, path = parts
        if added_raw != "-" and deleted_raw != "-":
            total_changed_lines += int(added_raw) + int(deleted_raw)
        counted_files += 1
        changed_files.append(path)
    return total_changed_lines, counted_files, changed_files


def classify_pr_size(total_changed_lines: int) -> str:
    """Classify PR size according to Tier 1 governance buckets."""
    if total_changed_lines <= 299:
        return "normal"
    if total_changed_lines <= 800:
        return "warning"
    return "requires_split_justification"


def _normalize_path(path: str) -> str:
    normalized = path.strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_privileged_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized in PRIVILEGED_EXACT_PATHS or normalized.startswith(PRIVILEGED_PREFIXES)


def _is_backend_api_ai_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized in BACKEND_API_AI_EXACT_PATHS:
        return True
    return normalized.startswith(BACKEND_API_AI_PREFIXES)


def _is_closeout_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == "docs/roadmap/BACKLOG_LEDGER.md":
        return True
    if re.fullmatch(r"docs/review/PR_\d+_FIXED_MAPPING\.md", normalized):
        return True
    return normalized.startswith(("docs/runbooks/", "docs/review/")) and normalized.endswith(".md")


def _is_governance_doc_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized in {"AGENTS.md", "RUNBOOK_AGENT.md"}:
        return True
    return normalized.startswith(
        ("docs/orchestration/", "docs/policy/", "docs/security/", "docs/review/")
    )


def _has_markdown_section(pr_body: str, section_name: str) -> bool:
    escaped_name = re.escape(section_name).replace(r"\ ", r"\s+")
    normalized_body = re.sub(r"<!--.*?-->", "", pr_body or "", flags=re.DOTALL)
    return bool(re.search(rf"(?im)^##\s+{escaped_name}\s*$", normalized_body))


def missing_standard_sections(pr_body: str) -> list[str]:
    """Return required standard-governance sections missing from the PR body."""
    missing: list[str] = []
    for section in REQUIRED_STANDARD_SECTIONS:
        if not _has_markdown_section(pr_body, section):
            missing.append(section)
    return missing


def _has_trusted_approval(trusted_approvals: set[str] | None, approval_key: str) -> bool:
    """Return True when a trusted GitHub-controlled approval label is present."""
    return bool((trusted_approvals or set()) & TRUSTED_APPROVAL_LABELS[approval_key])


def _body_has_approval_line(pr_body: str, approval_label: str) -> bool:
    """Return True when the PR body records the expected approval line."""
    normalized_body = pr_body or ""
    match = re.search(
        rf"(?im)^{re.escape(approval_label)}:\s*approved\b{APPROVED_LINE_SUFFIX_RE}",
        normalized_body,
    )
    return bool(match and not NEGATED_APPROVAL_PATTERN.search(match.group(0)))


def has_operator_approval(pr_body: str, trusted_approvals: set[str] | None = None) -> bool:
    """Return True when PR body proof is backed by a trusted operator label."""
    return _body_has_approval_line(pr_body, "operator approval") and _has_trusted_approval(
        trusted_approvals,
        "operator",
    )


def has_emergency_exception(pr_body: str, trusted_approvals: set[str] | None = None) -> bool:
    """Return True when PR body proof is backed by trusted emergency approval."""
    return (
        has_operator_approval(pr_body, trusted_approvals)
        and _body_has_approval_line(pr_body, "emergency exception")
        and _has_trusted_approval(trusted_approvals, "emergency")
    )


def has_privileged_scope_exception(
    pr_body: str,
    trusted_approvals: set[str] | None = None,
) -> bool:
    """Return True when PR body proof is backed by trusted privileged approval."""
    return (
        has_operator_approval(pr_body, trusted_approvals)
        and _body_has_approval_line(pr_body, "privileged scope exception")
        and _has_trusted_approval(trusted_approvals, "privileged")
    )


def has_frontend_backend_mix_approval(
    pr_body: str,
    trusted_approvals: set[str] | None = None,
) -> bool:
    """Return True when PR body proof is backed by trusted frontend/backend approval."""
    return (
        has_operator_approval(pr_body, trusted_approvals)
        and _body_has_approval_line(pr_body, "frontend/backend mix approval")
        and _has_trusted_approval(trusted_approvals, "frontend_backend_mix")
    )


def has_frontend_mvp_approval(
    pr_body: str,
    trusted_approvals: set[str] | None = None,
) -> bool:
    """Return True when PR body proof is backed by trusted frontend MVP approval."""
    return (
        has_operator_approval(pr_body, trusted_approvals)
        and _body_has_approval_line(pr_body, "frontend vertical mvp approval")
        and _has_trusted_approval(trusted_approvals, "frontend_mvp")
    )


def has_mixed_frontend_backend_runtime(changed_files: list[str]) -> bool:
    """Return True when frontend files mix with backend/API/AI runtime files."""
    has_frontend = any(_normalize_path(path).startswith("frontend/") for path in changed_files)
    has_backend_api_ai = any(_is_backend_api_ai_path(path) for path in changed_files)
    return has_frontend and has_backend_api_ai


def classify_pr_scope(
    *,
    counted_files: int,
    changed_files: list[str],
    pr_body: str,
    trusted_approvals: set[str] | None = None,
) -> str:
    """Classify the PR under the current file-count scope policy."""
    if any(_is_privileged_path(path) for path in changed_files):
        return "privileged_ci_security_workflow"
    has_frontend = any(_normalize_path(path).startswith("frontend/") for path in changed_files)
    if has_frontend and (
        counted_files > STANDARD_MAX_FILES
        or has_frontend_mvp_approval(pr_body, trusted_approvals)
        or has_mixed_frontend_backend_runtime(changed_files)
    ):
        return "frontend_vertical_mvp"
    if counted_files <= MICRO_MAX_FILES:
        return "micro"
    return "standard_governance_design"


def normalize_split_justification_candidate(candidate_text: str) -> str:
    """Return a normalized split-justification line for placeholder comparison."""
    normalized = re.sub(r"\s+", " ", candidate_text.strip()).casefold()
    return re.sub(r"^(?:[-*]\s*)", "", normalized)


def extract_markdown_heading_level(line: str) -> int:
    """Return markdown heading depth for a line, or zero when it is not a heading."""
    stripped = line.lstrip()
    return len(stripped) - len(stripped.lstrip("#")) if stripped.startswith("#") else 0


def has_split_justification(pr_body: str) -> bool:
    """Return True when the PR body contains an explicit split-justification block."""
    normalized_body = re.sub(r"<!--.*?-->", "", pr_body or "", flags=re.DOTALL)
    inline_match = SPLIT_JUSTIFICATION_INLINE_PATTERN.search(normalized_body)
    if inline_match:
        inline_text = normalize_split_justification_candidate(inline_match.group(1)).strip("* ")
        return (
            bool(inline_text)
            and bool(re.search(r"[a-z0-9]", inline_text, flags=re.IGNORECASE))
            and inline_text not in SPLIT_JUSTIFICATION_TEMPLATE_PLACEHOLDERS
        )

    lines = normalized_body.splitlines()
    for index, line in enumerate(lines):
        if not SPLIT_JUSTIFICATION_HEADING_PATTERN.match(line.strip()):
            continue
        heading_level = extract_markdown_heading_level(line)
        for candidate in lines[index + 1 :]:
            candidate_text = candidate.strip()
            if not candidate_text:
                continue
            if candidate_text.startswith("#"):
                candidate_heading_level = extract_markdown_heading_level(candidate_text)
                if heading_level and candidate_heading_level > heading_level:
                    continue
                return False
            if (
                normalize_split_justification_candidate(candidate_text)
                in SPLIT_JUSTIFICATION_TEMPLATE_PLACEHOLDERS
            ):
                continue
            return True
        return False
    return False


def evaluate_pr_size_policy(
    *,
    total_changed_lines: int,
    counted_files: int,
    pr_body: str,
    changed_files: list[str] | None = None,
    trusted_approvals: set[str] | None = None,
) -> tuple[int, list[str]]:
    """Evaluate scope policy and return exit code plus deterministic terminal lines."""
    changed_files = changed_files or []
    category = classify_pr_scope(
        counted_files=counted_files,
        changed_files=changed_files,
        pr_body=pr_body,
        trusted_approvals=trusted_approvals,
    )
    legacy_loc_bucket = classify_pr_size(total_changed_lines)
    lines = [
        f"PR scope category: {category}",
        f"Changed lines: {total_changed_lines}",
        f"Counted files: {counted_files}",
        f"Line-count signal: {legacy_loc_bucket} (advisory; file-count policy is authoritative)",
    ]

    if counted_files > EMERGENCY_MAX_FILES:
        if has_emergency_exception(pr_body, trusted_approvals):
            lines.append(
                "PR scope governance: OK (>30 files) because an operator-approved emergency exception is documented.",
            )
            return 0, lines
        lines.append("PR scope governance: FAIL (>30 files without emergency/operator exception).")
        lines.append("Category: oversized")
        lines.append("Required section missing: emergency operator exception")
        lines.append(
            "How to fix: split the PR, or document an explicit operator-approved emergency exception in the PR body.",
        )
        return 1, lines

    if category == "micro":
        if any(_is_governance_doc_path(path) for path in changed_files):
            missing_sections = missing_standard_sections(pr_body)
            if missing_sections:
                lines.append(
                    "PR scope governance: FAIL (micro governance/security PR body sections missing)."
                )
                lines.append("Category: micro")
                lines.extend(
                    f"Required section missing: ## {section.title()}"
                    for section in missing_sections
                )
                lines.append(
                    "How to fix: add ## Scope, ## Out of scope, and ## Tests sections for governance/security docs, or keep micro PRs to trivial non-governance changes.",
                )
                return 1, lines
        lines.append(f"PR scope governance: OK (micro PR <= {MICRO_MAX_FILES} files).")
        return 0, lines

    if category == "privileged_ci_security_workflow":
        if any(_normalize_path(path).startswith("frontend/") for path in changed_files) and not (
            has_emergency_exception(pr_body, trusted_approvals)
            or has_frontend_backend_mix_approval(pr_body, trusted_approvals)
        ):
            lines.append(
                "PR scope governance: FAIL (privileged CI/security/workflow PR mixes with frontend product implementation without explicit approved exception).",
            )
            lines.append("Category: privileged_ci_security_workflow")
            lines.append(
                "How to fix: split frontend product implementation from privileged CI/security/workflow changes or document an explicit operator-approved exception."
            )
            return 1, lines
        if counted_files > PRIVILEGED_HARD_CAP_FILES and not (
            has_emergency_exception(pr_body, trusted_approvals)
            or has_privileged_scope_exception(pr_body, trusted_approvals)
        ):
            lines.append(
                f"PR scope governance: FAIL (privileged CI/security/workflow PR has {counted_files} files; hard cap is {PRIVILEGED_HARD_CAP_FILES} without operator-approved exception).",
            )
            lines.append("Category: privileged_ci_security_workflow")
            lines.append("Required section missing: operator-approved privileged scope exception")
            lines.append(
                "How to fix: split the privileged PR to <=15 files or document an explicit operator-approved exception.",
            )
            return 1, lines
        if counted_files > PRIVILEGED_TARGET_FILES:
            lines.append(
                f"PR scope governance: WARNING (privileged PR target is <= {PRIVILEGED_TARGET_FILES} files; hard cap is {PRIVILEGED_HARD_CAP_FILES}).",
            )
        lines.append("PR scope governance: OK (privileged CI/security/workflow policy).")
        return 0, lines

    if category == "frontend_vertical_mvp":
        if counted_files > FRONTEND_MVP_MAX_FILES:
            lines.append(
                f"PR scope governance: FAIL (frontend vertical MVP PR exceeds {FRONTEND_MVP_MAX_FILES} files).",
            )
            lines.append("Category: frontend_vertical_mvp")
            lines.append("How to fix: split the PR into smaller vertical flow increments.")
            return 1, lines
        missing: list[str] = []
        if not has_frontend_mvp_approval(pr_body, trusted_approvals):
            missing.append("operator approval for frontend vertical MVP")
        if not has_split_justification(pr_body):
            missing.append("split justification")
        if missing:
            lines.append("PR scope governance: FAIL (frontend vertical MVP proof missing).")
            lines.append("Category: frontend_vertical_mvp")
            lines.extend(f"Required section missing: {item}" for item in missing)
            lines.append(
                "How to fix: add operator approval for one vertical user flow and a non-template Split Justification.",
            )
            return 1, lines
        if has_mixed_frontend_backend_runtime(changed_files) and not (
            has_emergency_exception(pr_body, trusted_approvals)
            or has_frontend_backend_mix_approval(pr_body, trusted_approvals)
        ):
            lines.append(
                "PR scope governance: FAIL (frontend MVP mixes frontend UI with backend/API/AI runtime without explicit approved exception).",
            )
            lines.append("Category: frontend_vertical_mvp")
            lines.append(
                "How to fix: split backend/API/AI runtime changes or document `Frontend/backend mix approval: approved` with operator approval."
            )
            return 1, lines
        lines.append(
            f"PR scope governance: OK (frontend vertical MVP <= {FRONTEND_MVP_MAX_FILES} files with approval and split justification).",
        )
        return 0, lines

    missing_sections = missing_standard_sections(pr_body)
    if missing_sections:
        lines.append(
            "PR scope governance: FAIL (standard governance/design PR body sections missing)."
        )
        lines.append("Category: standard_governance_design")
        lines.extend(
            f"Required section missing: ## {section.title()}" for section in missing_sections
        )
        lines.append(
            "How to fix: add ## Scope, ## Out of scope, and ## Tests sections to the PR body.",
        )
        return 1, lines

    if counted_files > STANDARD_MAX_FILES:
        lines.append(
            f"PR scope governance: FAIL (standard governance/design PR has {counted_files} files; cap is {STANDARD_MAX_FILES}).",
        )
        lines.append("Category: standard_governance_design")
        lines.append(
            "How to fix: split the PR or reclassify as an approved frontend vertical MVP when the scope is one frontend user flow.",
        )
        return 1, lines

    if counted_files > STANDARD_SPLIT_JUSTIFICATION_FILES and not has_split_justification(pr_body):
        lines.append(
            f"PR scope governance: FAIL (standard governance/design PR has >{STANDARD_SPLIT_JUSTIFICATION_FILES} files without split justification).",
        )
        lines.append("Category: standard_governance_design")
        lines.append("Required section missing: ## Split Justification")
        lines.append(
            "How to fix: add a non-template ## Split Justification section or split the PR to <=15 files.",
        )
        return 1, lines

    closeout_count = sum(1 for path in changed_files if _is_closeout_path(path))
    if closeout_count:
        lines.append(
            f"Closeout files allowed in same PR: {closeout_count} (counted for visibility).",
        )
    lines.append(
        f"PR scope governance: OK (standard governance/design PR <= {STANDARD_MAX_FILES} files)."
    )
    return 0, lines


def collect_numstat_output(*, base_sha: str, head_sha: str) -> str:
    """Collect git --numstat output between two revisions."""
    if GIT_BINARY is None:
        raise RuntimeError("git executable not found in PATH")
    result = subprocess.run(  # nosec B603: fixed git argv without shell for local CI routing only (remove-by: 2026-09-30, ref: PR3-risk-topology)
        [
            GIT_BINARY,
            "diff",
            "--numstat",
            f"{base_sha}...{head_sha}",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def collect_changed_files(*, base_sha: str, head_sha: str) -> list[str]:
    """Collect changed paths between two revisions, including binary and rename-only files."""
    if GIT_BINARY is None:
        raise RuntimeError("git executable not found in PATH")
    result = subprocess.run(  # nosec B603: fixed git argv without shell for local CI routing only (remove-by: 2026-09-30, ref: PR3-risk-topology)
        [
            GIT_BINARY,
            "diff",
            "--name-status",
            "-z",
            "--diff-filter=ACDMRT",
            f"{base_sha}...{head_sha}",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=False,
    )
    tokens = [
        token.decode("utf-8", errors="replace") for token in result.stdout.split(b"\0") if token
    ]
    changed_files: list[str] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if status.startswith(("R", "C")):
            if index + 1 >= len(tokens):
                break
            old_path = tokens[index]
            new_path = tokens[index + 1]
            changed_files.extend([old_path, new_path])
            index += 2
            continue
        if index >= len(tokens):
            break
        changed_files.append(tokens[index])
        index += 1
    return list(dict.fromkeys(changed_files))


def extract_pr_body(event_path: Path) -> str:
    """Extract PR body from a GitHub event payload."""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    body = pull_request.get("body")
    if isinstance(body, str):
        return body

    repository = payload.get("repository")
    repo_full_name = repository.get("full_name") if isinstance(repository, dict) else None
    if not isinstance(repo_full_name, str) or "/" not in repo_full_name:
        return ""

    number = pull_request.get("number")
    if not isinstance(number, int):
        return ""

    try:
        pull_request = _fetch_pr_metadata_from_api(number, repo_full_name)
    except (ValueError, KeyError, urllib.error.URLError):
        return ""
    body = pull_request.get("body")
    return body if isinstance(body, str) else ""


def extract_trusted_approvals(event_path: Path) -> set[str]:
    """Extract trusted approval labels from a GitHub pull_request event payload."""
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, dict):
        return set()
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return set()
    labels = pull_request.get("labels")
    if not isinstance(labels, list):
        repository = payload.get("repository")
        repo_full_name = repository.get("full_name") if isinstance(repository, dict) else None
        number = pull_request.get("number")
        if not isinstance(repo_full_name, str) or "/" not in repo_full_name:
            return set()
        if not isinstance(number, int):
            return set()
        try:
            live_pull_request = _fetch_pr_metadata_from_api(number, repo_full_name)
        except (ValueError, KeyError, urllib.error.URLError):
            return set()
        labels = live_pull_request.get("labels")
        if not isinstance(labels, list):
            return set()

    trusted_approvals: set[str] = set()
    for label in labels:
        if not isinstance(label, dict):
            continue
        name = label.get("name")
        if isinstance(name, str):
            trusted_approvals.add(_normalize_approval_label(name))
    return trusted_approvals


def _read_flag_value(argv: list[str], index: int, flag: str) -> str:
    """Return the next argv token for a flag or exit with a deterministic error."""
    value_index = index + 1
    if value_index >= len(argv):
        raise SystemExit(f"Missing value for {flag}.")
    value = argv[value_index]
    if value.startswith("--"):
        raise SystemExit(f"Missing value for {flag}.")
    return value


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    argv = list(sys.argv[1:] if argv is None else argv)
    base_sha = ""
    head_sha = ""
    pr_body = ""
    event_path: Path | None = None
    trusted_approvals: set[str] = set()

    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument == "--base-sha":
            index += 1
            base_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--head-sha":
            index += 1
            head_sha = _read_flag_value(argv, index - 1, argument)
        elif argument == "--body":
            index += 1
            pr_body = _read_flag_value(argv, index - 1, argument)
        elif argument == "--event-path":
            index += 1
            event_path = Path(_read_flag_value(argv, index - 1, argument))
        else:
            raise SystemExit(f"Unknown argument: {argument}")
        index += 1

    if not base_sha or not head_sha:
        raise SystemExit("Provide both --base-sha and --head-sha.")

    if event_path is not None:
        trusted_approvals = extract_trusted_approvals(event_path)
        if not pr_body:
            pr_body = extract_pr_body(event_path)

    total_changed_lines, _numstat_counted_files, _numstat_changed_files = parse_numstat_details(
        collect_numstat_output(base_sha=base_sha, head_sha=head_sha),
    )
    changed_files = collect_changed_files(base_sha=base_sha, head_sha=head_sha)
    counted_files = len(changed_files)
    exit_code, lines = evaluate_pr_size_policy(
        total_changed_lines=total_changed_lines,
        counted_files=counted_files,
        pr_body=pr_body,
        changed_files=changed_files,
        trusted_approvals=trusted_approvals,
    )
    for line in lines:
        print(line)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
