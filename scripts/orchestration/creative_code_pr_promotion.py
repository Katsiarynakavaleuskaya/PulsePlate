"""CLI for PR-3 human-approved creative-code PR promotion.

This tool promotes one accepted PR-2 candidate patch into a normal non-draft
`experiment/*` pull request after isolated validation and explicit human TTY
approval. It is intentionally not wired to experiment_pipeline,
experiment_promote, notification wrappers, review-thread tooling, or merge
readiness.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404: fixed git/gh subprocess wrappers only (remove-by: 2026-07-31, ref: PR-3)
import sys
import tempfile
import uuid
from typing import Any, Mapping, Protocol, cast
from urllib.parse import urlparse

from core.evidence.fingerprints import fingerprint_payload
from scripts.orchestration import creative_code_patch_generation as patch_generation_cli
from scripts.orchestration.creative_code_patch_builder import (
    CANDIDATE_PATCH_FILE,
    EXPERIMENT_PACKET_FILE,
    PATCH_METADATA_FILE,
    REQUEST_FILE,
    RESULT_FILE,
    SELECTED_VARIANT_FILE,
    SOURCE_BUNDLE_FILE,
)
from scripts.orchestration.creative_code_patch_contract import (
    CreativeCodePatchContractError,
    read_creative_code_patch_build_request,
    read_creative_code_patch_result,
    validate_creative_code_patch_build_request,
    validate_creative_code_patch_result,
    validate_creative_code_patch_run_sidecars,
)
from scripts.orchestration.creative_code_patch_workspace import (
    REPO_ROOT,
    CreativeCodePatchWorkspaceError,
    git_env_without_parent_state,
    read_json,
    resolve_run_dir as resolve_patch_run_dir,
    resolve_run_file as resolve_patch_run_file,
    write_json_atomic,
)
from scripts.orchestration.creative_code_pr_promotion_contract import (
    RUNNER_COAUTHOR,
    TARGET_BASE_BRANCH,
    TARGET_REPOSITORY,
    CreativeCodePRPromotionContractError,
    build_creative_code_pr_promotion_approval,
    build_creative_code_pr_promotion_plan,
    build_creative_code_pr_promotion_receipt,
    build_creative_code_pr_promotion_validation,
    promotion_plan_fingerprint,
    read_json_object,
    reject_unsafe_public_text,
    require_safe_branch,
    validate_creative_code_pr_promotion_approval,
    validate_creative_code_pr_promotion_plan,
    validate_creative_code_pr_promotion_receipt,
    validate_creative_code_pr_promotion_validation,
)
from scripts.orchestration.creative_code_specification import (
    read_creative_code_specification_bundle,
    validate_creative_code_specification_bundle,
)
from scripts.orchestration.experiment_runner import RunnerCapabilitySignal, evaluate_candidate

PROMOTION_ROOT = REPO_ROOT / "artifacts" / "orchestration" / "creative_code" / "promotions"

PLAN_FILE = "promotion_plan.json"
PROMOTION_STATE_FILE = "promotion_state.json"
VALIDATION_FILE = "preopen_validation.json"
APPROVAL_FILE = "promotion_approval.json"
RECEIPT_FILE = "promotion_receipt.json"
PR_BODY_FILE = "pull_request_body.md"
VALIDATION_CHECKOUT = "validation_checkout"
PROMOTION_CHECKOUT = "promotion_checkout"

SUCCESS_PLAN_OUTPUT = "PASS: creative-code PR promotion plan complete"
SUCCESS_VALIDATE_OUTPUT = "PASS: creative-code PR promotion validation complete"
SUCCESS_APPROVE_OUTPUT = "PASS: creative-code PR promotion approval complete"
SUCCESS_PROMOTE_OUTPUT = "PASS: creative-code PR promotion complete"

SAFE_PROMOTION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SAFE_SLUG_RE = re.compile(r"[^a-z0-9]+")
COMMIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
SCP_GITHUB_REMOTE_RE = re.compile(
    r"^(?:(?P<user>[A-Za-z0-9._-]+)@)?(?P<host>github\.com):(?P<path>[^?#]+)$",
    re.IGNORECASE,
)
TEMP_UPLOAD_BRANCH_RE = re.compile(r"^experiment/promotion-upload-[a-z0-9][a-z0-9._-]{0,68}$")
SECRET_ENV_SUBSTRINGS = (
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASS",
    "SALT",
    "COOKIE",
    "CREDENTIAL",
    "DATABASE_URL",
    "DSN",
)


class CreativeCodePRPromotionError(ValueError):
    """Raised when the PR-3 promotion CLI fails closed."""


RUNNER_CAPABILITY_ERROR = (
    "Fresh Experiment Runner capability unavailable; trusted dispatch is required."
)


class TemporaryUploadBranchAmbiguousError(CreativeCodePRPromotionError):
    """Raised after a temp upload push returns success without create-only proof."""


class ApprovalInput(Protocol):
    def isatty(self) -> bool: ...

    def readline(self) -> str: ...


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _existing_components(path: Path) -> list[Path]:
    current_path = Path(path.anchor) if path.anchor else Path(".")
    parts = path.parts[1:] if path.anchor else path.parts
    components: list[Path] = []
    for part in parts:
        current_path = current_path / part
        if current_path.exists() or current_path.is_symlink():
            components.append(current_path)
    return components


def _reject_symlink_components(path: Path, *, label: str) -> None:
    for component in _existing_components(path):
        if component.is_symlink():
            raise CreativeCodePRPromotionError(f"{label} must not traverse symlinks.")


def ensure_promotion_root() -> Path:
    _reject_symlink_components(PROMOTION_ROOT, label="promotion artifact root")
    try:
        PROMOTION_ROOT.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise CreativeCodePRPromotionError("promotion artifact root could not be created.") from exc
    root = cast(Path, PROMOTION_ROOT.resolve(strict=True))
    if not root.is_dir():
        raise CreativeCodePRPromotionError("promotion artifact root must be a directory.")
    return root


def resolve_promotion_dir(promotion_id: str, *, create: bool = False) -> Path:
    normalized = promotion_id.strip()
    if not normalized or not SAFE_PROMOTION_ID_RE.fullmatch(normalized):
        raise CreativeCodePRPromotionError("promotion_id must be a safe identifier.")
    root = ensure_promotion_root()
    target = PROMOTION_ROOT / normalized
    _reject_symlink_components(target, label="promotion directory")
    candidate = target.resolve(strict=False)
    if not _is_relative_to(candidate, root):
        raise CreativeCodePRPromotionError("promotion directory must stay under artifact root.")
    if create:
        target.mkdir(parents=True, exist_ok=True)
    try:
        resolved = cast(Path, target.resolve(strict=True))
    except OSError as exc:
        raise CreativeCodePRPromotionError("promotion directory must exist.") from exc
    if not _is_relative_to(resolved, root) or not resolved.is_dir():
        raise CreativeCodePRPromotionError("promotion directory must stay under artifact root.")
    return resolved


def resolve_promotion_file(promotion_dir: Path, filename: str, *, for_write: bool = False) -> Path:
    if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
        raise CreativeCodePRPromotionError("promotion artifact filename must be direct.")
    root = ensure_promotion_root()
    run_root = promotion_dir.resolve(strict=True)
    if not _is_relative_to(run_root, root):
        raise CreativeCodePRPromotionError("promotion directory must stay under artifact root.")
    target = run_root / filename
    _reject_symlink_components(target.parent, label="promotion artifact parent")
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            raise CreativeCodePRPromotionError("promotion artifact file must not be a symlink.")
        if not target.is_file():
            raise CreativeCodePRPromotionError("promotion artifact path must be a file.")
    if for_write:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _write_text_atomic(path: Path, content: str) -> None:
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def _resolve_binary(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise CreativeCodePRPromotionError(f"{name} binary is required.")
    resolved = Path(binary).expanduser().resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise CreativeCodePRPromotionError(f"{name} binary must resolve to an executable file.")
    return str(resolved)


def _normalize_github_repo_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path or "\\" in path or "//" in path:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if path.startswith("/"):
        path = path[1:]
    if not path or path.startswith("/") or path.endswith("/"):
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/")
    if len(parts) != 2 or not all(parts):
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if any(part in {".", ".."} for part in parts):
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    repository = f"{parts[0]}/{parts[1]}"
    if repository != TARGET_REPOSITORY:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    return repository


def validate_pulseplate_remote_url(remote_url: str) -> str:
    """Validate that origin points exactly at the canonical PulsePlate GitHub repo."""

    candidate = remote_url.strip()
    if not candidate or any(character.isspace() for character in candidate):
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")

    scp_match = SCP_GITHUB_REMOTE_RE.fullmatch(candidate)
    if scp_match:
        if scp_match.group("user") != "git":
            raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
        return _normalize_github_repo_path(scp_match.group("path"))

    parsed = urlparse(candidate)
    if parsed.scheme not in {"ssh", "https"}:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if parsed.hostname is None or parsed.hostname.lower() != "github.com":
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if parsed.query or parsed.fragment or parsed.params:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.") from exc
    if port is not None:
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if parsed.scheme == "ssh":
        if parsed.username != "git" or parsed.password is not None:
            raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    if parsed.scheme == "https" and (parsed.username is not None or parsed.password is not None):
        raise CreativeCodePRPromotionError("origin remote must target PulsePlate.")
    return _normalize_github_repo_path(parsed.path)


def _require_commit_sha(commit_sha: str, *, label: str = "commit_sha") -> str:
    if not COMMIT_SHA_RE.fullmatch(commit_sha):
        raise CreativeCodePRPromotionError(f"{label} must be a full lowercase commit SHA.")
    return commit_sha


def _require_temp_upload_branch(branch: str, *, label: str = "temporary upload branch") -> str:
    if not TEMP_UPLOAD_BRANCH_RE.fullmatch(branch):
        raise CreativeCodePRPromotionError(f"{label} is not a safe temporary branch.")
    if "//" in branch or ".." in branch or branch.endswith((".", ".lock", "/")):
        raise CreativeCodePRPromotionError(f"{label} is not a safe git ref name.")
    return branch


def _require_remote_ref_branch(branch: str) -> str:
    return _require_temp_upload_branch(branch)


def _sanitized_command_env(*, allow_github_auth: bool = False) -> dict[str, str]:
    env: dict[str, str] = dict(git_env_without_parent_state())
    if allow_github_auth:
        # Do not copy token values into the env. The gh CLI may use its credential
        # store; token-only environments fail closed instead of being forwarded.
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    for key in list(env):
        upper_key = key.upper()
        if any(fragment in upper_key for fragment in SECRET_ENV_SUBSTRINGS):
            env.pop(key, None)
    venv_python = os.environ.get("VENV_PYTHON")
    if venv_python:
        env["VENV_PYTHON"] = venv_python
    return env


def _sanitized_git_identity_env() -> dict[str, str]:
    env = _sanitized_command_env()
    env.pop("GIT_CONFIG_GLOBAL", None)
    env.pop("GIT_CONFIG_NOSYSTEM", None)
    return env


def _run_process(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    input_text: str | None = None,
    timeout_seconds: int = 600,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(  # nosec B603: absolute binaries with bounded argv only (remove-by: 2026-07-31, ref: PR-3)
        argv,
        cwd=str(cwd),
        env=env,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    if check and process.returncode != 0:
        stderr = process.stderr.strip() or process.stdout.strip() or "unknown command failure"
        raise CreativeCodePRPromotionError(f"{Path(argv[0]).name} command failed: {stderr}")
    return process


def _reject_non_human_git_identity(*, name: str, email: str) -> None:
    normalized_name = name.strip()
    normalized_email = email.strip()
    lower_name = normalized_name.lower()
    lower_email = normalized_email.lower()
    if (
        not normalized_name
        or not normalized_email
        or "@" not in normalized_email
        or "\n" in normalized_name
        or "\n" in normalized_email
    ):
        raise CreativeCodePRPromotionError("human git identity is not configured.")
    if (
        "experiment runner" in lower_name
        or lower_email in {"pulseplate@pm.me", "runner@example.com"}
        or lower_email.endswith("@example.com")
    ):
        raise CreativeCodePRPromotionError("promotion commit requires a human git identity.")


class GitTransport:
    """Fakeable git transport with absolute binary and no shell."""

    def __init__(self, *, git_binary: str | None = None) -> None:
        self.git_binary = git_binary or _resolve_binary("git")
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        cwd: Path,
        input_text: str | None = None,
        check: bool = True,
        timeout_seconds: int = 600,
    ) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        return _run_process(
            [self.git_binary, *args],
            cwd=cwd,
            env=_sanitized_command_env(),
            input_text=input_text,
            timeout_seconds=timeout_seconds,
            check=check,
        )

    def rev_parse_origin_main(self) -> str:
        return self.run(["rev-parse", "origin/main"], cwd=REPO_ROOT).stdout.strip()

    def shared_status(self) -> str:
        return self.run(
            ["status", "--porcelain=v1", "--untracked-files=all"],
            cwd=REPO_ROOT,
        ).stdout

    def remote_url(self) -> str:
        return self.run(["remote", "get-url", "origin"], cwd=REPO_ROOT).stdout.strip()

    def remote_branch_exists(self, branch: str) -> bool:
        process = self.run(
            ["ls-remote", "--exit-code", "--heads", "origin", branch],
            cwd=REPO_ROOT,
            check=False,
            timeout_seconds=60,
        )
        if process.returncode == 0:
            return True
        if process.returncode == 2:
            return False
        stderr = process.stderr.strip() or process.stdout.strip()
        raise CreativeCodePRPromotionError(f"remote branch lookup failed: {stderr}")

    def local_branch_exists(self, branch: str, *, cwd: Path = REPO_ROOT) -> bool:
        process = self.run(["show-ref", "--verify", f"refs/heads/{branch}"], cwd=cwd, check=False)
        return process.returncode == 0

    def human_identity(self) -> tuple[str, str]:
        name = _run_process(
            [self.git_binary, "config", "--get", "user.name"],
            cwd=REPO_ROOT,
            env=_sanitized_git_identity_env(),
            check=False,
            timeout_seconds=60,
        ).stdout.strip()
        email = _run_process(
            [self.git_binary, "config", "--get", "user.email"],
            cwd=REPO_ROOT,
            env=_sanitized_git_identity_env(),
            check=False,
            timeout_seconds=60,
        ).stdout.strip()
        _reject_non_human_git_identity(name=name, email=email)
        return name, email

    def verify_commit_identity(self, *, cwd: Path, expected_name: str, expected_email: str) -> None:
        output = self.run(
            ["show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", "HEAD"],
            cwd=cwd,
            timeout_seconds=60,
        ).stdout.rstrip("\n")
        parts = output.split("\x00")
        if len(parts) != 4:
            raise CreativeCodePRPromotionError("promotion commit identity could not be read.")
        author_name, author_email, committer_name, committer_email = parts
        for name, email in (
            (author_name, author_email),
            (committer_name, committer_email),
        ):
            _reject_non_human_git_identity(name=name, email=email)
        if (
            author_name != expected_name
            or author_email != expected_email
            or committer_name != expected_name
            or committer_email != expected_email
        ):
            raise CreativeCodePRPromotionError("promotion commit identity mismatch.")

    def push_upload_branch(self, *, cwd: Path, branch: str) -> None:
        _require_temp_upload_branch(branch)
        process = self.run(
            [
                "push",
                "--porcelain",
                "origin",
                f"HEAD:refs/heads/{branch}",
            ],
            cwd=cwd,
            timeout_seconds=600,
        )
        push_output = f"{process.stdout}\n{process.stderr}"
        if "[new branch]" not in push_output:
            raise TemporaryUploadBranchAmbiguousError(
                "temporary upload push did not create a new branch; cleanup required."
            )


def _reject_forbidden_gh_args(args: list[str]) -> None:
    joined = " ".join(args)
    forbidden_sequences = (
        ["pr", "ready"],
        ["pr", "review"],
        ["pr", "merge"],
        ["pr", "close"],
        ["auth", "token"],
    )
    for sequence in forbidden_sequences:
        for index in range(0, len(args) - len(sequence) + 1):
            if args[index : index + len(sequence)] == sequence:
                raise CreativeCodePRPromotionError(
                    f"forbidden gh command shape: {' '.join(sequence)}"
                )
    forbidden_tokens = ("--draft", "--add-reviewer", "/reviews", "/merge")
    if any(token in args or token in joined for token in forbidden_tokens):
        raise CreativeCodePRPromotionError("forbidden gh command authority requested.")


class GitHubTransport:
    """Fakeable GitHub transport backed by the gh CLI."""

    def __init__(self, *, gh_binary: str | None = None) -> None:
        self.gh_binary = gh_binary or _resolve_binary("gh")
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        cwd: Path = REPO_ROOT,
        check: bool = True,
        timeout_seconds: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        _reject_forbidden_gh_args(args)
        self.calls.append(list(args))
        return _run_process(
            [self.gh_binary, *args],
            cwd=cwd,
            env=_sanitized_command_env(allow_github_auth=True),
            timeout_seconds=timeout_seconds,
            check=check,
        )

    def current_login(self) -> str:
        return self.run(["api", "user", "--jq", ".login"]).stdout.strip()

    def create_branch_ref(self, *, branch: str, commit_sha: str) -> None:
        branch = require_safe_branch(branch)
        commit_sha = _require_commit_sha(commit_sha)
        self.run(
            [
                "api",
                "-X",
                "POST",
                f"repos/{TARGET_REPOSITORY}/git/refs",
                "-f",
                f"ref=refs/heads/{branch}",
                "-f",
                f"sha={commit_sha}",
            ],
            timeout_seconds=120,
        )

    def delete_branch_ref(self, *, branch: str) -> bool:
        branch = _require_remote_ref_branch(branch)
        process = self.run(
            [
                "api",
                "-X",
                "DELETE",
                f"repos/{TARGET_REPOSITORY}/git/refs/heads/{branch}",
            ],
            check=False,
            timeout_seconds=120,
        )
        return process.returncode == 0

    def create_pull_request(
        self,
        *,
        head_branch: str,
        title: str,
        body_file: Path,
    ) -> str:
        return self.run(
            [
                "pr",
                "create",
                "--repo",
                TARGET_REPOSITORY,
                "--base",
                TARGET_BASE_BRANCH,
                "--head",
                head_branch,
                "--title",
                title,
                "--body-file",
                str(body_file),
            ],
            timeout_seconds=120,
        ).stdout.strip()

    def read_pull_request(self, *, pr_ref: str) -> dict[str, Any]:
        output = self.run(
            [
                "pr",
                "view",
                pr_ref,
                "--repo",
                TARGET_REPOSITORY,
                "--json",
                "number,url,state,isDraft,baseRefName,headRefName,headRefOid",
            ],
            timeout_seconds=120,
        ).stdout
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as exc:
            raise CreativeCodePRPromotionError("gh pr view returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise CreativeCodePRPromotionError("gh pr view must return a JSON object.")
        return payload


class GateRunner:
    """Runs the expensive pre-open gates inside an isolated checkout."""

    def run_pre_commit(self, *, cwd: Path) -> None:
        _run_process(
            [_resolve_binary("pre-commit"), "run", "--all-files"],
            cwd=cwd,
            env=_sanitized_command_env(),
            timeout_seconds=1200,
        )

    def run_validate_changed(self, *, cwd: Path) -> None:
        _run_process(
            [_resolve_binary("make"), "validate-changed"],
            cwd=cwd,
            env=_sanitized_command_env(),
            timeout_seconds=1200,
        )

    def run_fresh_oracle(self, *, experiment_packet: Path, candidate_patch: Path) -> dict[str, Any]:
        packet = read_json(experiment_packet)
        if not isinstance(packet, dict):
            raise CreativeCodePRPromotionError("experiment packet must be a JSON object.")
        try:
            result = evaluate_candidate(packet, candidate_patch)
        except RunnerCapabilitySignal:
            raise CreativeCodePRPromotionError(RUNNER_CAPABILITY_ERROR) from None
        if not isinstance(result, dict):
            raise CreativeCodePRPromotionError("fresh oracle must return a JSON object.")
        return result


def _load_patch_run(
    patch_run_id: str,
) -> tuple[
    Path,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    str,
    dict[str, Any],
    dict[str, Any],
]:
    run_dir = resolve_patch_run_dir(patch_run_id, create=False)
    request_path = resolve_patch_run_file(run_dir, REQUEST_FILE)
    bundle_path = resolve_patch_run_file(run_dir, SOURCE_BUNDLE_FILE)
    result_path = resolve_patch_run_file(run_dir, RESULT_FILE)
    selected_variant_path = resolve_patch_run_file(run_dir, SELECTED_VARIANT_FILE)
    patch_path = resolve_patch_run_file(run_dir, CANDIDATE_PATCH_FILE)
    metadata_path = resolve_patch_run_file(run_dir, PATCH_METADATA_FILE)

    bundle = read_creative_code_specification_bundle(bundle_path)
    request = read_creative_code_patch_build_request(str(request_path))
    request = validate_creative_code_patch_build_request(request, source_bundle=bundle)
    result = read_creative_code_patch_result(str(result_path))
    result = validate_creative_code_patch_result(result)
    selected_variant = read_json(selected_variant_path)
    metadata = read_json(metadata_path)
    if not isinstance(selected_variant, dict) or not isinstance(metadata, dict):
        raise CreativeCodePRPromotionError("selected variant and patch metadata must be objects.")
    validate_creative_code_specification_bundle(bundle)
    try:
        patch_text = patch_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CreativeCodePRPromotionError("candidate patch could not be read.") from exc
    return run_dir, request, bundle, result, patch_text, selected_variant, metadata


def _patch_changed_paths(patch_text: str) -> list[str]:
    paths: set[str] = set()
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
            raise CreativeCodePRPromotionError("candidate.patch contains unsupported diff header.")
        old_path = parts[2][2:]
        new_path = parts[3][2:]
        if old_path != new_path:
            raise CreativeCodePRPromotionError("candidate.patch renames are not supported.")
        path = Path(new_path)
        if path.is_absolute() or ".." in path.parts or "\\" in new_path or new_path in {"", "."}:
            raise CreativeCodePRPromotionError("candidate.patch contains unsafe changed path.")
        paths.add(new_path)
    if not paths:
        raise CreativeCodePRPromotionError("candidate.patch must contain at least one diff header.")
    return sorted(paths)


def _require_accepted_pr2_artifacts(
    *,
    request: dict[str, Any],
    result: dict[str, Any],
    patch_text: str,
    selected_variant: dict[str, Any],
    patch_metadata: dict[str, Any],
) -> dict[str, Any]:
    try:
        return cast(
            dict[str, Any],
            validate_creative_code_patch_run_sidecars(
                request=request,
                result=result,
                patch_text=patch_text,
                selected_variant=selected_variant,
                patch_metadata=patch_metadata,
                require_accepted=True,
            ),
        )
    except CreativeCodePatchContractError as exc:
        raise CreativeCodePRPromotionError(str(exc)) from exc


def _slugify(value: str) -> str:
    lowered = value.lower()
    slug = SAFE_SLUG_RE.sub("-", lowered).strip("-")
    return slug or "candidate"


def _derive_branch(*, selected_variant_id: str, patch_fingerprint: str) -> str:
    patch_short = patch_fingerprint.removeprefix("sha256:")[:8]
    slug = _slugify(selected_variant_id)
    max_slug = 80 - len("experiment/") - len("-") - len(patch_short)
    branch = f"experiment/{slug[:max_slug].strip('-')}-{patch_short}"
    return cast(str, require_safe_branch(branch))


def _derive_temp_upload_branch(*, target_branch: str, commit_sha: str) -> str:
    require_safe_branch(target_branch)
    _require_commit_sha(commit_sha)
    target_slug = _slugify(target_branch.split("/", 1)[1])[:30].strip("-") or "candidate"
    branch = f"experiment/promotion-upload-{target_slug}-{commit_sha[:8]}-{uuid.uuid4().hex[:10]}"
    return _require_temp_upload_branch(branch)


def _cleanup_temp_upload_ref(github: GitHubTransport, *, branch: str) -> bool:
    try:
        return github.delete_branch_ref(branch=branch)
    except (CreativeCodePRPromotionError, OSError, subprocess.SubprocessError):
        return False


def _render_pr_body(
    *,
    promotion_id: str,
    result: dict[str, Any],
    branch: str,
    changed_paths: list[str],
    validation_fingerprint: str | None = None,
    approval_id: str | None = None,
) -> str:
    changed = "\n".join(f"- `{path}`" for path in changed_paths)
    validation_ref = validation_fingerprint or "pending validate command"
    approval_ref = approval_id or "pending approve command"
    body = f"""## Summary
