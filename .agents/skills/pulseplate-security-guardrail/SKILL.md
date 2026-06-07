---
name: pulseplate-security-guardrail
description: PulsePlate security compass — indexes canonical guard tests, hard gates, and architectural invariants. Advisory only; canonical enforcement lives in code/tests.
compatibility: Compatible with Kimi Code CLI, Codex, Qoder, and other agentskills.io-compatible runtimes. This skill is read-only advisory; never add enforcement rules here.
---

# PulsePlate Security Guardrail

## When to use

- Before any PR touches auth, quota, rate-limit, LLM, WebSocket, or agent-input paths.
- When reviewing security-sensitive surfaces (billing, paywall, iOS release, orchestration).
- When a generic security skill recommends changes that may conflict with PulsePlate invariants.

## What this is (and is not)

This skill is a **reference compass**, not an enforcement layer. Canonical enforcement lives in:

- `tests/test_repo_policy_guards.py`
- `tests/guards/test_nosec_policy_guard.py`
- `tests/guards/test_subprocess_uses_absolute_binaries.py`
- `AGENTS.md` hard gates

## Canonical guard index

### Rate limiting & LLM quota

- **Rule:** All LLM endpoints (`/api/v1/insight`, `/insight`) MUST use `@limit_if_available(RATE_LIMIT_INSIGHT)`.
- **Rule:** All export endpoints MUST use `@limit_if_available(RATE_LIMIT_EXPORTS)`.
- **Rule:** Server-side monthly hard quota MUST be enforced before any provider call.
- **Tests:** `tests/test_rate_limit_llm_and_exports_api.py`, `tests/test_rate_limit_client_key_api.py`
- **Policy:** `app/security/rate_limit.py`

### AI agent input guard

- **Rule:** AI-facing insight and MCP entrypoints MUST screen text with `prepare_safe_ai_prompt_input(...)` before quota/RAG/provider calls.
- **Rule:** MCP tool-level blocking MUST preserve JSON-RPC contract (`-32602 Invalid params`).
- **Tests:** `tests/test_agent_input_guard.py`, `tests/test_mcp_pulseplate_server_coverage.py`, `tests/test_insight_error_hygiene.py`
- **Policy:** `app/security/agent_input_guard.py`

### WebSocket foundation

- **Rule:** Auth is mandatory and fail-closed (missing/invalid token → close `1008`).
- **Rule:** Runtime guardrails: message-size limit, sliding-window burst limit, event allowlist.
- **Policy:** `app/main.py` (`/ws` endpoint)

### #nosec policy (no blind suppressions)

- **Rule:** `# nosec` forbidden when a simple fix exists.
- **Rule:** Allowed only with: rule code, one-line justification, `(remove-by: YYYY-MM-DD, ref: issue/PR)`.
- **Rule:** `remove-by` and `ref` MUST NOT be `N/A`.
- **Tests:** `tests/guards/test_nosec_policy_guard.py`

### Subprocess absolute binaries

- **Rule:** External tool subprocess calls MUST use absolute path via `shutil.which()`.
- **Rule:** Direct Python subprocess MUST NOT use bare `python`/`python3`; use `sys.executable`.
- **Tests:** `tests/guards/test_subprocess_uses_absolute_binaries.py`

### Knowledge promotion & evidence graph

- **Rule:** RAG chunks are evidence artifacts, not canonical facts.
- **Rule:** Knowledge writes require passed canonical verification bundle.
- **Rule:** Route layer and `legacy_app.py` must never write or mutate knowledge records.
- **Policy:** `docs/memory/kpp_knowledge_promotion_pipeline.md`

### App Store / iOS release integrity

- **Rule:** `PrivacyInfo.xcprivacy` must cover required-reason APIs.
- **Rule:** Release `BASE_URL` is explicit HTTPS; no silent production fallback.
- **Rule:** HealthKit must remain read-only unless a separate reviewed PR changes entitlement posture.

## Review priorities (P0 first)

1. P0/P1 correctness and regressions
2. Security, auth, quota, secret-handling paths
3. Billing, subscriptions, paywall, and release-truth surfaces
4. App Store / Fastlane / iOS release integrity
5. Orchestration invariants (`agent-coordinator`, `task_bootstrap.py`, `native_subagent_bridge`)
6. Schema drift between backend contracts, OpenAPI, and generated client types
