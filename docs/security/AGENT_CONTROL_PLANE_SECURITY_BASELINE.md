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
- Runtime anchor: `app/security/agent_control_plane.py:276` (`issue_scoped_token`)

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

## Operational Guide (MVP Primitives)

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_CONTROL_ALLOWLIST` | Yes (if policy gate used) | `""` (deny all) | Comma or newline-separated `action:target` pairs |
| `AGENT_CONTROL_AUDIT_SIGNING_KEY` | Yes (fail-closed) | None | HMAC key for signing audit envelopes |
| `AGENT_CONTROL_BROKER_HMAC_KEY` | Yes (fail-closed) | None | HMAC key for scoped token issuing |
| `AGENT_CONTROL_SCOPED_TTL_SECONDS` | No | `300` | TTL for scoped tokens (minimum 1 second) |

### Policy Gate (deny-by-default)

```python
from app.security.agent_control_plane import evaluate_policy, require_policy_allow

# Evaluate without raising (returns PolicyDecision)
decision = evaluate_policy("agent.exec", "target-resource")
if not decision.allowed:
    log.warning(f"Denied: {decision.reason}")

# Or fail-closed (raises PermissionError if denied)
decision = require_policy_allow("agent.exec", "target-resource")
```

### Signed Audit Envelope

```python
from app.security.agent_control_plane import sign_audit_envelope, verify_audit_envelope

# Sign a policy decision for tamper-evident audit trail
envelope = sign_audit_envelope(decision, metadata={"user_id": "123"})

# Verify integrity (returns bool)
is_valid = verify_audit_envelope(envelope)
```

### Scoped Token Issuing

```python
from app.security.agent_control_plane import issue_scoped_token

# Issue short-lived token (default 300s TTL)
token = issue_scoped_token("agent.exec", ttl_seconds=60)
# token.token, token.scope, token.issued_at_utc, token.expires_at_utc
```

**Known limitation (MVP):** Scoped tokens are deterministic (HMAC-based without nonce). Identical scope + timestamp produces identical tokens. Adding a nonce/random component is tracked as P2 for Wave 2 in `docs/roadmap/BACKLOG_LEDGER.md:60`.

### Secret Rotation Checklist

1. Generate new secrets (use `secrets.token_hex(32)` minimum)
2. Update environment variables in deployment config
3. Restart services to pick up new secrets
4. Verify new audit envelopes are signed correctly
5. Old audit envelopes remain verifiable with old secret (archive separately)

### Fail-Closed Semantics

- **Empty secrets rejected**: Passing `secret=""` or `hmac_key=""` raises `RuntimeError`
- **Missing env vars rejected**: Unset `AGENT_CONTROL_AUDIT_SIGNING_KEY` raises `RuntimeError`
- **Invalid TTL rejected**: `ttl_seconds < 1` raises `ValueError`

### Deterministic Test Coverage

All fail-closed behaviors are covered in `tests/test_agent_control_plane_mvp.py`:
- `test_sign_audit_envelope_rejects_empty_string_secret`
- `test_verify_audit_envelope_rejects_empty_string_secret`
- `test_issue_scoped_token_rejects_empty_string_hmac_key`

## Release Gate (Security)

Release is blocked if any are true:

- Unresolved critical secret exposure
- Policy gate not enforced for privileged actions
- Audit signing disabled
- Token rotation incomplete after incident
