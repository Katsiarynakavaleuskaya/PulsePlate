# Agent Control Plane Security Baseline

## Purpose

Define the minimum security controls required to operate PulsePlate agent automation safely.

## Evidence anchors

- `RUNBOOK_AGENT.md:121` — canonical Security Ops checklist for containment, rotation, and verification.
- `docs/orchestration/workflow.md:97` — governance checkpoint that gates agent automation changes.
- `docs/runbooks/README.md:26` — runbook index entry for this baseline.
- `app/security/agent_control_plane.py:1` — runtime MVP primitives for policy gate, signed audit envelope,
  and short-lived scoped token issuing.
- `tests/test_agent_control_plane_mvp.py:1` — deterministic tests for fail-closed semantics and signature integrity.

## Mandatory Controls (P0)

1. Secrets lifecycle

- No long-lived secrets in local agent files
- Use short-lived scoped credentials from a broker
- Enforce rotation playbooks for bot/API/provider keys
- Runtime anchor: `app/security/agent_control_plane.py:264` (`issue_scoped_token`)

1. Policy-first execution

- Every privileged action must pass policy evaluation
- Default deny for unknown actions/tools/targets
- Fail-closed when policy engine is unavailable
- Runtime anchor: `app/security/agent_control_plane.py:113` (`evaluate_policy`, `require_policy_allow`)

1. Auditability

- Signed execution envelopes (request + decision + result hash)
- Immutable/tamper-evident logs for privileged operations
- Incident timeline reproducibility within 15 minutes
- Runtime anchor: `app/security/agent_control_plane.py:212` (`sign_audit_envelope`, `verify_audit_envelope`)

1. Isolation

- Sandboxed execution for high-risk actions
- Outbound allowlist for tool calls and webhooks
- No direct unrestricted local filesystem access

1. Approval model

- Auto-safe actions can run autonomously
- High-impact actions require human approval (review-required mode)

## Token and Webhook Rotation Protocol

1. Revoke old token/secret
2. Issue new token with minimum scope
3. Update runtime secret store
4. Delete/reset webhooks and verify status
5. Validate old token is unusable where possible
6. Record incident evidence and completion in runbook/ledger

## Prohibited Patterns

- Plaintext `privateKeyPem` or bot/API tokens in local markdown/json state
- Tool execution paths bypassing policy gate
- Silent retries that bypass approval mode
- Logging secrets in terminal, telemetry, or debug payloads

## Monitoring Baseline

- Alerts on suspicious token usage patterns
- Alerts on policy-denied spikes by action class
- Alerts on outbound calls to non-allowlisted targets
- Alerts on anomalous LLM cost bursts

## Release Gate (Security)

Release is blocked if any are true:

- Unresolved critical secret exposure
- Policy gate not enforced for privileged actions
- Audit signing disabled
- Token rotation incomplete after incident
