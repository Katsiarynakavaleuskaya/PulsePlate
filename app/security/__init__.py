"""Security module exports.

RU: Ленивые экспорты модуля безопасности.
EN: Lazy security module exports.

The orchestration tooling imports sandbox/control-plane helpers from this
package in lightweight Python environments. Keep FastAPI-bound exports lazy so
tooling imports do not pull runtime web dependencies unless explicitly used.
"""

from __future__ import annotations

from importlib import import_module
import sys
from typing import Any

_SUBMODULES = {
    "agent_control_plane": "app.security.agent_control_plane",
    "agent_input_guard": "app.security.agent_input_guard",
    "execution_sandbox": "app.security.execution_sandbox",
    "goplus_agentguard_bridge": "app.security.goplus_agentguard_bridge",
    "llm_monthly_quota": "app.security.llm_monthly_quota",
    "rate_limit": "app.security.rate_limit",
    "server_salt": "app.security.server_salt",
    "web_session": "app.security.web_session",
}

_AGENT_CONTROL_PLANE_MODULE = "app.security.agent_control_plane"

_EXPORT_MODULES = {
    "UNSAFE_AI_INPUT_DETAIL": "app.security.agent_input_guard",
    "AgentInputScanResult": "app.security.agent_input_guard",
    "AgentInputThreat": "app.security.agent_input_guard",
    "require_safe_ai_agent_input": "app.security.agent_input_guard",
    "scan_ai_agent_input": "app.security.agent_input_guard",
    "ALLOWLIST_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "AUDIT_SIGNING_KEY_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "AUDIT_LOG_PATH_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "BROKER_HMAC_KEY_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "DEFAULT_SCOPED_TOKEN_TTL_SECONDS": _AGENT_CONTROL_PLANE_MODULE,
    "EXECUTION_MODE_AUTO_SAFE": _AGENT_CONTROL_PLANE_MODULE,
    "EXECUTION_MODE_BLOCKED": _AGENT_CONTROL_PLANE_MODULE,
    "EXECUTION_MODE_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "EXECUTION_MODE_REVIEW_REQUIRED": _AGENT_CONTROL_PLANE_MODULE,
    "ExecutionModeDecision": _AGENT_CONTROL_PLANE_MODULE,
    "SCOPED_TTL_ENV": _AGENT_CONTROL_PLANE_MODULE,
    "IssuedScopedToken": _AGENT_CONTROL_PLANE_MODULE,
    "PolicyDecision": _AGENT_CONTROL_PLANE_MODULE,
    "SignedAuditEnvelope": _AGENT_CONTROL_PLANE_MODULE,
    "evaluate_policy": _AGENT_CONTROL_PLANE_MODULE,
    "issue_scoped_token": _AGENT_CONTROL_PLANE_MODULE,
    "load_allowlist_from_env": _AGENT_CONTROL_PLANE_MODULE,
    "normalize_execution_mode": _AGENT_CONTROL_PLANE_MODULE,
    "parse_allowlist": _AGENT_CONTROL_PLANE_MODULE,
    "persist_audit_envelope": _AGENT_CONTROL_PLANE_MODULE,
    "require_audit_secret": _AGENT_CONTROL_PLANE_MODULE,  # pragma: allowlist secret
    "require_execution_mode": _AGENT_CONTROL_PLANE_MODULE,
    "require_policy_allow": _AGENT_CONTROL_PLANE_MODULE,
    "require_scoped_token_ttl_seconds": _AGENT_CONTROL_PLANE_MODULE,
    "require_secrets_hmac_key": _AGENT_CONTROL_PLANE_MODULE,  # pragma: allowlist secret
    "sign_audit_envelope": _AGENT_CONTROL_PLANE_MODULE,
    "verify_audit_envelope": _AGENT_CONTROL_PLANE_MODULE,
    "DEFAULT_ALLOWED_BINARIES": "app.security.execution_sandbox",
    "DEFAULT_SANDBOX_MAX_OUTPUT_BYTES": "app.security.execution_sandbox",
    "DEFAULT_SANDBOX_TIMEOUT_SECONDS": "app.security.execution_sandbox",
    "SANDBOX_ALLOWED_BINARIES_ENV": "app.security.execution_sandbox",
    "SANDBOX_ENABLED_ENV": "app.security.execution_sandbox",
    "SANDBOX_MAX_OUTPUT_ENV": "app.security.execution_sandbox",
    "SANDBOX_ROOT_ENV": "app.security.execution_sandbox",
    "SANDBOX_TIMEOUT_ENV": "app.security.execution_sandbox",
    "SandboxRequest": "app.security.execution_sandbox",
    "SandboxResult": "app.security.execution_sandbox",
    "load_allowed_binaries": "app.security.execution_sandbox",
    "parse_allowed_binaries": "app.security.execution_sandbox",
    "require_sandbox_enabled": "app.security.execution_sandbox",
    "require_sandbox_max_output_bytes": "app.security.execution_sandbox",
    "require_sandbox_timeout_seconds": "app.security.execution_sandbox",
    "resolve_allowed_binary": "app.security.execution_sandbox",
    "resolve_sandbox_cwd": "app.security.execution_sandbox",
    "resolve_sandbox_root": "app.security.execution_sandbox",
    "run_local_sandbox": "app.security.execution_sandbox",
    "sanitize_sandbox_env": "app.security.execution_sandbox",
    "sandbox_enabled": "app.security.execution_sandbox",
    "RATE_LIMIT_429_RESPONSES": "app.security.rate_limit",
    "RATE_LIMIT_EXPORTS": "app.security.rate_limit",
    "RATE_LIMIT_INSIGHT": "app.security.rate_limit",
    "limit_if_available": "app.security.rate_limit",
    "limiter": "app.security.rate_limit",
    "rate_limit_client_key": "app.security.rate_limit",  # pragma: allowlist secret
    "wire_rate_limiting": "app.security.rate_limit",
}

