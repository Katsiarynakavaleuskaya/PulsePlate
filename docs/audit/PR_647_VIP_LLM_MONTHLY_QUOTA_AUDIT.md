## PR-647 — VIP LLM Monthly Hard Quota (P0 Security) — Audit

**Date:** 5 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**PR:** PR-647
**Branch:** `security/p0-vip-llm-monthly-quota-pr647`
**Scope (hard):** backend/security only. **No frontend / iOS / new LLM features / refactors.**

---

## Summary (high signal)

- Policy requires a **monthly hard quota/budget** for any LLM endpoint to be economically safe. Evidence: [E2]
- Current runtime has **VIP-only + rate limiting**, but **no monthly quota** (no symbols / no accounting layer). Evidence: [E3], [E4]
- Provider call happens at `await provider.generate(prompt_text)` inside `legacy_app.py` — the interception seam for hard stop. Evidence: [E7]
- Insight endpoints exist at runtime: `POST /api/v1/insight` and legacy `POST /insight`. Evidence: [E6]

---

## 0) Audit Meta

### 0.1 Ledger item (SoT)

This PR closes ledger item:
**P0 CRITICAL SECURITY: VIP LLM hard monthly quota (deterministic enforcement)**.

Evidence: [E1]

### 0.2 Policy source (SoT)

Quota is mandatory by policy:
`docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`.

Evidence: [E2]

### 0.3 Allowed files (PR-647)

Allowed to change (non-exhaustive, scope-minimal):

- `legacy_app.py` (insight endpoints; enforcement seam)
- `app/security/*` (shared enforcement helpers, if any)
- `core/*` (shared accounting primitives, if needed)
- `tests/*` (deterministic enforcement tests)
- `docs/audit/*`, `docs/roadmap/BACKLOG_LEDGER.md` (audit + ledger updates)

Forbidden:

- `frontend/`, `ios/`
- any new LLM product features or business logic changes
- soft limits without hard stop

---

## 1) Current State (Evidence: BEFORE)

### 1.1 Usage accounting

**Q4. Where is LLM usage accounted (requests/tokens/cost)?**

Finding: no explicit accounting layer exists for LLM usage in runtime code (no requests/month, tokens/month, cost/month).

Evidence: [E3], [E4]

**Q5. Is there persistent storage for counters?**

Finding: no evidence of quota counters/persistent store configuration for LLM quota in codebase at this time.
(Rate limiting is configured via SlowAPI; explicit Redis/storage URI configuration is not found in repo code.)

Evidence: [E5]

**Q6. Reset semantics (monthly boundary)?**

Finding: not applicable yet — there is no monthly quota/counter to reset.

Evidence: [E3], [E4]

### 1.2 Enforcement

**Q7. Any hard stop by cumulative usage?**

Finding: no hard stop exists for cumulative usage (monthly quota). Current stops are:

- VIP tier guard (403) at route level
- rate limiting (429) at route level
- `FEATURE_INSIGHT` kill-switch (503) before provider call
- provider missing (503) before provider call

Evidence: [E2], [E7]

**Q8. Where exactly is the provider call (interception seam)?**

Finding: provider call occurs at:
`await provider.generate(prompt_text)` inside `legacy_app.py` insight functions.

Evidence: [E7]

**Q9. Can we stop the request before provider call?**

Finding: yes — the code path already has pre-provider gates (VIP guard, rate limiting, kill-switch),
and PR-647 must add quota enforcement **before** `provider.generate(...)`.

Evidence: [E7]

---

## 2) Quota Model (Design decisions)

### Q10. Quota unit (first iteration)

✅ **`requests/month` per VIP key**

Rationale (budget-first P0):

- Cheapest enforceable hard cap (does not require provider token accounting or pricing tables).
- Provides a strict upper bound on LLM spend by limiting the number of paid provider calls per month.

### Q11. Limit source (config)

✅ **ENV**: `VIP_LLM_INSIGHT_REQUESTS_PER_MONTH` (with a safe default in code)

Constraints:

- Server-side authoritative (no trust in client).
- Must be easy to tune without code changes (ops-friendly).

### Q11. Counter storage (authoritative usage table)

✅ **DB (SQLAlchemy) usage table**, authoritative

Constraints (security + determinism):

- **Never store raw VIP key**. Store `key_fingerprint = sha256(raw_key + server_salt)`, where `server_salt` is read from env.
- `server_salt`: **required env (no default)**; rotation requires counter migration policy (non-goal for P0).
- Bucket is **UTC calendar month**: `YYYY-MM-01T00:00:00Z`. Store as `month_start_date` (`date`) for simplicity.
- **Atomicity (hard requirement):** check + increment must be one atomic operation (single statement or transactional
  upsert/increment with guard), otherwise parallel requests can break the hard cap.

### Q12. VIP tier binding (P0)

✅ One shared limit for all VIP keys (per key), P0 baseline.

Non-goals (explicitly out of scope for P0):

- Per-plan quotas
- Tokens/month or cost/month accounting
- Paid add-ons / rollover / proration

---

## 3) Enforcement semantics (Hard)

### 3.1 Where enforcement runs (hard stop seam)

Quota enforcement must run **inside the handler** and must hard-stop **before** the provider call
(`await provider.generate(...)`).