Promote one accepted PR-2 creative-code candidate patch into the normal PulsePlate PR lifecycle as a non-draft experiment PR.

## Goal
Open a reviewable `experiment/*` branch from an accepted local candidate patch with explicit human approval.

## Business reason
This reduces manual patch copying and preserves provenance from creative-code generation into ordinary CI, bot review, security review, QA, fixed mapping, and human merge decision.

## Scope
- Promotion id: `{promotion_id}`
- Source PR-2 result: `{result["result_id"]}`
- Patch fingerprint: `{result["patch_summary"]["patch_fingerprint"]}`
- Base branch: `main`
- Head branch: `{branch}`
- Changed paths:
{changed}

## Out of scope
Draft PRs, branch updates, force push, review requests, review submissions, review-thread resolution, fixed mapping generation, merge-readiness claims, merge, release, Slack authority, GitHub App changes, product runtime AI, OpenAPI/client, frontend, iOS, DB, and dependency changes.

## Creative Research Origin
The candidate patch comes from a PR-2 sandboxed patch-builder result. PR-2 artifacts are local evidence only and are not promotion or merge authority.

## Alternatives Considered
Manual patch copying remains possible but loses structured provenance. Autonomous promotion was rejected because human approval is required before opening a non-draft PR.

## Patch Evidence
Patch fingerprint: `{result["patch_summary"]["patch_fingerprint"]}`. Candidate evaluation is not merge-readiness evidence.

