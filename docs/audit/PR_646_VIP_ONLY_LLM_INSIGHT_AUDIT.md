## PR-646 — VIP-only LLM Insight (P0 Security) — Audit

**Date:** 5 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**PR:** PR-646
**Branch (planned):** `security/p0-vip-only-llm-insight-pr646`
**Scope (hard):** backend/security + docs only. **No frontend/iOS/product refactors.**

---

## Summary (high signal)

- The ledger item “Move LLM insight to VIP tier” exists and was stale vs runtime. Evidence: [E1]
- Runtime routes exist for both `POST /api/v1/insight` and legacy `POST /insight`. Evidence: [E2]
- OpenAPI includes **only** `/api/v1/insight` (legacy `/insight` is hidden). Evidence: [E3], [E4], [E5]
- Both insight endpoints are **VIP-guarded** and **rate-limited**. Evidence: [E6], [E8]
- `_get_api_key_dynamic` is not used on insight endpoints. Evidence: [E7]
- Tests already prove **FREE→403**, **PRO→403**, **VIP→200** and error hygiene (no provider exception leaks). Evidence: [E9]
- Runtime implementation landed earlier as PR #640 (ledger closure should reference it). Evidence: [E10]
- Remaining gap (non-goal for PR-646): monthly hard quota/budget enforcement is **not** evidenced here. Per policy
  `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`, the endpoint remains economically unsafe until quota exists; this must
  be tracked as a separate open P0 ledger item.

---

## 1) Scope (PR-646)

### Goal (ledger)

Make LLM Insight available **ONLY** to VIP tier:

- `POST /api/v1/insight` → VIP-only
- `POST /insight` (legacy) → VIP-guarded + hidden from OpenAPI (or removed)
- Both endpoints remain **rate-limited** (`RATE_LIMIT_INSIGHT`)

Ledger anchor evidence: [E1]

### Allowed / forbidden areas (docs-only)

- This PR is **docs-only**: audit + ledger status updates (+ policy doc).
- Frontend/iOS are frozen (no runtime changes). OpenAPI client artifacts are **not** regenerated here because
  OpenAPI already reflects correct visibility. Evidence: [E4], [E5]

---

## 2) Findings (current `main`)

### 2.1 Endpoint surface

Routes exist at runtime for both:

1) `POST /api/v1/insight`
2) `POST /insight` (legacy)

Evidence: [E2]

OpenAPI visibility:

- `/api/v1/insight` **is present** in OpenAPI. Evidence: [E3], [E4]
- `/insight` **is not present** in OpenAPI (hidden). Evidence: [E3], [E5]

### 2.2 Auth / tier guard behavior

Both insight endpoints are guarded with `require_vip_tier`.

Evidence: [E6]

`_get_api_key_dynamic` exists in `legacy_app.py` but is not used by insight endpoints.

Evidence: [E7]

### 2.3 Rate limiting (cost-abuse control)

Both insight endpoints are decorated with:

- `@limit_if_available(RATE_LIMIT_INSIGHT)`
- `responses=RATE_LIMIT_429_RESPONSES` (OpenAPI 429 documentation)

Evidence: [E8]

---

## 3) Decision: legacy `/insight`

**Decision:** Keep `/insight` as a deprecated legacy alias that remains:

- VIP-only (`require_vip_tier`)
- Hidden from OpenAPI (`include_in_schema=False`)
- Rate-limited (`RATE_LIMIT_INSIGHT`)

Rationale (security + compatibility): removes unauthenticated surface while preserving backward compatibility,
without expanding the public contract (hidden from OpenAPI).

Evidence: [E6], [E3], [E8]

---

## 4) Tests (security-critical)

Existing tests prove:

- Tier matrix: **FREE → 403**, **PRO → 403**, **VIP → 200**
- Error hygiene: provider exception text is not leaked

Evidence: [E9]

---

## 5) Ledger drift + closure

The ledger description for this item was stale vs runtime: it claimed `_get_api_key_dynamic` and unauthenticated
legacy insight. Current runtime is already VIP-only + rate-limited. Evidence: [E6], [E7], [E8]

Runtime implementation already merged in PR #640. Evidence: [E10]

---

## 6) Exit criteria (DoD)

This audit is satisfied when the following are true (all evidence exists in Appendix):

- VIP-only access: FREE/PRO rejected, VIP allowed. Evidence: [E9], [E6]
- Rate limiting present + 429 documented. Evidence: [E8]
- Legacy `/insight` not exposed in OpenAPI. Evidence: [E3], [E5]
- `_get_api_key_dynamic` not used for insight routes. Evidence: [E7]
- Ledger entry updated to ✅ Done with links to PR #640 and this audit. (docs-only)
- Separate P0 ledger item exists for monthly hard quota enforcement per `docs/policy/LLM_UNIT_ECONOMICS_GUARDRAILS.md`.

