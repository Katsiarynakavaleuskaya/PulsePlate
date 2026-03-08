# Agent Control Plane Security Baseline

## Purpose

Define the minimum security controls required to operate PulsePlate agent automation safely.

## Evidence anchors

- `RUNBOOK_AGENT.md:139` — canonical Security Ops checklist for containment, rotation, and verification.
- `docs/orchestration/workflow.md:97` — governance checkpoint that gates agent automation changes.
- `docs/runbooks/README.md:26` — runbook index entry for this baseline.
- `app/security/agent_control_plane.py:1` — runtime MVP primitives for policy gate, signed audit envelope,
  and short-lived scoped token issuing.
- `tests/test_agent_control_plane_mvp.py:1` — deterministic tests for fail-closed semantics and signature integrity.

## Mandatory Controls (P0)

### C1. Secrets lifecycle

- No long-lived secrets in local agent files
- Use short-lived scoped credentials from a broker
- Enforce rotation playbooks for bot/API/provider keys
- Runtime anchor: `app/security/agent_control_plane.py:276` (`issue_scoped_token`)

### C2. Policy-first execution

- Every privileged action must pass policy evaluation
- Default deny for unknown actions/tools/targets
- Fail-closed when policy engine is unavailable
- Runtime anchor: `app/security/agent_control_plane.py:113` (`evaluate_policy`, `require_policy_allow`)

### C3. Auditability

- Signed execution envelopes (request + decision + result hash)
- Immutable/tamper-evident logs for privileged operations
- Incident timeline reproducibility within 15 minutes
- Runtime anchor: `app/security/agent_control_plane.py:212` (`sign_audit_envelope`, `verify_audit_envelope`)

### C4. Isolation

- Sandboxed execution for high-risk actions
- Outbound allowlist for tool calls and webhooks
- No direct unrestricted local filesystem access

### C5. Approval model

- Auto-safe actions can run autonomously
- High-impact actions require human approval (review-required mode)

## Agent-as-Attacker Threat Model (EVMbench-inspired)

**Purpose:** Document abuse scenarios where an agent could violate policy, and map them to existing controls.

**Rationale:** EVMbench research demonstrates that AI agents can execute end-to-end exploits against vulnerable systems. Understanding "what would an agent need to do to cause harm" helps validate our controls.

**Evidence anchors:** Control implementations at `app/security/agent_control_plane.py`; tests at `tests/test_agent_control_plane_mvp.py`.

### Threat Scenarios

| ID | Scenario | Attack Vector | Impact | Mitigating Control (with evidence) |
|----|----------|---------------|--------|-----------------------------------|
| T1 | **Secret exfiltration** | Agent extracts credentials from env vars or files and sends to external endpoint | Full credential compromise | C4-a (`agent_control_plane.py:106`), C2-a (`agent_control_plane.py:113`) |
| T2 | **Privilege escalation** | Agent bypasses policy gate to execute privileged action | Unauthorized system access | C2-a (`agent_control_plane.py:113`), C2-b (`agent_control_plane.py:151`) |
| T3 | **Audit tampering** | Agent modifies or deletes audit logs to hide malicious activity | Loss of forensic evidence | C3-a (`agent_control_plane.py:212`), C3-b (`agent_control_plane.py:254`) |
| T4 | **Token theft/replay** | Agent steals or replays scoped tokens beyond intended scope | Extended unauthorized access | C1-a (`agent_control_plane.py:276`), TTL enforcement (`test_agent_control_plane_mvp.py:112`) |
| T5 | **Prompt injection** | Malicious content in retrieved data causes agent to execute harmful actions | Arbitrary action execution | C2-a (`agent_control_plane.py:113`), external content untrusted (policy) |
| T6 | **Resource exhaustion** | Agent triggers expensive operations (LLM calls, exports) repeatedly | Financial/operational DoS | Rate limiting (`app/security/rate_limit.py`), cost alerts (monitoring) |
| T7 | **Data poisoning** | Agent writes malicious data to config/code files | Persistent backdoor | C4 (isolation, planned), code review, guard tests (`test_repo_policy_guards.py`) |

### Control Effectiveness Matrix