Evidence seam: `legacy_app.py:2127` and `legacy_app.py:2172` (see [E7]).

### 3.2 What enforcement does (attempt-consume semantics)

Define a single server-side authoritative operation (conceptual name: `attempt_consume_quota(...)`):

- If allowed: atomically **increment** usage for `(key_fingerprint, month_start_date)` and continue request handling.
- If exceeded: return **HTTP 429** with deterministic payload:
  - `{"detail": "quota_exceeded"}`
  - No provider exception leakage (stable error contract).

### 3.3 Bucket (monthly boundary)

`month_start_date = first_day_utc(today_utc)` (UTC calendar month), stored as `date`:

- Example: `2026-02-01` represents `2026-02-01T00:00:00Z`.

### 3.4 Idempotency / retries (explicit non-goal for P0)

Non-goal (P0): idempotency keys / deduplication.

Constraints:

- Quota counts **per request attempt**.
- Clients must not automatically retry on 5xx without an idempotency key; otherwise retries may consume quota twice.

---

## 4) Reset semantics (Time boundaries)

Reset is achieved by selecting a **new UTC calendar month bucket** (`month_start_date`) automatically:

- No cron/job is required for reset.
- Old usage rows are retained (non-goal for P0: cleanup/compaction).

---

## 5) Tests + DoD (P0 minimum)

### 5.1 Tests (security-critical matrix)

Minimum required tests for P0:

1. **VIP under quota → 200**
2. **VIP over quota → 429** with deterministic payload `{"detail": "quota_exceeded"}` and no-leak checks
3. **FREE/PRO → 403** (no regression vs VIP tier guard)
4. **Concurrency / atomicity proof**: `limit=1`, two parallel requests → exactly **1 succeeds**, **1 returns quota_exceeded**

### 5.2 DoD (runtime)

P0 is complete only if:

- Quota enforcement runs **before** provider call (`provider.generate(...)`).
- Counter is stored in DB keyed by `(key_fingerprint, month_start_date)`.
- `server_salt` is **required env** (no default) and startup fails with a clear error if missing.
- OpenAPI and client artifacts are unchanged.
- Targeted pytest suite for quota is green, and `pre-commit` is green.

---

## Appendix: Evidence (append-only)

### [E1] Ledger item exists (SoT)

Command:
```bash
rg -n "P0 CRITICAL SECURITY: VIP LLM hard monthly quota" docs/roadmap/BACKLOG_LEDGER.md -n -C 3
```

Raw output (truncated):
```text
232:- [ ] P0 CRITICAL SECURITY: VIP LLM hard monthly quota (deterministic enforcement)
233-  - Owner: @katsiaryna_kavaleuskaya
234-  - Priority: P0 (CRITICAL security)
235-  - Target PR: TBD (security fix)
```

Exit code: `0`

### [E2] Policy requires monthly hard quota (SoT)

Command:
```bash
rg -n "economically unsafe|hard cost cap|Monthly hard quota|monthly hard quota" docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md -n
```

Raw output (truncated):
```text
13:LLM is a **metered resource**, not a feature. Any LLM endpoint is **economically unsafe** until it has a
14:**hard cost cap** (quota/budget) per user/key.
38:**Note:** VIP-only + rate limiting are necessary but not sufficient. Until a monthly hard quota is enforced,
39:LLM endpoints remain **economically unsafe** by this policy and must be tracked as an open P0 security item in
72:3. **Monthly hard quota** (cost ceiling)
```

Exit code: `0`

### [E3] No quota symbols in code (expected)

Command:
```bash
rg -n "INSIGHT_QUOTA|LLM_QUOTA|quota_exceeded|monthly quota|hard quota" --type py app core legacy_app.py llm.py providers
```

Raw output:
```text
<empty>
```

Exit code: `1`

### [E4] No token-usage accounting symbols in insight code (expected)

Command:
```bash
rg -n "prompt_tokens|completion_tokens|total_tokens|token_usage" legacy_app.py llm.py providers
```

Raw output:
```text
<empty>
```

Exit code: `1`

### [E5] No explicit rate-limit storage config found in repo code (expected)

Command:
```bash
rg -n "redis://|storage_uri|RATELIMIT_STORAGE|RATE_LIMIT_STORAGE" --type py app core legacy_app.py
```

Raw output:
```text
<empty>
```

Exit code: `1`

### [E6] Insight endpoints exist at runtime

Command:
```bash
python - <<'PY'
import os
os.environ['TESTING'] = 'true'
import app
paths = {r.path for r in app.app.routes}
print('/api/v1/insight' in paths)
print('/insight' in paths)
PY
```

Raw output (truncated):
```text
True
True
```

Exit code: `0`

### [E7] Provider call + pre-provider gates (interception seam)

Evidence anchor: `legacy_app.py:2127` and `legacy_app.py:2172` (`provider.generate(...)`) and kill-switch gate
`legacy_app.py:2142-2145` (`FEATURE_INSIGHT`).

Source excerpt:
```text
legacy_app.py:2127  insight_text = await provider.generate(prompt_text)
legacy_app.py:2142  flag_value = os.getenv("FEATURE_INSIGHT", "false")
legacy_app.py:2143  if not _is_truthy(flag_value): ...
legacy_app.py:2172  insight_text = await provider.generate(prompt_text)
```