---

## 7) Risk notes (P0 security)

- **Financial risk:** cost-abuse surface for LLM; mitigations here are VIP-only + rate limiting.
  Note: rate limiting is not a unit-economics cost cap; quotas/budgets are documented separately.
- **Contract risk:** legacy `/insight` remains hidden from OpenAPI, preventing new client adoption.

Evidence for “$72k/month cost attack risk” note: [E11]

---

## Appendix: Evidence (append-only)

### [E1] Ledger item exists (before closure)

Command:
```bash
rg -n "P0 Move LLM insight to VIP tier|Move LLM insight to VIP tier" docs/roadmap/BACKLOG_LEDGER.md -n -C 3
```

Raw output (truncated):
```text
211:### P0 Move LLM insight to VIP tier
213:- [ ] P0 CRITICAL: Move LLM insight to VIP tier (prevent FREE tier abuse)
216-  - Target PR: TBD (security fix)
```

Exit code: `0`

### [E2] Runtime route registration

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

Raw output:
```text
True
True
```

Exit code: `0`

### [E3] OpenAPI visibility (live)

Command:
```bash
python - <<'PY'
import os
os.environ['TESTING'] = 'true'
import app
paths = set(app.app.openapi().get('paths', {}).keys())
print('/api/v1/insight' in paths)
print('/insight' in paths)
PY
```

Raw output:
```text
True
False
```

Exit code: `0`

### [E4] Generated client OpenAPI contains canonical insight path

Command:
```bash
rg -n "\"/api/v1/insight\"" frontend/src/api/openapi.json -n
```

Raw output (truncated):
```text
6685:    "/api/v1/insight": {
```

Exit code: `0`

### [E5] Generated client OpenAPI does not include legacy `/insight`

Command:
```bash
rg -n "\"/insight\"" frontend/src/api/openapi.json -n
```

Raw output:
```text
<no matches>
```

Exit code: `1`

### [E6] VIP guard on both insight endpoints (route decorators)

Command:
```bash
rg -n "^@app\\.post\\(|\"/api/v1/insight\"|\"/insight\"|dependencies=\\[Depends\\(require_vip_tier\\)\\]|@limit_if_available\\(RATE_LIMIT_INSIGHT\\)|include_in_schema=False" legacy_app.py -m 30
```

Raw output (truncated):
```text
2180:    "/api/v1/insight",
2181:    dependencies=[Depends(require_vip_tier)],
2185:@limit_if_available(RATE_LIMIT_INSIGHT)
2192:    "/insight",
2193:    include_in_schema=False,
2195:    dependencies=[Depends(require_vip_tier)],
```

Exit code: `0`

### [E7] `_get_api_key_dynamic` is not used for insight endpoints

Command:
```bash
rg -n "_get_api_key_dynamic" legacy_app.py | rg -n "insight" || true
```

Raw output:
```text
<empty>
```

Exit code: `0`

### [E8] Rate limiting + 429 documentation for insight endpoints

Command:
```bash
rg -n "limit_if_available\\(RATE_LIMIT_INSIGHT\\)|RATE_LIMIT_429_RESPONSES" legacy_app.py -n -m 20
```

Raw output (truncated):
```text
2183:    responses=RATE_LIMIT_429_RESPONSES,
2185:@limit_if_available(RATE_LIMIT_INSIGHT)
2198:    responses=RATE_LIMIT_429_RESPONSES,
```

Exit code: `0`

### [E9] Tests: VIP-only matrix + error hygiene

Command:
```bash
pytest -q tests/test_insight_vip_guard_api.py tests/test_insight_error_hygiene.py
```

Raw output:
```text
.....                                                                    [100%]
```

Exit code: `0`

### [E10] Runtime implementation already merged (PR #640)

Command:
```bash
git show -s --format='%h %s' 98330ead
```

Raw output:
```text
98330ead P0: Enforce VIP tier for LLM Insight and close legacy /insight endpoint (#640)
```

Exit code: `0`

### [E11] $72k/month cost attack risk note (project context)

Command:
```bash
rg -n "72k" docs/insights/RECURSIVE_METHODS_LLM_RAG.md -n -m 5
```

Raw output (truncated):
```text
982:> **Abuse / attack-surface note:** The repo backlog flags a **$72k/month cost attack risk** for LLM endpoints without
985:> the same `multiplier` (e.g., ~$72k/month -> ~$216k-$360k/month at 3-5x) unless mitigations (rate limits,
```

Exit code: `0`