| Control | Evidence | T1 | T2 | T3 | T4 | T5 | T6 | T7 |
|---------|----------|----|----|----|----|----|----|----|----|
| C1-a Short-lived tokens | `agent_control_plane.py:276` | ○ | ○ | - | ● | - | - | - |
| C1-b Fail-closed secrets | `agent_control_plane.py:167` | ● | ○ | - | ○ | - | - | - |
| C2-a Deny-by-default | `agent_control_plane.py:113` | ● | ● | - | - | ● | ○ | ○ |
| C2-b Fail-closed policy | `agent_control_plane.py:151` | ● | ● | - | - | ● | - | - |
| C3-a Signed audit | `agent_control_plane.py:212` | - | - | ● | - | - | - | - |
| C3-b Audit verification | `agent_control_plane.py:254` | - | - | ● | - | - | - | - |
| C4-a Outbound allowlist | `agent_control_plane.py:106` | ● | - | - | - | - | - | - |
| C4-b Sandboxed execution | `app/security/execution_sandbox.py:303` | ○ | ● | - | - | ○ | ○ | ● |
| C5-a Approval model | `app/security/agent_control_plane.py:239`, `app/routers/cbt_insight.py:238` | - | ● | - | - | - | ○ | ○ |

**Legend:** ● = Primary mitigation, ○ = Secondary/partial mitigation, - = Not applicable

### Residual Risks

| Risk | Description | Mitigation Status | Exit Criteria |
|------|-------------|-------------------|---------------|
| R1 | Deterministic tokens (no nonce) enable prediction | P2 backlog: nonce-bearing tokens | Tests show distinct tokens for same scope+timestamp |
| R2 | Sandbox is local and bounded, but not a strong host/container isolation boundary yet | P2 backlog: stronger remote isolation follow-up | Stronger isolated runner boundary approved and green |
| R3 | Cost monitoring is alerting-only (no hard cap) | P1 backlog: LLM monthly quota | Hard quota test at `tests/test_insight_vip_monthly_quota_api.py` passes |
| R4 | Prompt injection defense is policy-only (no content filtering) | Accepted risk: policy gate sufficient for MVP | N/A (accepted) |

### Detection Indicators

Signs that an agent may be attempting malicious activity:

- Repeated policy denials for same action/target pattern — logged at `evaluate_policy()` (`agent_control_plane.py:113`)
- Outbound requests to non-allowlisted targets — blocked at `load_allowlist_from_env()` (`agent_control_plane.py:106`)
- Token issuance rate spike — monitored via `issue_scoped_token()` (`agent_control_plane.py:276`)
- Audit envelope verification failures — detected at `verify_audit_envelope()` (`agent_control_plane.py:254`)
- Unusual error patterns in agent logs — application telemetry

## Controls Ownership and Verification Evidence

Each mandatory control is mapped to an owner, runtime enforcement point, and
verification evidence. Status: **Impl** = implemented in code, **Doc** = documented
contract (enforcement via policy/process), **Planned** = tracked in backlog.

**Anchor maintenance:** `file:line` references point to function definitions in
`app/security/agent_control_plane.py`. When functions move (refactor, reorder),
update this table in the same PR. Canonical verification:
`grep -n "^def " app/security/agent_control_plane.py` — compare output with
the anchors below.

| ID | Control | Owner | Status | Runtime Evidence (`file:line`) | Verification |
|----|---------|-------|--------|-------------------------------|--------------|
| C1-a | Short-lived scoped tokens | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:276` | See "Canonical Security Verification" |
| C1-b | Fail-closed on missing/empty secrets | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:167`, `:178` | See "Canonical Security Verification" |
| C1-c | Rotation playbook adopted | @katsiaryna_kavaleuskaya | Doc | This document: "Credential Rotation Protocols" | Manual: follow per-class protocol below |
| C2-a | Deny-by-default policy gate | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:113` | See "Canonical Security Verification" |
| C2-b | Fail-closed on policy unavailable | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:151` | See "Canonical Security Verification" |
| C3-a | Signed audit envelopes (HMAC-SHA256) | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:212` | See "Canonical Security Verification" |
| C3-b | Audit envelope verification | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:254` | See "Canonical Security Verification" |
| C3-c | Incident timeline within 15 min | @katsiaryna_kavaleuskaya | Doc | `RUNBOOK_AGENT.md:139` | Manual: follow containment checklist |
| C4-a | Outbound allowlist enforcement | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:106` | See "Canonical Security Verification" |
| C4-b | Sandboxed execution (high-risk) | @katsiaryna_kavaleuskaya | Impl (local bounded sandbox) | `app/security/execution_sandbox.py:255`, `tests/test_execution_sandbox.py:1` | Deterministic local sandbox tests |
| C5-a | Auto-safe / review-required split | @katsiaryna_kavaleuskaya | Impl | `app/security/agent_control_plane.py:239`, `app/routers/cbt_insight.py:238`, `tests/test_agent_control_plane_mvp.py:130` | Runtime enforcement tests |

### Canonical Security Verification

Single source of truth for security-related verification commands. Referenced by
the controls ownership table, release gate, and RUNBOOK Security Ops checklist.

```bash
# Full agent control plane test suite (all controls)
pytest tests/test_agent_control_plane_mvp.py -v
pytest tests/test_execution_sandbox.py -v

