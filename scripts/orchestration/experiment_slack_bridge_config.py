"""Configuration and runtime validation helpers for the Slack bridge."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import re
from typing import cast

from scripts.orchestration.experiment_slack_bridge_constants import (
    ALLOWED_WORKFLOW_REFS,
    ALLOWED_WORKFLOWS,
    BRIDGE_AUDIT_RETENTION_DAYS_ENV,
    BRIDGE_MIN_INTERVAL_ENV,
    BRIDGE_TIMEOUT_ENV,
    CONTROL_CHAR_RE,
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_GITHUB_REPOSITORY,
    DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID,
    DEFAULT_WORKFLOW_FILE,
    DEFAULT_WORKFLOW_REF,
    GITHUB_DISPATCH_REPO_ALLOWLIST_ENV,
    GITHUB_INSTALLATION_AUTH_CLASS,
    GITHUB_INSTALLATION_AUTH_PREFIX,
    GITHUB_TOKEN_RE,
    GITHUB_RUNTIME_AUTH_CLASS,
    LIVE_APPROVAL_SHA256_ENV,
    LIVE_SECRET_PRESENCE_ENV,
    MAX_AUDIT_RETENTION_DAYS,
    OPERATOR_LEDGER_TASK_PACKET_ID_ENV,
    SAFE_BRANCH_RE,
    SAFE_SLACK_ID_RE,
    SECRET_SHAPED_RE,
    SHA256_HEX_RE,
    SHELL_META_RE,
    SLACK_APP_AUTH_ENV,
    SLACK_APP_TOKEN_RE,
    SLACK_BOT_AUTH_ENV,
    SLACK_BOT_TOKEN_RE,
    SLACK_CHANNEL_ALLOWLIST_ENV,
    SLACK_TEAM_ALLOWLIST_ENV,
    SLACK_USER_ALLOWLIST_ENV,
)
from scripts.orchestration.experiment_slack_bridge_models import (
    BridgeConfig,
    GitHubDispatchAuth,
    GitHubDispatchAuthClass,
    GitHubDispatchConfig,
    GitHubDispatchTarget,
    SlackSocketAuditError,
    SlackSocketConfigError,
    _sha256_text,
)
from scripts.orchestration.experiment_slack_redaction import SLACK_IDENTIFIER_RE


def _normalize_slack_id(raw_value: str, *, label: str) -> str:
    value = raw_value.strip()
    if not value or CONTROL_CHAR_RE.search(value) or not SAFE_SLACK_ID_RE.fullmatch(value):
        raise SlackSocketConfigError(f"{label} allowlist is invalid.")
    return value


def _allowlist_from_env(env_name: str, *, label: str) -> frozenset[str]:
    raw = os.environ.get(env_name, "")
    if not raw.strip():
        return frozenset()
    values: set[str] = set()
    for candidate in raw.split(","):
        candidate = candidate.strip()
        if not candidate:
            raise SlackSocketConfigError(f"{label} allowlist is invalid.")
        values.add(_normalize_slack_id(candidate, label=label))
    return frozenset(values)


def _optional_token(env_name: str) -> str | None:
    token = os.environ.get(env_name, "").strip()
    if not token:
        return None
    token_pattern = {
        SLACK_APP_AUTH_ENV: SLACK_APP_TOKEN_RE,
        SLACK_BOT_AUTH_ENV: SLACK_BOT_TOKEN_RE,
    }.get(env_name)
    if token_pattern is None:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    if CONTROL_CHAR_RE.search(token) or "`" in token or token_pattern.fullmatch(token) is None:
        raise SlackSocketConfigError(f"{env_name} token class is invalid.")
    return token


def _github_auth() -> GitHubDispatchAuth | None:
    for env_name in ("GH_TOKEN", "GITHUB_TOKEN"):
        raw_token = os.environ.get(env_name)
        if raw_token is None or not raw_token.strip():
            continue
        token = raw_token.strip()
        if (
            CONTROL_CHAR_RE.search(token)
            or "`" in token
            or GITHUB_TOKEN_RE.fullmatch(token) is None
        ):
            raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
        auth_class = cast(
            GitHubDispatchAuthClass,
            (
                GITHUB_INSTALLATION_AUTH_CLASS
                if token.startswith(GITHUB_INSTALLATION_AUTH_PREFIX)
                else GITHUB_RUNTIME_AUTH_CLASS
            ),
        )
        return GitHubDispatchAuth(
            token=token,
            source_env=env_name,
            auth_class=auth_class,
        )
    return None


def _github_token() -> str | None:
    auth = _github_auth()
    if auth is None:
        return None
    return cast(str, auth.token)


def _live_approval_sha256() -> str | None:
    """Read and validate the live-dispatch approval digest from runtime env."""

    raw = os.environ.get(LIVE_APPROVAL_SHA256_ENV, "").strip()
    if not raw or raw.lower() == "none":
        return None
    normalized = raw.lower()
    if (
        CONTROL_CHAR_RE.search(normalized)
        or "`" in normalized
        or SHA256_HEX_RE.fullmatch(normalized) is None
    ):
        raise SlackSocketConfigError("Slack live-dispatch approval configuration is invalid.")
    return normalized


def _operator_ledger_task_packet_id() -> str:
    """Read the local operator-ledger task packet id without promoting it to authority."""

    raw = os.environ.get(OPERATOR_LEDGER_TASK_PACKET_ID_ENV)
    if raw is None or raw == "":
        return cast(str, DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID)
    if raw != raw.strip() or len(raw) > 64:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    if not all(char.isalnum() or char in {"-", "_"} for char in raw):
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    if (
        SLACK_IDENTIFIER_RE.search(raw)
        or SECRET_SHAPED_RE.search(raw)
        or SHA256_HEX_RE.fullmatch(raw.lower())
    ):
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    return raw


def _compute_live_approval_digest(branch_ref: str, hypothesis: str) -> str:
    """Compute the canonical approval digest for a branch + hypothesis pair."""

    return cast(str, _sha256_text(branch_ref + "\0" + hypothesis))


def _positive_int_from_env(env_name: str, default: int, *, maximum: int) -> int:
    raw = os.environ.get(env_name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.") from exc
    if value <= 0 or value > maximum:
        raise SlackSocketConfigError("Slack operator bridge configuration is invalid.")
    return value


def _normalized_absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _reject_symlinked_existing_path(root: Path, candidate: Path, *, message: str) -> None:
    current = root
    if current.is_symlink():
        raise SlackSocketAuditError(message)
    for part in candidate.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise SlackSocketAuditError(message)


def _reject_symlinked_output_components(
    candidate: Path,
    *,
    artifact_dir: Path,
    repo_root: Path,
) -> None:
    repo_root = _normalized_absolute_path(Path(repo_root))
    artifact_root = _normalized_absolute_path(repo_root / "artifacts" / "orchestration")
    artifact_dir = _normalized_absolute_path(artifact_dir)
    candidate = _normalized_absolute_path(candidate)
    try:
        artifact_root.relative_to(repo_root)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        repo_root,
        artifact_root,
        message="Slack operator audit ancestors must not be symlinks.",
    )
    try:
        artifact_dir.relative_to(artifact_root)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        artifact_root,
        artifact_dir,
        message="Slack operator audit ancestors must not be symlinks.",
    )
    try:
        candidate.relative_to(artifact_dir)
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator audit directory must stay under artifacts/orchestration."
        ) from exc
    _reject_symlinked_existing_path(
        artifact_dir,
        candidate,
        message="Slack operator audit path must not traverse a symlink.",
    )


def _resolve_audit_dir(
    raw_audit_dir: str | None,
    *,
    repo_root: Path,
    audit_artifact_dir: Path,
) -> Path:
    base_dir = _normalized_absolute_path(Path(audit_artifact_dir))
    candidate: Path = Path(raw_audit_dir).expanduser() if raw_audit_dir else base_dir
    if not candidate.is_absolute():
        candidate = _normalized_absolute_path(repo_root / candidate)
    else:
        candidate = _normalized_absolute_path(candidate)
    try:
        candidate.relative_to(_normalized_absolute_path(repo_root / "artifacts" / "orchestration"))
    except ValueError as exc:
        raise SlackSocketAuditError(
            "Slack operator bridge audit directory must stay under artifacts/orchestration."
        ) from exc
    return candidate


def _is_safe_ref(value: str) -> bool:
    if (
        not value
        or CONTROL_CHAR_RE.search(value)
        or SHELL_META_RE.search(value)
        or not SAFE_BRANCH_RE.fullmatch(value)
        or value.startswith(("-", "/", "."))
        or value.endswith(("/", "."))
        or ".." in value
        or "//" in value
        or "@{" in value
        or value.startswith("refs/")
    ):
        return False
    return all(
        part not in {"", ".", ".."} and not part.startswith(".") for part in value.split("/")
    )


def _validate_workflow_ref(ref: str) -> str:
    if ref not in ALLOWED_WORKFLOW_REFS or not _is_safe_ref(ref):
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return ref


def _validate_workflow_file(workflow_file: str) -> str:
    if workflow_file not in ALLOWED_WORKFLOWS:
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return workflow_file


def _validate_repo(raw_repo: str | None) -> str | None:
    if raw_repo is None or raw_repo == "":
        return None
    if raw_repo != raw_repo.strip():
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    repo = raw_repo
    if (
        CONTROL_CHAR_RE.search(repo)
        or SHELL_META_RE.search(repo)
        or "%" in repo
        or "\\" in repo
        or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
    ):
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    owner, name = repo.split("/", maxsplit=1)
    if any(
        part in {"", ".", ".."} or part.startswith(".") or part.endswith(".") or ".." in part
        for part in (owner, name)
    ):
        raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
    return repo


def _github_dispatch_repo_allowlist() -> frozenset[str]:
    raw_allowlist = os.environ.get(GITHUB_DISPATCH_REPO_ALLOWLIST_ENV, "")
    if not raw_allowlist.strip():
        return frozenset()
    values: set[str] = set()
    for candidate in raw_allowlist.split(","):
        if not candidate or candidate != candidate.strip():
            raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
        repo = _validate_repo(candidate)
        if repo is None:
            raise SlackSocketConfigError("GitHub dispatch configuration is invalid.")
        values.add(repo)
    return frozenset(values)


def build_config(
    *,
    dispatch_mode: str,
    repo_root: Path,
    audit_artifact_dir: Path,
    audit_dir: str | None = None,
    repo: str | None = None,
    workflow_file: str = DEFAULT_WORKFLOW_FILE,
    workflow_ref: str = DEFAULT_WORKFLOW_REF,
) -> BridgeConfig:
    """Read sanitized bridge config from runtime env."""

    if dispatch_mode not in {"dry-run", "execute"}:
        raise SlackSocketConfigError("Slack operator bridge dispatch mode is invalid.")
    github_auth = _github_auth()
    repo_allowlist = _github_dispatch_repo_allowlist()
    workflow_file_value = _validate_workflow_file(workflow_file)
    workflow_ref_value = _validate_workflow_ref(workflow_ref)
    target_repo = _validate_repo(repo if repo is not None else os.environ.get("GITHUB_REPOSITORY"))
    current_repo = _validate_repo(os.environ.get("GITHUB_REPOSITORY")) or DEFAULT_GITHUB_REPOSITORY
    github_target = (
        GitHubDispatchTarget(
            repo=target_repo,
            workflow_file=workflow_file_value,
            workflow_ref=workflow_ref_value,
            current_repo=current_repo,
            repo_allowlist=repo_allowlist,
        )
        if target_repo is not None
        else None
    )
    return BridgeConfig(
        dispatch_mode=dispatch_mode,
        allowed_channels=_allowlist_from_env(SLACK_CHANNEL_ALLOWLIST_ENV, label="channel"),
        allowed_users=_allowlist_from_env(SLACK_USER_ALLOWLIST_ENV, label="user"),
        allowed_teams=_allowlist_from_env(SLACK_TEAM_ALLOWLIST_ENV, label="team"),
        audit_dir=_resolve_audit_dir(
            audit_dir,
            repo_root=repo_root,
            audit_artifact_dir=audit_artifact_dir,
        ),
        repo=target_repo,
        workflow_file=workflow_file_value,
        workflow_ref=workflow_ref_value,
        timeout_seconds=_positive_int_from_env(BRIDGE_TIMEOUT_ENV, 10, maximum=30),
        min_interval_seconds=_positive_int_from_env(
            BRIDGE_MIN_INTERVAL_ENV,
            60,
            maximum=3600,
        ),
        audit_retention_days=_positive_int_from_env(
            BRIDGE_AUDIT_RETENTION_DAYS_ENV,
            DEFAULT_AUDIT_RETENTION_DAYS,
            maximum=MAX_AUDIT_RETENTION_DAYS,
        ),
        slack_app_token=_optional_token(SLACK_APP_AUTH_ENV),
        slack_bot_token=_optional_token(SLACK_BOT_AUTH_ENV),
        github_token=github_auth.token if github_auth is not None else None,
        live_approval_sha256=_live_approval_sha256(),
        operator_ledger_task_packet_id=_operator_ledger_task_packet_id(),
        github_dispatch=GitHubDispatchConfig(auth=github_auth, target=github_target),
    )


def validate_secret_presence(
    *,
    config_builder: Callable[..., BridgeConfig],
    required_env: tuple[str, ...] = LIVE_SECRET_PRESENCE_ENV,
) -> dict[str, object]:
    """Return a value-free live-smoke secret/allowlist presence report."""

    present = {env_name: bool(os.environ.get(env_name, "").strip()) for env_name in required_env}
    missing = [env_name for env_name, is_present in present.items() if not is_present]
    status = "pass" if not missing else "fail"
    if not missing:
        try:
            config = config_builder(dispatch_mode="dry-run")
        except (SlackSocketAuditError, SlackSocketConfigError):
            missing = list(required_env)
            status = "fail"
        else:
            if (
                config.slack_app_token is None
                or config.slack_bot_token is None
                or not config.allowed_channels
                or not config.allowed_users
                or not config.allowed_teams
            ):
                missing = list(required_env)
                status = "fail"
    return {
        "missing_env": missing,
        "required_env_present": present,
        "status": status,
    }
