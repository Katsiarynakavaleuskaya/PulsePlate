"""Advisory review-source status helpers for PR review context.

These helpers describe degraded review-source evidence. They do not grant
posting, review-thread resolution, or merge-readiness authority.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import re
from types import MappingProxyType
from typing import Mapping

DEGRADED_STATUSES = frozenset(
    {"degraded", "unavailable", "rate_limited", "usage_limit_reached", "auth_missing", "partial"}
)
BLOCKING_STATUSES = frozenset(
    {"fallback_finding", "failed_required_check", "unresolved_threads", "actionable_bot_comments"}
)
REVIEW_SOURCE_STATUSES = frozenset({"available"}) | DEGRADED_STATUSES | BLOCKING_STATUSES
REVIEW_SOURCE_POLICY_VERSION = "pulseplate.review-source-policy/v1"
TERMINAL_NONBLOCKING_STATUSES = frozenset({"rate_limited", "usage_limit_reached"})
_CODEX_REVIEW_SOURCE_UNAVAILABILITY_BODY_STATUSES: Mapping[str, str] = MappingProxyType(
    {
        (
            "Codex usage limits have been reached for code reviews. "
            "Please check with the admins of this repo to increase the limits by adding credits."
        ): "usage_limit_reached",
        (
            "Codex usage limits have been reached for code reviews. "
            "Please check with the admins of this repo to increase the limits by adding credits.\n"
            "Credits must be used to enable repository wide code reviews."
        ): "usage_limit_reached",
        (
            "You have reached your Codex usage limits for code reviews. "
            "You can see your limits in the "
            "[Codex usage dashboard](https://chatgpt.com/codex/cloud/settings/usage)."
        ): "usage_limit_reached",
    }
)
_SECRETISH_RE = re.compile(
    r"(?i)(github_pat_[a-z0-9_]+|gh[opsru]_[a-z0-9_]+|ghp_[a-z0-9_]+|"
    r"ghs_[a-z0-9_.-]+|sk-[a-z0-9_-]+|"
    r"\b(?:token|secret|password|api[_-]?key|github_token|gh_token)\b\s*[:=]\s*[^\s]+)"
)
_LOCAL_PATH_RE = re.compile(
    r"(?i)(file://)?("
    r"/(?:Users|private|var|tmp|Volumes)/[^\s,;]+|"
    r"~[\\/][^\s,;]+|"
    r"[A-Za-z]:[\\/][^\s,;]+"
    r")"
)


@dataclass(frozen=True)
class ReviewSourceStatus:
    source: str
    status: str
    source_degraded: bool
    fallback_required: bool
    blocking: bool
    reason: str
    evidence: str


def review_source_policy_projection() -> dict[str, object]:
    """Return the versioned, machine-checkable review-source policy."""

    return {
        "blocking_statuses": sorted(BLOCKING_STATUSES),
        "policy_version": REVIEW_SOURCE_POLICY_VERSION,
        "terminal_nonblocking_statuses": sorted(TERMINAL_NONBLOCKING_STATUSES),
        "terminal_unavailability": {
            "blocking": False,
            "fallback_required": False,
            "operator_override_required": False,
            "prior_review_required": False,
            "retry_required": False,
            "review_claim": "none",
            "source_degraded": True,
            "substitute_review_required": False,
            "ttl_required": False,
        },
    }


def classify_codex_review_source_unavailability_body(body: str) -> str:
    """Map an exact trusted Codex quota body to its closed source status."""

    if not isinstance(body, str):
        raise ValueError("Codex review-source response body must be a string")
    try:
        return _CODEX_REVIEW_SOURCE_UNAVAILABILITY_BODY_STATUSES[body]
    except KeyError as exc:
        raise ValueError(
            "Codex review-source response is not an exact known quota response"
        ) from exc


def redact_review_source_text(value: str) -> str:
    """Redact token-like values from advisory review-source metadata."""

    redacted = _SECRETISH_RE.sub("<redacted>", value)
    return _LOCAL_PATH_RE.sub("<redacted-path>", redacted)


def build_review_source_status(
    *,
    source: str,
    available: bool | None = None,
    status: str | None = None,
    reason: str = "",
    evidence: str = "",
    degraded: bool = False,
    blocking: bool = False,
) -> dict[str, object]:
    """Return stable advisory status metadata for one review source."""

    normalized_status = (status or "").strip().lower().replace("-", "_")
    if not normalized_status:
        if available and not degraded:
            normalized_status = "available"
        elif available:
            normalized_status = "degraded"
        else:
            normalized_status = "unavailable"
    if normalized_status not in REVIEW_SOURCE_STATUSES:
        allowed = ", ".join(sorted(REVIEW_SOURCE_STATUSES))
        raise ValueError(f"status must be one of: {allowed}.")
    source_degraded = degraded or normalized_status in DEGRADED_STATUSES
    source_blocking = blocking or normalized_status in BLOCKING_STATUSES
    redacted_reason = redact_review_source_text(reason)
    redacted_evidence = redact_review_source_text(evidence)

    return asdict(
        ReviewSourceStatus(
            source=source,
            status=normalized_status,
            source_degraded=source_degraded,
            fallback_required=source_blocking
            or (source_degraded and normalized_status not in TERMINAL_NONBLOCKING_STATUSES),
            blocking=source_blocking,
            reason=redacted_reason,
            evidence=redacted_evidence,
        )
    )


def summarize_degraded_sources(sources: list[dict[str, object]]) -> list[str]:
    """Return deterministic human-readable summaries for degraded sources."""

    summaries: list[str] = []
    for source in sources:
        if not bool(source.get("source_degraded")):
            continue
        name = str(source.get("source") or "unknown")
        status = str(source.get("status") or "unknown")
        reason = str(source.get("reason") or "no reason provided")
        summaries.append(f"{name}: {status} ({reason})")
    return summaries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit advisory PulsePlate review-source status JSON without side effects."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--status", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--evidence", default="")
    parser.add_argument("--blocking", action="store_true")
    args = parser.parse_args(argv)
    print(
        json.dumps(
            build_review_source_status(
                source=args.source,
                status=args.status or None,
                reason=args.reason,
                evidence=args.evidence,
                blocking=args.blocking,
            ),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by py_compile/CLI smoke gates.
    raise SystemExit(main())
