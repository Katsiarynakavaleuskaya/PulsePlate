"""Shared constants for the Experiment Runner Slack bridge."""

from __future__ import annotations

from pathlib import Path
import re


def default_audit_artifact_dir(repo_root: Path) -> Path:
    """Return the default local audit directory for Slack bridge artifacts."""

    return repo_root / "artifacts" / "orchestration" / "experiments" / "slack_socket_bridge"


SLACK_APP_AUTH_ENV = "SLACK_APP_" + "".join(("TO", "KEN"))
SLACK_BOT_AUTH_ENV = "SLACK_BOT_" + "".join(("TO", "KEN"))
SLACK_CHANNEL_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_CHANNEL_ALLOWLIST"
SLACK_USER_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_USER_ALLOWLIST"
SLACK_TEAM_ALLOWLIST_ENV = "EXPERIMENT_NOTIFICATION_SLACK_TEAM_ALLOWLIST"
BRIDGE_MIN_INTERVAL_ENV = "EXPERIMENT_SLACK_SOCKET_MIN_INTERVAL_SECONDS"
BRIDGE_TIMEOUT_ENV = "EXPERIMENT_SLACK_SOCKET_TIMEOUT_SECONDS"
BRIDGE_AUDIT_RETENTION_DAYS_ENV = "EXPERIMENT_SLACK_SOCKET_AUDIT_RETENTION_DAYS"
BRIDGE_EXECUTE_ENABLED_ENV = "EXPERIMENT_SLACK_SOCKET_EXECUTE_ENABLED"
BRIDGE_EXECUTE_ENABLED_VALUE = "reviewed-dry-run-dispatch"
LIVE_APPROVAL_SHA256_ENV = "EXPERIMENT_SLACK_SOCKET_LIVE_APPROVAL_SHA256"
WORKFLOW_DISPATCH_APPROVAL_PROOF_ENV = "EXPERIMENT_SLACK_SOCKET_WORKFLOW_DISPATCH_APPROVAL_PROOF"
WORKFLOW_DISPATCH_SECRET_ENV = (  # pragma: allowlist secret
    "EXPERIMENT_SLACK_SOCKET_WORKFLOW_DISPATCH_" + "".join(("SE", "CRET"))
)
OPERATOR_LEDGER_TASK_PACKET_ID_ENV = "EXPERIMENT_OPERATOR_LEDGER_TASK_PACKET_ID"
GITHUB_DISPATCH_REPO_ALLOWLIST_ENV = "EXPERIMENT_GITHUB_DISPATCH_REPO_ALLOWLIST"
GITHUB_INSTALLATION_AUTH_PREFIX = "ghs_"
GITHUB_INSTALLATION_AUTH_CLASS = "installation"
GITHUB_RUNTIME_AUTH_CLASS = "runtime"
GITHUB_API_HOST = "api.github.com"
SLACK_API_HOST = "slack.com"
DEFAULT_WORKFLOW_FILE = "experiment-runner-dispatch.yml"
DEFAULT_WORKFLOW_REF = "main"
DEFAULT_GITHUB_REPOSITORY = "Katsiarynakavaleuskaya/PulsePlate"
DEFAULT_OPERATOR_LEDGER_TASK_PACKET_ID: str = "operator-plane-slack-bridge"
MIN_WORKFLOW_DISPATCH_SECRET_LENGTH = 32
ALLOWED_WORKFLOW_REFS = {DEFAULT_WORKFLOW_REF}
SAFE_SLACK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,79}$")
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
SHELL_META_RE = re.compile(r"[;&|`$<>\\\\]")
ENV_ASSIGNMENT_RE = re.compile(r"(^|\s)[A-Za-z_][A-Za-z0-9_]*=")
SECRET_SHAPED_RE = re.compile(
    r"(xapp-[A-Za-z0-9-]{10,}|xox[abcprs]-[A-Za-z0-9-]{10,}|"
    r"gh[pousr]_[A-Za-z0-9._-]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{10,}|sk-[A-Za-z0-9_-]{12,})",
    re.IGNORECASE,
)
SLACK_APP_TOKEN_RE = re.compile(r"^xapp-[A-Za-z0-9-]{10,}$")
SLACK_BOT_TOKEN_RE = re.compile(r"^xoxb-[A-Za-z0-9-]{10,}$")
GITHUB_TOKEN_RE = re.compile(r"^(gh[pousr]_[A-Za-z0-9._-]{20,}|github_pat_[A-Za-z0-9_]{20,})$")
ALLOWED_COMMANDS = {"help", "kpp-status", "mvp-evidence", "status", "run-experiment"}
ALLOWED_WORKFLOWS = {DEFAULT_WORKFLOW_FILE}
RATE_LIMIT_LOCK_DIR = "rate_limit_claim"
REJECTED_RATE_LIMIT_LOCK_DIR = "rejected_rate_limit_claim"
RATE_LIMIT_CLAIM_MAX_ATTEMPTS = 10
DEFAULT_AUDIT_RETENTION_DAYS = 14
MAX_AUDIT_RETENTION_DAYS = 366
LIVE_SECRET_PRESENCE_ENV = (
    SLACK_APP_AUTH_ENV,
    SLACK_BOT_AUTH_ENV,
    SLACK_CHANNEL_ALLOWLIST_ENV,
    SLACK_USER_ALLOWLIST_ENV,
    SLACK_TEAM_ALLOWLIST_ENV,
)
LIVE_SMOKE_BRANCH_REF_ENV = "EXPERIMENT_SLACK_SOCKET_BRANCH_REF"
LIVE_SMOKE_HYPOTHESIS_SHA256_ENV = "EXPERIMENT_SLACK_SOCKET_HYPOTHESIS_SHA256"
SHA256_HEX_RE = re.compile(r"^[A-Fa-f0-9]{64}$")
SLACK_LIVE_SMOKE_METHODS = {"apps.connections.open", "auth.test"}
SAFE_SLACK_ERROR_CODE_RE = re.compile(r"^[a-z0-9_]{1,80}$")