# Anchor drift check (compare with ownership table above)
grep -n "^def " app/security/agent_control_plane.py
grep -n "^def " app/security/execution_sandbox.py
```

Individual control checks (use `-k` filter):

| Scope | Command |
|-------|---------|
| Policy gate (C2-a, C2-b) | `pytest -k "deny_by_default or require_policy" tests/test_agent_control_plane_mvp.py` |
| Audit signing (C3-a, C3-b) | `pytest -k "sign_audit or verify_audit" tests/test_agent_control_plane_mvp.py` |
| Fail-closed (C1-b, G5) | `pytest -k empty_string tests/test_agent_control_plane_mvp.py` |
| Scoped tokens (C1-a) | `pytest -k scoped_token tests/test_agent_control_plane_mvp.py` |
| Allowlist (C4-a) | `pytest -k allowlist tests/test_agent_control_plane_mvp.py` |

## Credential Rotation Protocols

### General principles

- Rotation is **mandatory** after any suspected credential exposure.
- New credentials must be generated **before** revoking old ones to avoid downtime (where the platform supports overlap).
- Minimum entropy: `secrets.token_hex(32)` (256-bit) for all HMAC keys and tokens.
- All rotation events must be recorded in `docs/roadmap/BACKLOG_LEDGER.md` with date, PR, and operator.

### Protocol R1: HMAC Audit Signing Key (`AGENT_CONTROL_AUDIT_SIGNING_KEY`)

**Scope:** Signs and verifies all audit envelopes for tamper-evident trail.

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Generate new key: `python -c "import secrets; print(secrets.token_hex(32))"` | Key is 64 hex chars |
| 2 | Update `AGENT_CONTROL_AUDIT_SIGNING_KEY` in deployment secret store | Env var set in target environment |
| 3 | Restart affected services | Service healthy (`/health` returns 200) |
| 4 | Sign a test envelope and verify: `sign_audit_envelope(decision)` succeeds | No `RuntimeError` raised |
| 5 | Verify old envelopes: archive old key if historical verification needed | Old envelopes remain verifiable with archived key |
| 6 | Confirm old key is removed from all secret stores | `grep -r "old_key_prefix" .env* deploy/` returns empty |

**Rollback:** If new key causes failures, revert secret store to previous value and restart.

### Protocol R2: HMAC Broker Key (`AGENT_CONTROL_BROKER_HMAC_KEY`)

**Scope:** Issues short-lived scoped tokens for agent actions.

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Generate new key: `python -c "import secrets; print(secrets.token_hex(32))"` | Key is 64 hex chars |
| 2 | Update `AGENT_CONTROL_BROKER_HMAC_KEY` in deployment secret store | Env var set in target environment |
| 3 | Restart affected services | Service healthy (`/health` returns 200) |
| 4 | Issue test token: `issue_scoped_token("test.rotation")` succeeds | Returns valid `IssuedScopedToken` |
| 5 | Confirm outstanding tokens from old key expire naturally (max 300s default TTL) | After TTL: old tokens invalid |
| 6 | Remove old key from all secret stores | No references to old key remain |

**Rollback:** Revert secret store and restart. Outstanding tokens from new key become invalid (acceptable: max TTL window).

### Protocol R3: Bot Tokens (GitHub App, Telegram, CI bots)

**Scope:** Long-lived tokens used by automation bots for API access.

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Generate new token via provider admin UI (GitHub Settings > Developer settings, BotFather, etc.) | New token received |
| 2 | Update token in CI secrets / deployment secret store | Secret updated in GitHub Actions / deployment |
| 3 | Trigger a test workflow or API call using new token | API responds 200 (not 401/403) |
| 4 | Revoke old token via provider admin UI | Provider confirms revocation |
| 5 | Verify old token is rejected: test API call with old token | Returns 401 or equivalent |
| 6 | Record in ledger: date, operator, affected systems | `BACKLOG_LEDGER.md` entry updated |

**Rollback:** If new token causes failures before old token is revoked (step 4), revert secret store to old token value. If old token is already revoked, regenerate via provider UI.

### Protocol R4: API Provider Keys (LLM, external services)

**Scope:** Keys for external API providers (OpenAI, etc.).

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Generate new API key via provider dashboard | New key created |
| 2 | Update key in deployment secret store (do NOT update `.env` files in repo) | Secret updated |
| 3 | Restart affected services | Service healthy, provider calls succeed |
| 4 | Verify provider calls work: trigger a test request | Response 200 with valid payload |
| 5 | Revoke old key via provider dashboard | Provider confirms revocation |
| 6 | Verify old key rejected | Old key returns 401/403 from provider |

**Note:** For providers that support key overlap (two active keys), steps 1-4 can run before step 5 to avoid downtime.

### Protocol R5: Webhook Secrets

**Scope:** Shared secrets used to verify inbound webhook payloads.

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Generate new secret: `python -c "import secrets; print(secrets.token_hex(32))"` | Secret is 64 hex chars |
| 2 | Update webhook configuration at provider (GitHub webhook settings, etc.) | Provider shows new secret |
| 3 | Update corresponding secret in deployment secret store | Env var set |
| 4 | Restart services that validate webhook signatures | Service healthy |
| 5 | Trigger test webhook event | Signature validation passes (200, not 401) |
| 6 | Old webhook payloads with old signature are rejected | Replay with old signature returns 401 |

**Rollback:** Update provider webhook config back to old secret and restart services.

## Security Release Gate

### Gate conditions (all must pass for release)

Release is **blocked** if any of the following conditions are true.
Each condition has a verification method and required evidence.
Individual verification commands are defined in "Canonical Security Verification" above.

| # | Blocking Condition | Severity | Verification Command / Check | Evidence Required |
|---|-------------------|----------|------------------------------|-------------------|
| G1 | Unresolved critical secret exposure | P0-STOP | `git log --all --diff-filter=A -- '*.env' '*.pem' '*.key'` returns no new secrets; check `detect-secrets scan` output | Clean `detect-secrets` baseline (`.secrets.baseline`) |
| G2 | Policy gate not enforced for privileged actions | P0-STOP | See Canonical Security Verification: Policy gate (C2-a, C2-b) | Green test output |
| G3 | Audit signing disabled or bypassed | P0-STOP | See Canonical Security Verification: Audit signing (C3-a, C3-b) | Green test output |
| G4 | Token rotation incomplete after incident | P0-STOP | Manual: check `BACKLOG_LEDGER.md` for open rotation items with P0 priority | No open P0 rotation entries |
| G5 | Fail-closed semantics broken (empty secrets accepted) | P0-STOP | See Canonical Security Verification: Fail-closed (C1-b, G5) | Green test output |
| G6 | `make verify` fails | P0-STOP | `make verify` (lint + typecheck + test-fast + diff-cov >= 97%) | Green output, exit code 0 |
| G7 | Pre-commit hooks produce uncommitted changes | P1-BLOCK | `pre-commit run --all-files` exits 0 with no file modifications | Clean `git status` after run |

### Gate sign-off process

1. Run `make verify` locally and confirm exit code 0.
2. Execute `pre-commit run --all-files` and confirm no file modifications.
3. Verify all agent control plane tests pass: `pytest tests/test_agent_control_plane_mvp.py -v`.
4. Check `BACKLOG_LEDGER.md` for open P0 security items — must be zero.
5. Confirm CI is green on the PR (no required check failures).
6. Record sign-off in PR body under `## Merge Readiness`.

