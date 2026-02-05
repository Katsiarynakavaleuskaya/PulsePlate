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