## Oracle Evidence
Fresh candidate oracle validation is required before promotion. A separate oracle-only governance review of the actual PR diff remains required.

## Pre-Open Validation
Validation artifact: `{validation_ref}`.

## Security Notes
Generated code may be incorrect. No medical or clinical claim is established by this PR. Candidate source diff, model inputs, reasoning traces, external service payload material, runner logs, secrets, and machine-local filesystem details are intentionally omitted.

## Cost
Cost metadata: unavailable.

## Known Limitations
The opened PR starts the normal review cycle only. It does not prove merge readiness.

## Human Approval
Approval artifact: `{approval_ref}`. Approval is TTY-bound and actor-bound.

## Tests / Validation
- focused promotion contract tests
- focused PR-2 patch-builder regression tests
- `make validate-changed`
- `pre-commit run --all-files`

## Deferred / Follow-ups
Additional applied candidates remain separate governed review lanes after this PR starts normal review.

## Experiment Runner Evidence
Candidate evaluation is not merge-readiness evidence. Oracle-only governance evidence for this PR diff remains required before readiness claims.

## Discussion Thread Pass
Not claimed by this promotion tool.

## Fixed in Commit Mapping
Not generated by this promotion tool.

## Merge Readiness
Merge readiness is not claimed.
"""
    reject_unsafe_public_text(body, label="pull_request_body")
    return body


def _load_plan(promotion_dir: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        validate_creative_code_pr_promotion_plan(
            read_json_object(resolve_promotion_file(promotion_dir, PLAN_FILE))
        ),
    )


def _load_state(promotion_dir: Path) -> dict[str, Any]:
    state = read_json(resolve_promotion_file(promotion_dir, PROMOTION_STATE_FILE))
    if not isinstance(state, dict):
        raise CreativeCodePRPromotionError("promotion state must be a JSON object.")
    patch_run = state.get("patch_run")
    if not isinstance(patch_run, str) or not SAFE_PROMOTION_ID_RE.fullmatch(patch_run):
        raise CreativeCodePRPromotionError("promotion state patch_run is invalid.")
    return state


def _load_validation(promotion_dir: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        validate_creative_code_pr_promotion_validation(
            read_json_object(resolve_promotion_file(promotion_dir, VALIDATION_FILE))
        ),
    )


def _load_approval(promotion_dir: Path) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        validate_creative_code_pr_promotion_approval(
            read_json_object(resolve_promotion_file(promotion_dir, APPROVAL_FILE))
        ),
    )


def _require_validation_matches_plan(
    *,
    validation_artifact: dict[str, Any],
    plan_artifact: dict[str, Any],
) -> str:
    plan_fp = promotion_plan_fingerprint(plan_artifact)
    if validation_artifact["promotion_id"] != plan_artifact["promotion_id"]:
        raise CreativeCodePRPromotionError("validation artifact promotion_id mismatch.")
    if validation_artifact["plan_fingerprint"] != plan_fp:
        raise CreativeCodePRPromotionError("validation artifact does not match current plan.")
    if validation_artifact["patch_fingerprint"] != plan_artifact["patch_fingerprint"]:
        raise CreativeCodePRPromotionError("validation patch fingerprint does not match plan.")
    if validation_artifact["base_commit_sha"] != plan_artifact["base_commit_sha"]:
        raise CreativeCodePRPromotionError("validation base commit does not match plan.")
    return cast(str, plan_fp)


def _require_approval_matches_plan_and_validation(
    *,
    approval_artifact: dict[str, Any],
    plan_artifact: dict[str, Any],
    validation_artifact: dict[str, Any],
) -> None:
    plan_fp = _require_validation_matches_plan(
        validation_artifact=validation_artifact,
        plan_artifact=plan_artifact,
    )
    if approval_artifact["promotion_id"] != plan_artifact["promotion_id"]:
        raise CreativeCodePRPromotionError("approval artifact promotion_id mismatch.")
    if approval_artifact["plan_fingerprint"] != plan_fp:
        raise CreativeCodePRPromotionError("approval artifact does not match current plan.")
    if approval_artifact["validation_fingerprint"] != validation_artifact["validation_fingerprint"]:
        raise CreativeCodePRPromotionError("approval artifact does not match current validation.")
    if approval_artifact["confirmed_patch_fingerprint"] != plan_artifact["patch_fingerprint"]:
        raise CreativeCodePRPromotionError("approval patch fingerprint does not match plan.")
    if approval_artifact["confirmed_base_commit_sha"] != plan_artifact["base_commit_sha"]:
        raise CreativeCodePRPromotionError("approval base commit does not match plan.")
    if approval_artifact["confirmed_target_branch"] != plan_artifact["target_head_branch"]:
        raise CreativeCodePRPromotionError("approval target branch does not match plan.")


def _require_receipt_matches_plan_validation_approval(
    *,
    receipt: dict[str, Any],
    plan_artifact: dict[str, Any],
    validation_artifact: dict[str, Any],
    approval_artifact: dict[str, Any],
) -> None:
    plan_fp = promotion_plan_fingerprint(plan_artifact)
    expected_pairs = (
        ("promotion_id", plan_artifact["promotion_id"]),
        ("plan_fingerprint", plan_fp),
        ("validation_fingerprint", validation_artifact["validation_fingerprint"]),
        ("approval_id", approval_artifact["approval_id"]),
        ("source_result_id", plan_artifact["source_result_id"]),
        ("patch_fingerprint", plan_artifact["patch_fingerprint"]),
        ("head_branch", plan_artifact["target_head_branch"]),
        ("approved_by_login", approval_artifact["approved_by_login"]),
    )
    for key, expected in expected_pairs:
        if receipt[key] != expected:
            raise CreativeCodePRPromotionError(f"existing receipt {key} mismatch.")


def _require_open_pr_readback(
    readback: Mapping[str, Any],
    *,
    branch: str,
    commit_sha: str,
    pr_url: str,
    expected_number: int | None,
    error_message: str,
) -> tuple[int, str]:
    number = readback.get("number")
    url = readback.get("url")
    if (
        not isinstance(number, int)
        or number < 1
        or not isinstance(url, str)
        or not url
        or url != pr_url
        or (expected_number is not None and number != expected_number)
        or readback.get("state") != "OPEN"
        or readback.get("isDraft") is not False
        or readback.get("baseRefName") != TARGET_BASE_BRANCH
        or readback.get("headRefName") != branch
        or readback.get("headRefOid") != commit_sha
    ):
        raise CreativeCodePRPromotionError(error_message)
    return number, url


def _require_existing_receipt_live_pr(
    *,
    receipt: dict[str, Any],
    github: GitHubTransport,
) -> None:
    if (
        receipt["pull_request_state"] != "open"
        or receipt["partial_failure"] is not None
        or receipt["pull_request_number"] < 1
        or not receipt["pull_request_url"]
        or receipt["review_cycle_started"] is not True
    ):
        raise CreativeCodePRPromotionError("existing receipt is not a completed open PR.")
    readback = github.read_pull_request(pr_ref=receipt["pull_request_url"])
    _require_open_pr_readback(
        readback,
        branch=receipt["head_branch"],
        commit_sha=receipt["commit_sha"],
        pr_url=receipt["pull_request_url"],
        expected_number=receipt["pull_request_number"],
        error_message="existing promotion receipt failed live PR readback verification",
    )


def _load_current_patch_text_for_plan(
    *,
    promotion_dir: Path,
    plan_artifact: dict[str, Any],
) -> str:
    state = _load_state(promotion_dir)
    if state["source_result_id"] != plan_artifact["source_result_id"]:
        raise CreativeCodePRPromotionError("promotion state does not match current plan.")
    if state["patch_fingerprint"] != plan_artifact["patch_fingerprint"]:
        raise CreativeCodePRPromotionError("promotion state patch fingerprint mismatch.")
    run_dir = resolve_patch_run_dir(state["patch_run"], create=False)
    patch_text = resolve_patch_run_file(run_dir, CANDIDATE_PATCH_FILE).read_text(encoding="utf-8")
    current_patch_fingerprint = fingerprint_payload({"candidate_patch": patch_text})
    if current_patch_fingerprint != plan_artifact["patch_fingerprint"]:
        raise CreativeCodePRPromotionError("candidate.patch changed after plan validation.")
    if _patch_changed_paths(patch_text) != sorted(plan_artifact["changed_paths"]):
        raise CreativeCodePRPromotionError("candidate.patch changed paths mismatch.")
    return cast(str, patch_text)


def _load_trusted_apple_dispatch_result(
    *,
    result_path: Path,
    generation_receipt_path: Path,
    experiment_packet: Path,
    run_dir: Path,
    plan_artifact: Mapping[str, Any],
) -> tuple[Path, dict[str, Any], dict[str, Any], str, str, Path, str, Path, str]:
    """Load one exact accepted Apple Container result through the PR-2 trust boundary."""

    try:
        resolved_result = patch_generation_cli._resolve_dispatch_result(result_path)
        packet = patch_generation_cli._read_experiment_packet(
            experiment_packet,
            trusted_root=run_dir,
        )
        result = patch_generation_cli._validate_dispatch_result_binding(
            dispatch_result=patch_generation_cli._read_pinned_dispatch_json_object(resolved_result),
            packet=packet,
            changed_paths=list(plan_artifact["changed_paths"]),
            patch_fingerprint=str(plan_artifact["patch_fingerprint"]),
        )
        generation_root = patch_generation_cli.PATCH_GENERATION_ROOT
        patch_generation_cli._reject_symlink_components(
            generation_root,
            label="patch generation root",
        )
        receipt_candidate = (
            generation_receipt_path
            if generation_receipt_path.is_absolute()
            else patch_generation_cli.REPO_ROOT / generation_receipt_path
        )
        patch_generation_cli._reject_symlink_components(
            receipt_candidate,
            label="trusted generation receipt",
        )
        try:
            resolved_receipt = receipt_candidate.resolve(strict=True)
        except OSError as exc:
            raise CreativeCodePRPromotionError("trusted generation receipt must exist.") from exc
        resolved_generation_root = generation_root.resolve(strict=False)
        if (
            not _is_relative_to(resolved_receipt, resolved_generation_root)
            or not resolved_receipt.is_file()
        ):
            raise CreativeCodePRPromotionError(
                "trusted generation receipt must be a file under patch generation artifacts."
            )
        if resolved_receipt.name != patch_generation_cli.RECEIPT_FILENAME:
            raise CreativeCodePRPromotionError(
                "trusted generation receipt must be named generation_receipt.json."
            )
        receipt = patch_generation_cli.validate_generation_receipt(
            patch_generation_cli._read_generated_sidecar_json_object(
                resolved_receipt,
                run_dir=resolved_generation_root,
                label="generation receipt",
            )
        )
        resolved_gate = resolved_receipt.with_name(patch_generation_cli.GATE_FILENAME)
        patch_generation_cli._reject_symlink_components(
            resolved_gate,
            label="trusted generation gate",
        )
        gate = patch_generation_cli._read_generation_gate(resolved_gate)
        patch_generation_cli._validate_receipt_matches_gate(
            receipt,
            gate,
            resolved_gate,
        )
        patch_generation_cli.validate_generation_receipt_linked_artifacts(receipt)
    except (
        patch_generation_cli.CreativeCodePatchGenerationError,
        CreativeCodePatchWorkspaceError,
    ) as exc:
        raise CreativeCodePRPromotionError(str(exc)) from exc

    if receipt["run_id"] != run_dir.name:
        raise CreativeCodePRPromotionError(
            "trusted dispatch generation receipt does not match the PR-2 run."
        )
    if receipt["result_id"] != plan_artifact["source_result_id"]:
        raise CreativeCodePRPromotionError(
            "trusted dispatch generation receipt does not match the planned PR-2 result."
        )
    if receipt["experiment_packet_fingerprint"] != fingerprint_payload(packet):
        raise CreativeCodePRPromotionError(
            "trusted dispatch experiment packet is not bound to the PR-2 generation receipt."
        )
    if packet["base_commit_sha"] != plan_artifact["base_commit_sha"]:
        raise CreativeCodePRPromotionError(
            "trusted dispatch experiment packet base commit does not match plan."
        )
    if packet["candidate_patch_fingerprint"] != plan_artifact["patch_fingerprint"]:
        raise CreativeCodePRPromotionError(
            "trusted dispatch experiment packet candidate fingerprint does not match plan."
        )
    if sorted(packet["mutable_candidate_surface"]) != sorted(plan_artifact["changed_paths"]):
        raise CreativeCodePRPromotionError(
            "trusted dispatch experiment packet mutable paths do not match plan."
        )
    if result["status"] != "accepted" or result["failure_class"] is not None:
        raise CreativeCodePRPromotionError(
            "trusted Apple Container dispatch result must be accepted."
        )
    backend = result.get("execution_backend")
    if (
        not isinstance(backend, dict)
        or backend.get("name") != "apple-container"
        or backend.get("preflight_status") != "passed"
    ):
        raise CreativeCodePRPromotionError(
            "trusted dispatch result must prove passed Apple Container provenance."
        )
    if receipt["runner_summary"]["runner_result_fingerprint"] != fingerprint_payload(result):
        raise CreativeCodePRPromotionError(
            "trusted dispatch result does not match the result finalized into PR-2."
        )
    return (
        resolved_result,
        packet,
        result,
        fingerprint_payload(packet),
        fingerprint_payload(result),
        resolved_receipt,
        fingerprint_payload(receipt),
        resolved_gate,
        fingerprint_payload(gate),
    )


def plan(
    *,
    patch_run: str,
    promotion_id: str,
    git: GitTransport | None = None,
) -> dict[str, Any]:
    git = git or GitTransport()
    promotion_dir = resolve_promotion_dir(promotion_id, create=True)
    if any(
        path.name not in {PR_BODY_FILE, PLAN_FILE, PROMOTION_STATE_FILE}
        for path in promotion_dir.iterdir()
    ):
        raise CreativeCodePRPromotionError("promotion directory contains unexpected artifacts.")
    run_dir, request, _bundle, result, patch_text, selected_variant, patch_metadata = (
        _load_patch_run(patch_run)
    )
    metadata = _require_accepted_pr2_artifacts(
        request=request,
        result=result,
        patch_text=patch_text,
        selected_variant=selected_variant,
        patch_metadata=patch_metadata,
    )
    origin_main = git.rev_parse_origin_main()
    if origin_main != result["base_commit_sha"]:
        raise CreativeCodePRPromotionError("PR-2 base_commit_sha must match current origin/main.")
    if git.shared_status().strip():
        raise CreativeCodePRPromotionError("shared worktree must be clean before planning.")
    branch = _derive_branch(
        selected_variant_id=result["selected_variant_id"],
        patch_fingerprint=metadata["patch_fingerprint"],
    )
    if git.remote_branch_exists(branch) or git.local_branch_exists(branch):
        raise CreativeCodePRPromotionError("target experiment branch already exists.")
    title = f"experiment: {_slugify(result['selected_variant_id'])[:80]}"
    body = _render_pr_body(
        promotion_id=promotion_id,
        result=result,
        branch=branch,
        changed_paths=result["changed_paths"],
    )
    body_fingerprint = fingerprint_payload({"pull_request_body": body})
    plan_artifact = build_creative_code_pr_promotion_plan(
        promotion_id=promotion_id,
        source_result_id=result["result_id"],
        source_request_id=request["request_id"],
        source_bundle_id=request["source_bundle_id"],
        source_bundle_fingerprint=request["source_bundle_fingerprint"],
        selected_variant_id=request["selected_variant_id"],
        selected_variant_fingerprint=request["selected_variant_fingerprint"],
        patch_fingerprint=metadata["patch_fingerprint"],
        base_commit_sha=request["base_commit_sha"],
        changed_paths=result["changed_paths"],
        target_head_branch=branch,
        pull_request_title=title,
        pull_request_body_fingerprint=body_fingerprint,
    )
    _write_text_atomic(resolve_promotion_file(promotion_dir, PR_BODY_FILE, for_write=True), body)
    write_json_atomic(
        resolve_promotion_file(promotion_dir, PLAN_FILE, for_write=True), plan_artifact
    )
    write_json_atomic(
        resolve_promotion_file(promotion_dir, PROMOTION_STATE_FILE, for_write=True),
        {
            "schema_version": "1.0",
            "artifact_type": "creative_code_pr_promotion_local_state",
            "promotion_id": promotion_id,
            "patch_run": patch_run,
            "source_result_id": result["result_id"],
            "patch_fingerprint": metadata["patch_fingerprint"],
        },
    )
    return {
        "promotion_dir": str(promotion_dir),
        "patch_run_dir": str(run_dir),
        "plan": plan_artifact,
        "plan_fingerprint": promotion_plan_fingerprint(plan_artifact),
    }


def _destroy_checkout(promotion_dir: Path, dirname: str) -> bool:
    checkout = promotion_dir / dirname
    if not checkout.exists() and not checkout.is_symlink():
        return True
    root = promotion_dir.resolve(strict=True)
    if checkout.is_symlink():
        raise CreativeCodePRPromotionError("promotion checkout must not be a symlink.")
    resolved = checkout.resolve(strict=True)
    if not _is_relative_to(resolved, root):
        raise CreativeCodePRPromotionError("promotion checkout must stay under promotion dir.")
    shutil.rmtree(resolved)
    return not checkout.exists()


def _prepare_checkout(
    *,
    promotion_dir: Path,
    dirname: str,
    base_commit_sha: str,
    git: GitTransport,
    branch: str | None = None,
    promotion_remote: bool = False,
) -> Path:
    checkout = promotion_dir / dirname
    if checkout.exists() or checkout.is_symlink():
        raise CreativeCodePRPromotionError(f"{dirname} already exists.")
    git.run(["clone", "--no-hardlinks", str(REPO_ROOT), str(checkout)], cwd=REPO_ROOT)
    try:
        git.run(["checkout", "--detach", base_commit_sha], cwd=checkout)
        if promotion_remote:
            remote_url = git.remote_url()
            validate_pulseplate_remote_url(remote_url)
            git.run(["remote", "set-url", "origin", remote_url], cwd=checkout)
        else:
            git.run(["remote", "set-url", "--push", "origin", "DISABLED"], cwd=checkout)
        if branch:
            git.run(["checkout", "-b", branch], cwd=checkout)
        head_sha = git.run(["rev-parse", "HEAD"], cwd=checkout).stdout.strip()
        if head_sha != base_commit_sha:
            raise CreativeCodePRPromotionError("promotion checkout HEAD mismatch.")
        status = git.run(["status", "--porcelain=v1", "--untracked-files=all"], cwd=checkout).stdout
        if status.strip():
            raise CreativeCodePRPromotionError("promotion checkout must start clean.")
    except Exception:
        _destroy_checkout(promotion_dir, dirname)
        raise
    return checkout


def _apply_patch_and_verify(
    *,
    checkout: Path,
    patch_text: str,
    changed_paths: list[str],
    git: GitTransport,
) -> None:
    git.run(["apply", "--check"], cwd=checkout, input_text=patch_text)
    git.run(["apply", "--index"], cwd=checkout, input_text=patch_text)
    actual = git.run(
        ["diff", "--cached", "--name-only", "--no-renames", "HEAD"], cwd=checkout
    ).stdout.splitlines()
    if sorted(actual) != sorted(changed_paths):
        raise CreativeCodePRPromotionError("applied patch changed paths do not match plan.")


def _ensure_patch_unchanged_after_gates(
    *,
    checkout: Path,
    expected_patch_fingerprint: str,
    git: GitTransport,
) -> None:
    status = git.run(["status", "--porcelain=v1", "--untracked-files=all"], cwd=checkout).stdout
    if status.strip():
        raise CreativeCodePRPromotionError("pre-open gates mutated the validation checkout.")
    patch_text = git.run(["diff", "--binary", "HEAD^", "HEAD"], cwd=checkout).stdout
    if fingerprint_payload({"candidate_patch": patch_text}) != expected_patch_fingerprint:
        raise CreativeCodePRPromotionError("patch changed after validation gates.")


def validate(
    *,
    promotion_id: str,
    trusted_dispatch_result: Path | None = None,
    trusted_generation_receipt: Path | None = None,
    git: GitTransport | None = None,
    gate_runner: GateRunner | None = None,
) -> dict[str, Any]:
    if (trusted_dispatch_result is None) != (trusted_generation_receipt is None):
        raise CreativeCodePRPromotionError(
            "trusted dispatch result and generation receipt must be supplied together."
        )
    git = git or GitTransport()
    gate_runner = gate_runner or GateRunner()
    promotion_dir = resolve_promotion_dir(promotion_id, create=False)
    plan_artifact = _load_plan(promotion_dir)
    if git.rev_parse_origin_main() != plan_artifact["base_commit_sha"]:
        raise CreativeCodePRPromotionError("origin/main drifted after promotion plan.")
    if git.shared_status().strip():
        raise CreativeCodePRPromotionError("shared worktree must be clean before validation.")

    state = _load_state(promotion_dir)
    run_dir = resolve_patch_run_dir(state["patch_run"], create=False)
    patch_path = resolve_patch_run_file(run_dir, CANDIDATE_PATCH_FILE)
    experiment_packet = resolve_patch_run_file(run_dir, EXPERIMENT_PACKET_FILE)
    patch_text = _load_current_patch_text_for_plan(
        promotion_dir=promotion_dir,
        plan_artifact=plan_artifact,
    )
    checkout_created = False
    try:
        checkout = _prepare_checkout(
            promotion_dir=promotion_dir,
            dirname=VALIDATION_CHECKOUT,
            base_commit_sha=plan_artifact["base_commit_sha"],
            git=git,
            branch=f"validation/{promotion_id}",
            promotion_remote=False,
        )
        checkout_created = True
        _apply_patch_and_verify(
            checkout=checkout,
            patch_text=patch_text,
            changed_paths=plan_artifact["changed_paths"],
            git=git,
        )
        git.run(
            [
                "-c",
                "user.name=PulsePlate Validation",
                "-c",
                "user.email=pulseplate@pm.me",
                "commit",
                "--no-gpg-sign",
                "-m",
                f"validation: {promotion_id}",
            ],
            cwd=checkout,
        )
        trusted_dispatch_snapshot: (
            tuple[
                Path,
                dict[str, Any],
                dict[str, Any],
                str,
                str,
                Path,
                str,
                Path,
                str,
            ]
            | None
        ) = None
        if trusted_dispatch_result is None:
            oracle_result = gate_runner.run_fresh_oracle(
                experiment_packet=experiment_packet,
                candidate_patch=patch_path,
            )
        else:
            if trusted_generation_receipt is None:
                raise CreativeCodePRPromotionError(
                    "trusted generation receipt path missing during validation."
                )
            trusted_dispatch_snapshot = _load_trusted_apple_dispatch_result(
                result_path=trusted_dispatch_result,
                generation_receipt_path=trusted_generation_receipt,
                experiment_packet=experiment_packet,
                run_dir=run_dir,
                plan_artifact=plan_artifact,
            )
            oracle_result = trusted_dispatch_snapshot[2]
        if (
            oracle_result.get("status") != "accepted"
            or oracle_result.get("failure_class") is not None
        ):
            raise CreativeCodePRPromotionError("fresh candidate oracle rejected the patch.")
        if sorted(oracle_result.get("mutated_paths", [])) != sorted(plan_artifact["changed_paths"]):
            raise CreativeCodePRPromotionError("fresh candidate oracle changed paths mismatch.")
        if oracle_result.get("shared_tree_untouched") is not True:
            raise CreativeCodePRPromotionError("fresh candidate oracle touched shared tree.")
        gate_runner.run_pre_commit(cwd=checkout)
        gate_runner.run_validate_changed(cwd=checkout)
        _ensure_patch_unchanged_after_gates(
            checkout=checkout,
            expected_patch_fingerprint=plan_artifact["patch_fingerprint"],
            git=git,
        )
        if trusted_dispatch_snapshot is not None:
            if trusted_dispatch_result is None or trusted_generation_receipt is None:
                raise CreativeCodePRPromotionError(
                    "trusted dispatch evidence paths missing during snapshot verification."
                )
            current_snapshot = _load_trusted_apple_dispatch_result(
                result_path=trusted_dispatch_result,
                generation_receipt_path=trusted_generation_receipt,
                experiment_packet=experiment_packet,
                run_dir=run_dir,
                plan_artifact=plan_artifact,
            )
            if (
                current_snapshot[0] != trusted_dispatch_snapshot[0]
                or current_snapshot[3] != trusted_dispatch_snapshot[3]
                or current_snapshot[4] != trusted_dispatch_snapshot[4]
                or current_snapshot[5] != trusted_dispatch_snapshot[5]
                or current_snapshot[6] != trusted_dispatch_snapshot[6]
                or current_snapshot[7] != trusted_dispatch_snapshot[7]
                or current_snapshot[8] != trusted_dispatch_snapshot[8]
            ):
                raise CreativeCodePRPromotionError(
                    "trusted dispatch evidence changed during validation."
                )
    finally:
        destroyed = _destroy_checkout(promotion_dir, VALIDATION_CHECKOUT)
    if not checkout_created or not destroyed:
        raise CreativeCodePRPromotionError("validation checkout cleanup failed.")
    budget_observations = oracle_result.get("budget_observations", {})
    if not isinstance(budget_observations, dict):
        raise CreativeCodePRPromotionError("fresh oracle budget observations missing.")
    validation_artifact: dict[str, Any] = build_creative_code_pr_promotion_validation(
        promotion_id=promotion_id,
        plan_fingerprint=promotion_plan_fingerprint(plan_artifact),
        patch_fingerprint=plan_artifact["patch_fingerprint"],
        base_commit_sha=plan_artifact["base_commit_sha"],
        oracle_commands_configured=int(budget_observations["oracle_commands_configured"]),
        oracle_commands_executed=int(budget_observations["oracle_commands_executed"]),
    )
    write_json_atomic(
        resolve_promotion_file(promotion_dir, VALIDATION_FILE, for_write=True),
        validation_artifact,
    )
    return validation_artifact


def approve(
    *,
    promotion_id: str,
    approved_by_login: str,
    github: GitHubTransport | None = None,
    stdin: ApprovalInput | None = None,
    stdout: Any | None = None,
) -> dict[str, Any]:
    github = github or GitHubTransport()
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    promotion_dir = resolve_promotion_dir(promotion_id, create=False)
    plan_artifact = _load_plan(promotion_dir)
    validation_artifact = _load_validation(promotion_dir)
    plan_fp = _require_validation_matches_plan(
        validation_artifact=validation_artifact,
        plan_artifact=plan_artifact,
    )
    if not stdin.isatty() or not getattr(stdout, "isatty", lambda: False)():
        raise CreativeCodePRPromotionError("approval requires an interactive TTY.")
    current_login = github.current_login()
    if current_login != approved_by_login:
        raise CreativeCodePRPromotionError("current gh actor does not match approved_by_login.")
    phrase = f"APPROVE NON-DRAFT PR {plan_fp} {plan_artifact['patch_fingerprint'][7:15]}"
    print(f"Type exactly: {phrase}", file=stdout)
    typed = stdin.readline().strip()
    if typed != phrase:
        raise CreativeCodePRPromotionError("approval phrase mismatch.")
    approval_artifact: dict[str, Any] = build_creative_code_pr_promotion_approval(
        promotion_id=promotion_id,
        plan_fingerprint=plan_fp,
        validation_fingerprint=validation_artifact["validation_fingerprint"],
        approved_by_login=approved_by_login,
        confirmed_patch_fingerprint=plan_artifact["patch_fingerprint"],
        confirmed_base_commit_sha=plan_artifact["base_commit_sha"],
        confirmed_target_branch=plan_artifact["target_head_branch"],
    )
    write_json_atomic(
        resolve_promotion_file(promotion_dir, APPROVAL_FILE, for_write=True),
        approval_artifact,
    )
    return approval_artifact


def _commit_message(*, plan_artifact: dict[str, Any], approval: dict[str, Any]) -> str:
    return (
        f"experiment: promote {plan_artifact['selected_variant_id']}\n\n"
        f"Creative-Code-Result: {plan_artifact['source_result_id']}\n"
        f"Creative-Code-Patch: {plan_artifact['patch_fingerprint']}\n"
        f"Human-Promotion-Approval: {approval['approval_id']}\n"
        f"Co-authored-by: {RUNNER_COAUTHOR}\n"
    )


def promote(
    *,
    promotion_id: str,
    git: GitTransport | None = None,
    github: GitHubTransport | None = None,
) -> dict[str, Any]:
    git = git or GitTransport()
    github = github or GitHubTransport()
    promotion_dir = resolve_promotion_dir(promotion_id, create=False)
    receipt_path = resolve_promotion_file(promotion_dir, RECEIPT_FILE, for_write=True)
    plan_artifact = _load_plan(promotion_dir)
    validation_artifact = _load_validation(promotion_dir)
    approval_artifact = _load_approval(promotion_dir)
    plan_fp = promotion_plan_fingerprint(plan_artifact)
    _require_approval_matches_plan_and_validation(
        approval_artifact=approval_artifact,
        plan_artifact=plan_artifact,
        validation_artifact=validation_artifact,
    )
    if receipt_path.exists():
        receipt = cast(
            dict[str, Any],
            validate_creative_code_pr_promotion_receipt(read_json_object(receipt_path)),
        )
        _require_receipt_matches_plan_validation_approval(
            receipt=receipt,
            plan_artifact=plan_artifact,
            validation_artifact=validation_artifact,
            approval_artifact=approval_artifact,
        )
        _require_existing_receipt_live_pr(receipt=receipt, github=github)
        return receipt
    if approval_artifact["approved_by_login"] != github.current_login():
        raise CreativeCodePRPromotionError("current gh actor does not match approval.")
    if git.rev_parse_origin_main() != plan_artifact["base_commit_sha"]:
        raise CreativeCodePRPromotionError("origin/main drifted after approval.")
    branch = plan_artifact["target_head_branch"]
    if git.remote_branch_exists(branch) or git.local_branch_exists(branch):
        raise CreativeCodePRPromotionError("target experiment branch already exists.")
    human_name, human_email = git.human_identity()

    patch_text = _load_current_patch_text_for_plan(
        promotion_dir=promotion_dir,
        plan_artifact=plan_artifact,
    )
    pr_url = ""
    commit_sha = "0" * 40
    temp_upload_branch = ""
    temp_upload_pushed = False
    partial_failure: str | None = None
    commit_identity_verified = False
    target_ref_created = False
    try:
        checkout = _prepare_checkout(
            promotion_dir=promotion_dir,
            dirname=PROMOTION_CHECKOUT,
            base_commit_sha=plan_artifact["base_commit_sha"],
            git=git,
            branch=branch,
            promotion_remote=True,
        )
        _apply_patch_and_verify(
            checkout=checkout,
            patch_text=patch_text,
            changed_paths=plan_artifact["changed_paths"],
            git=git,
        )
        git.run(
            [
                "-c",
                f"user.name={human_name}",
                "-c",
                f"user.email={human_email}",
                "commit",
                "--no-gpg-sign",
                "-m",
                _commit_message(plan_artifact=plan_artifact, approval=approval_artifact),
            ],
            cwd=checkout,
        )
        commit_sha = git.run(["rev-parse", "HEAD"], cwd=checkout).stdout.strip()
        git.verify_commit_identity(
            cwd=checkout,
            expected_name=human_name,
            expected_email=human_email,
        )
        commit_identity_verified = True
        if git.remote_branch_exists(branch):
            raise CreativeCodePRPromotionError(
                "target experiment branch appeared before ref create."
            )
        temp_upload_branch = _derive_temp_upload_branch(
            target_branch=branch,
            commit_sha=commit_sha,
        )
        if git.remote_branch_exists(temp_upload_branch):
            raise CreativeCodePRPromotionError("temporary upload branch already exists.")
        temp_upload_pushed = True
        git.push_upload_branch(cwd=checkout, branch=temp_upload_branch)
        if git.remote_branch_exists(branch):
            raise CreativeCodePRPromotionError(
                "target experiment branch appeared before ref create."
            )
        github.create_branch_ref(branch=branch, commit_sha=commit_sha)
        target_ref_created = True
        _cleanup_temp_upload_ref(github, branch=temp_upload_branch)
        temp_upload_pushed = False
        body = _render_pr_body(
            promotion_id=promotion_id,
            result={
                "result_id": plan_artifact["source_result_id"],
                "patch_summary": {"patch_fingerprint": plan_artifact["patch_fingerprint"]},
            },
            branch=branch,
            changed_paths=plan_artifact["changed_paths"],
            validation_fingerprint=validation_artifact["validation_fingerprint"],
            approval_id=approval_artifact["approval_id"],
        )
        body_file = resolve_promotion_file(promotion_dir, PR_BODY_FILE, for_write=True)
        _write_text_atomic(body_file, body)
        pr_url = github.create_pull_request(
            head_branch=branch,
            title=plan_artifact["pull_request_title"],
            body_file=body_file,
        )
        readback = github.read_pull_request(pr_ref=pr_url)
        try:
            pull_request_number, pull_request_url = _require_open_pr_readback(
                readback,
                branch=branch,
                commit_sha=commit_sha,
                pr_url=pr_url,
                expected_number=None,
                error_message="created PR failed non-draft readback verification",
            )
        except CreativeCodePRPromotionError as exc:
            partial_failure = "created PR failed non-draft readback verification"
            raise CreativeCodePRPromotionError(partial_failure) from exc
        success_receipt: dict[str, Any] = build_creative_code_pr_promotion_receipt(
            promotion_id=promotion_id,
            plan_fingerprint=plan_fp,
            validation_fingerprint=validation_artifact["validation_fingerprint"],
            approval_id=approval_artifact["approval_id"],
            source_result_id=plan_artifact["source_result_id"],
            patch_fingerprint=plan_artifact["patch_fingerprint"],
            head_branch=branch,
            commit_sha=commit_sha,
            pull_request_number=pull_request_number,
            pull_request_url=pull_request_url,
            approved_by_login=approval_artifact["approved_by_login"],
        )
        write_json_atomic(receipt_path, success_receipt)
        return success_receipt
    except Exception as exc:
        if partial_failure is None:
            partial_failure = exc.__class__.__name__
        if target_ref_created and commit_sha != "0" * 40 and commit_identity_verified:
            receipt = build_creative_code_pr_promotion_receipt(
                promotion_id=promotion_id,
                plan_fingerprint=plan_fp,
                validation_fingerprint=validation_artifact["validation_fingerprint"],
                approval_id=approval_artifact["approval_id"],
                source_result_id=plan_artifact["source_result_id"],
                patch_fingerprint=plan_artifact["patch_fingerprint"],
                head_branch=branch,
                commit_sha=commit_sha,
                pull_request_number=0,
                pull_request_url=pr_url,
                approved_by_login=approval_artifact["approved_by_login"],
                partial_failure=partial_failure,
            )
            write_json_atomic(receipt_path, receipt)
        raise
    finally:
        if temp_upload_pushed and temp_upload_branch:
            _cleanup_temp_upload_ref(github, branch=temp_upload_branch)
        _destroy_checkout(promotion_dir, PROMOTION_CHECKOUT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan, validate, approve, or promote a PR-2 creative-code patch."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--patch-run", required=True)
    plan_parser.add_argument("--promotion-id", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--promotion-id", required=True)
    validate_parser.add_argument("--trusted-dispatch-result", type=Path)
    validate_parser.add_argument("--trusted-generation-receipt", type=Path)
    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("--promotion-id", required=True)
    approve_parser.add_argument("--approved-by-login", required=True)
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--promotion-id", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            plan(patch_run=args.patch_run, promotion_id=args.promotion_id)
            print(SUCCESS_PLAN_OUTPUT)
        elif args.command == "validate":
            validate(
                promotion_id=args.promotion_id,
                trusted_dispatch_result=args.trusted_dispatch_result,
                trusted_generation_receipt=args.trusted_generation_receipt,
            )
            print(SUCCESS_VALIDATE_OUTPUT)
        elif args.command == "approve":
            approve(promotion_id=args.promotion_id, approved_by_login=args.approved_by_login)
            print(SUCCESS_APPROVE_OUTPUT)
        elif args.command == "promote":
            promote(promotion_id=args.promotion_id)
            print(SUCCESS_PROMOTE_OUTPUT)
        else:  # pragma: no cover - argparse enforces choices.
            parser.error("unsupported command")
    except (
        CreativeCodePRPromotionError,
        CreativeCodePRPromotionContractError,
        CreativeCodePatchContractError,
        CreativeCodePatchWorkspaceError,
    ) as exc:
        print(f"FAIL: {args.command}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
