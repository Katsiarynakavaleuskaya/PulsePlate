#!/usr/bin/env python3
"""Deterministic Slack Block Kit renderer for Experiment Runner KPP outcomes.

RU: Генерирует deterministic JSON Block Kit сообщений для KPP (Key Performance
Point) нотификаций Experiment Runner. Все секреты, пути, патчи и сырые логи
редэктируются.
EN: Generates deterministic JSON Block Kit messages for Experiment Runner KPP
(Key Performance Point) notifications. All secrets, paths, patches, and raw
logs are redacted.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from scripts.orchestration.experiment_slack_redaction import slack_text as _slack_text

KPP_PROMOTE = "PROMOTE"
KPP_DEFER = "DEFER"
KPP_DISCARD = "DISCARD"
KPP_FAIL = "FAIL"
KPP_ORACLE_VIOLATION = "ORACLE_VIOLATION"
KPP_SURFACE_BREACH = "SURFACE_BREACH"

KPP_OUTCOMES: tuple[str, ...] = (
    KPP_PROMOTE,
    KPP_DEFER,
    KPP_DISCARD,
    KPP_FAIL,
    KPP_ORACLE_VIOLATION,
    KPP_SURFACE_BREACH,
)

SECURITY_SENSITIVE_OUTCOMES: frozenset[str] = frozenset(
    {
        KPP_ORACLE_VIOLATION,
        KPP_SURFACE_BREACH,
    }
)

REDACTION_NOTICE = (
    "No sensitive user data, raw Slack identifiers, raw hypotheses, tokens, local paths, "
    "oracle output, or patch markers included."
)
ACTION_REQUIRED_COPY = "Human review required"
NO_MERGE_ACTION_COPY = "No merge/deploy/payment action was performed"
NO_SENSITIVE_DATA_COPY = "No sensitive user data included"
ARTIFACT_REFERENCE_COPY = "Artifact reference only; raw logs are not posted to Slack"
SLACK_SECTION_TEXT_LIMIT = 3000
_SLACK_TRUNCATION_MARKER = " [truncated=true]"


class KPPRenderError(RuntimeError):
    """KPP block rendering contract violation."""


def _slack_section_text(text: str, *, limit: int = SLACK_SECTION_TEXT_LIMIT) -> str:
    """Bound Slack section text while preserving already-redacted formatting."""

    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= len(_SLACK_TRUNCATION_MARKER):
        return _SLACK_TRUNCATION_MARKER[:limit]
    return text[: limit - len(_SLACK_TRUNCATION_MARKER)].rstrip() + _SLACK_TRUNCATION_MARKER


def _artifact_action_section_text(
    artifact_refs: tuple[str, ...],
    action_required: str,
    *,
    limit: int = SLACK_SECTION_TEXT_LIMIT,
) -> str:
    """Bound artifact references without dropping the required operator action."""

    action_suffix = f"\n\n*Action required:*\n{_slack_text(action_required)}"
    artifact_limit = limit - len(action_suffix)
    if artifact_limit <= 0:
        return _slack_section_text(action_suffix.lstrip(), limit=limit)

    artifact_lines = artifact_refs or ("none",)
    artifact_text = "\n".join(f"- `{_slack_text(line)}`" for line in artifact_lines)
    artifact_section = _slack_section_text(
        f"*Artifact/reference:*\n{artifact_text}",
        limit=artifact_limit,
    )
    return f"{artifact_section}{action_suffix}"


@dataclass(frozen=True)
class KPPSlackBlockMessage:
    """Deterministic KPP Slack Block Kit message payload."""

    kpp_outcome: str
    experiment_id: str
    header: str
    status_text: str
    kpp_class: str
    failure_class: str | None
    scope: str
    evidence_summary: tuple[str, ...]
    action_required: str
    artifact_refs: tuple[str, ...] = ()
    redaction_notice: str = REDACTION_NOTICE
    no_merge_action: str = NO_MERGE_ACTION_COPY
    no_sensitive_data: str = NO_SENSITIVE_DATA_COPY
    artifact_reference_only: str = ARTIFACT_REFERENCE_COPY

    def as_blocks_json(self) -> str:
        """Render stable Slack Block Kit JSON without untrusted formatting."""

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": _slack_text(self.header, limit=150),
                    "emoji": False,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Outcome:*\n`{_slack_text(self.kpp_outcome)}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{_slack_text(self.status_text)}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*KPP class:*\n`{_slack_text(self.kpp_class)}`",
                    },
                ],
            },
        ]

        if self.failure_class is not None:
            blocks[1]["fields"].append(
                {
                    "type": "mrkdwn",
                    "text": f"*Failure class:*\n`{_slack_text(self.failure_class)}`",
                }
            )

        evidence_lines = self.evidence_summary or ("none",)
        evidence_text = "\n".join(f"- {_slack_text(line)}" for line in evidence_lines)

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": _slack_section_text(
                        f"*Scope:*\n{_slack_text(self.scope)}\n\n"
                        f"*Evidence summary:*\n{evidence_text}"
                    ),
                },
            }
        )

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": _artifact_action_section_text(
                        self.artifact_refs,
                        self.action_required,
                    ),
                },
            }
        )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f":information_source: {_slack_text(self.redaction_notice)}\n"
                            f":white_check_mark: {_slack_text(self.no_merge_action)}\n"
                            f":lock: {_slack_text(self.no_sensitive_data)}\n"
                            f":page_facing_up: {_slack_text(self.artifact_reference_only)}"
                        ),
                    }
                ],
            }
        )

        return json.dumps({"blocks": blocks}, sort_keys=True, separators=(",", ":"))


def _validate_kpp_outcome(outcome: str) -> str:
    normalized = str(outcome).strip().upper()
    if normalized not in KPP_OUTCOMES:
        allowed = ", ".join(KPP_OUTCOMES)
        raise KPPRenderError(f"KPP outcome must be one of: {allowed}, got {outcome!r}.")
    return normalized


def _validate_experiment_id(value: str) -> str:
    experiment_id = str(value).strip()
    if not experiment_id:
        raise KPPRenderError("experiment_id must be non-empty.")
    if len(experiment_id) > 64:
        raise KPPRenderError("experiment_id must be at most 64 characters.")
    if not re.fullmatch(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", experiment_id):
        raise KPPRenderError(
            "experiment_id must contain only ASCII letters, digits, hyphens, "
            "and underscores, and must not contain path separators."
        )
    return experiment_id


def render_kpp_block_message(
    *,
    kpp_outcome: str,
    experiment_id: str,
    failure_class: str | None = None,
    scope: str = "",
    evidence_summary: tuple[str, ...] = (),
    artifact_refs: tuple[str, ...] = (),
    action_required: str | None = None,
) -> KPPSlackBlockMessage:
    """Render a deterministic KPP Slack Block Kit message for a given outcome."""

    outcome = _validate_kpp_outcome(kpp_outcome)
    experiment_id = _validate_experiment_id(experiment_id)

    if failure_class is not None:
        failure_class = str(failure_class).strip()
        if not failure_class:
            failure_class = None

    default_scope = "Experiment Runner KPP outcome; Slack display-only boundary."
    scope = str(scope).strip() if scope else default_scope

    if not evidence_summary:
        evidence_summary = ("No additional evidence provided.",)

    if outcome == KPP_PROMOTE:
        header = f"KPP PROMOTE: {experiment_id}"
        status_text = "High-signal experiment result ready for promotion review."
        kpp_class = "promotion_candidate"
        default_action = (
            "Review durable artifact and run promotion gate before any PR or merge action."
        )
    elif outcome == KPP_DEFER:
        header = f"KPP DEFER: {experiment_id}"
        status_text = "Experiment result deferred to backlog or follow-up lane."
        kpp_class = "deferred_candidate"
        default_action = "Check backlog ledger for deferred item and assigned target PR."
    elif outcome == KPP_DISCARD:
        header = f"KPP DISCARD: {experiment_id}"
        status_text = "Experiment result discarded; falsification or no-signal outcome."
        kpp_class = "discarded_candidate"
        default_action = "No further action required unless falsification reason is disputed."
    elif outcome == KPP_FAIL:
        header = f"KPP FAIL: {experiment_id}"
        status_text = "Experiment result failed; review failure class and safe artifact reference."
        kpp_class = "failed_candidate"
        default_action = "Inspect local artifact reference only; raw logs are not posted to Slack."
    elif outcome == KPP_ORACLE_VIOLATION:
        header = f"SECURITY ALERT: ORACLE_VIOLATION: {experiment_id}"
        status_text = "Oracle-only governance reviewer detected an oracle contract violation."
        kpp_class = "security_oracle_violation"
        default_action = (
            "Escalate to security auditor and coordinator immediately; no autonomous action."
        )
    elif outcome == KPP_SURFACE_BREACH:
        header = f"SECURITY ALERT: SURFACE_BREACH: {experiment_id}"
        status_text = "Experiment candidate attempted mutation outside allowed mutable surface."
        kpp_class = "security_surface_breach"
        default_action = (
            "Escalate to security auditor and coordinator immediately; no autonomous action."
        )
    else:
        allowed = ", ".join(KPP_OUTCOMES)
        raise KPPRenderError(f"Unhandled KPP outcome: must be one of {allowed}.")

    if action_required is None:
        action_required = default_action

    return KPPSlackBlockMessage(
        kpp_outcome=outcome,
        experiment_id=experiment_id,
        header=header,
        status_text=status_text,
        kpp_class=kpp_class,
        failure_class=failure_class,
        scope=scope,
        evidence_summary=evidence_summary,
        action_required=action_required,
        artifact_refs=artifact_refs,
    )


def route_kpp_outcome_from_result(
    result: dict[str, Any],
    promotion: dict[str, Any] | None = None,
) -> str:
    """Map an experiment result dict to a canonical KPP outcome string.

    RU: Определяет KPP outcome на основе result статуса, failure_class и
    признаков нарушений. Это чистая функция без side effects.
    EN: Determines KPP outcome from result status, failure_class, and violation
    indicators. Pure function with no side effects.
    """

    status = str(result.get("status", "")).strip()
    failure_class = result.get("failure_class")
    failure_class_str = str(failure_class).strip() if failure_class is not None else ""
    promotion_disposition = ""
    if promotion is not None:
        promotion_disposition = str(promotion.get("disposition", "")).strip().lower()

    runner_mode = str(result.get("runner_mode", "")).strip()
    mutated_paths = result.get("mutated_paths", [])

    if (
        runner_mode == "oracle_only_governance_reviewer"
        and status == "rejected"
        and failure_class_str == "policy_violation"
    ):
        return KPP_ORACLE_VIOLATION

    if (
        status == "rejected"
        and failure_class_str == "policy_violation"
        and isinstance(mutated_paths, list)
        and len(mutated_paths) > 0
    ):
        return KPP_SURFACE_BREACH

    if status == "accepted":
        return KPP_PROMOTE

    if status == "rejected":
        if promotion_disposition == "deferred" and failure_class_str != "policy_violation":
            return KPP_DEFER
        if failure_class_str in {"unchanged_result", "metric_regression"}:
            return KPP_DISCARD
        if failure_class_str in {"timeout", "oom", "guard_failure", "infra_flake"}:
            return KPP_FAIL
        if failure_class_str == "policy_violation":
            return KPP_SURFACE_BREACH
        return KPP_FAIL

    return KPP_FAIL


def _main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Render a KPP Slack Block Kit JSON.")
    parser.add_argument("--kpp-outcome", choices=KPP_OUTCOMES, required=True)
    parser.add_argument("--experiment-id", default="preview")
    parser.add_argument("--failure-class", default=None)
    args = parser.parse_args()

    try:
        message = render_kpp_block_message(
            kpp_outcome=args.kpp_outcome,
            experiment_id=args.experiment_id,
            failure_class=args.failure_class,
        )
    except KPPRenderError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
    print(message.as_blocks_json())


if __name__ == "__main__":
    _main()