_FASTAPI_BOUND_MODULES = {
    "app.security.agent_input_guard",
    "app.security.rate_limit",
    "app.security.web_session",
}

__all__ = [
    "limiter",
    "rate_limit_client_key",
    "wire_rate_limiting",
    "limit_if_available",
    "RATE_LIMIT_INSIGHT",
    "RATE_LIMIT_EXPORTS",
    "RATE_LIMIT_429_RESPONSES",
    "UNSAFE_AI_INPUT_DETAIL",
    "AgentInputThreat",
    "AgentInputScanResult",
    "scan_ai_agent_input",
    "require_safe_ai_agent_input",
    "ALLOWLIST_ENV",
    "AUDIT_SIGNING_KEY_ENV",
    "AUDIT_LOG_PATH_ENV",
    "BROKER_HMAC_KEY_ENV",
    "EXECUTION_MODE_ENV",
    "EXECUTION_MODE_AUTO_SAFE",
    "EXECUTION_MODE_REVIEW_REQUIRED",
    "EXECUTION_MODE_BLOCKED",
    "SCOPED_TTL_ENV",
    "DEFAULT_SCOPED_TOKEN_TTL_SECONDS",
    "PolicyDecision",
    "SignedAuditEnvelope",
    "IssuedScopedToken",
    "ExecutionModeDecision",
    "parse_allowlist",
    "load_allowlist_from_env",
    "evaluate_policy",
    "normalize_execution_mode",
    "require_execution_mode",
    "require_policy_allow",
    "require_audit_secret",
    "require_secrets_hmac_key",
    "require_scoped_token_ttl_seconds",
    "sign_audit_envelope",
    "verify_audit_envelope",
    "persist_audit_envelope",
    "issue_scoped_token",
    "SANDBOX_ENABLED_ENV",
    "SANDBOX_ROOT_ENV",
    "SANDBOX_TIMEOUT_ENV",
    "SANDBOX_MAX_OUTPUT_ENV",
    "SANDBOX_ALLOWED_BINARIES_ENV",
    "DEFAULT_SANDBOX_TIMEOUT_SECONDS",
    "DEFAULT_SANDBOX_MAX_OUTPUT_BYTES",
    "DEFAULT_ALLOWED_BINARIES",
    "SandboxRequest",
    "SandboxResult",
    "sandbox_enabled",
    "require_sandbox_enabled",
    "require_sandbox_timeout_seconds",
    "require_sandbox_max_output_bytes",
    "parse_allowed_binaries",
    "load_allowed_binaries",
    "resolve_sandbox_root",
    "resolve_sandbox_cwd",
    "resolve_allowed_binary",
    "sanitize_sandbox_env",
    "run_local_sandbox",
]


def _import_security_module(module_path: str) -> Any:
    try:
        return import_module(module_path)
    except ImportError as exc:
        exc_name = getattr(exc, "name", "")
        if module_path in _FASTAPI_BOUND_MODULES and (
            exc_name == "fastapi" or "fastapi" in str(exc).lower()
        ):
            raise ImportError(
                f"{module_path} requires FastAPI/runtime dependencies, but FastAPI is "
                f"not importable with interpreter {sys.executable!r}. Use repo Python "
                "via an absolute VENV_PYTHON or the repo .venv before importing "
                "FastAPI-bound security exports."
            ) from exc
        raise


def __getattr__(name: str) -> Any:
    """Load security submodules and public symbols only when requested."""

    if name in _SUBMODULES:
        module = _import_security_module(_SUBMODULES[name])
        globals()[name] = module
        return module

    module_path = _EXPORT_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(_import_security_module(module_path), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable completion output without importing FastAPI-bound modules."""

    return sorted({*globals(), *_SUBMODULES, *_EXPORT_MODULES, *__all__})