## Prohibited Patterns

- Plaintext `privateKeyPem` or bot/API tokens in local markdown/json state
- Tool execution paths bypassing policy gate
- Silent retries that bypass approval mode
- Logging secrets in terminal, telemetry, or debug payloads
- Committing `.env` files with real credentials (use `.env.example` with placeholders)
- Using `|| true` to suppress security check failures

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

**Known limitation (MVP — temporary seam):** Scoped tokens are deterministic (HMAC-based without nonce). Identical scope + timestamp produces identical tokens.

- **ADR reference:** `docs/architecture/ADR-003-agent-control-plane-mvp.md` (Wave 2 scope, line 84).
- **Backlog:** P2 in `docs/roadmap/BACKLOG_LEDGER.md`.
- **Exit criteria (close this seam when all are met):**
  1. Nonce/random component design approved in ADR-003 amendment or new ADR.
  2. Backward-compatible rollout plan documented (old tokens expire naturally within TTL window).
  3. Deterministic tests updated to cover nonce uniqueness (same scope + timestamp produces distinct tokens).
  4. No performance regression: token issuing latency stays under 1 ms p99.

### Fail-Closed Semantics

- **Empty secrets rejected**: Passing `secret=""` or `hmac_key=""` raises `RuntimeError`
- **Missing env vars rejected**: Unset `AGENT_CONTROL_AUDIT_SIGNING_KEY` raises `RuntimeError`
- **Invalid TTL rejected**: `ttl_seconds < 1` raises `ValueError`

### Deterministic Test Coverage

All fail-closed behaviors are covered in `tests/test_agent_control_plane_mvp.py`:
- `test_sign_audit_envelope_rejects_empty_string_secret`
- `test_verify_audit_envelope_rejects_empty_string_secret`
- `test_issue_scoped_token_rejects_empty_string_hmac_key`
