## PR-646 — VIP-only LLM Insight (P0 Security) — Audit

**Date:** 5 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**PR:** PR-646
**Branch (planned):** `security/p0-vip-only-llm-insight-pr646`
**Scope (hard):** backend/security + docs only. **No frontend/iOS/product refactors.**

---

## 1) Executive Summary

### Goal (ledger)

Make LLM Insight available **ONLY** to VIP tier:

- `POST /api/v1/insight` → VIP-only
- `POST /insight` (legacy) → removed **or** VIP-guarded (and not exposed in OpenAPI)
- Both endpoints must remain **rate-limited** (cost-abuse control)

### Audit finding (current `main`)

**The target state is already implemented on `main`**:

- `POST /api/v1/insight` is **VIP-guarded** with `require_vip_tier`
- `POST /insight` is **VIP-guarded** with `require_vip_tier`, **deprecated**, and **hidden from OpenAPI**
- Both endpoints are **rate-limited** with `@limit_if_available(RATE_LIMIT_INSIGHT)`
- Tests already exist and pass for **FREE→403**, **PRO→403**, **VIP→200** + error hygiene (no exception leaks)

**Implication:** a runtime PR that “implements VIP-only insight” would be **no-op** and is forbidden by repo workflow.
PR-646 should be executed as a **docs-only ledger-correction closure** (this audit + ledger update to ✅ Done,
linked to the already-merged implementation PR).

---

## 2) Audit Meta (Scope + Allowed files)

### Ledger scope anchor

**Question answered:** What exact ledger item is PR-646 supposed to close?

**Evidence**

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

### Allowed / forbidden areas (policy)

- **Allowed**: `legacy_app.py` / `app/security/*` / `tests/*` **only if** new behavior is needed; `docs/audit/*`,
  `docs/roadmap/BACKLOG_LEDGER.md` (ledger status).
- **Forbidden**: `frontend/` and `ios/` runtime changes (frozen until P0 backend-security is done).
  **Note:** generated OpenAPI artifacts under `frontend/src/api/*` are allowed **only** when runtime OpenAPI changes
  in this PR require regeneration. In this specific case, OpenAPI already reflects the correct visibility.

---

## 3) Current State (Evidence: BEFORE)

### 3.1 Endpoint surface (what routes exist)

**Question answered:** Do `/api/v1/insight` and `/insight` exist at runtime? Is `/insight` exposed in OpenAPI?

**Evidence A — runtime route registration**

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

**Evidence B — OpenAPI visibility (canonical)**

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

**Evidence C — generated frontend OpenAPI artifact contains only canonical path**

Command:
```bash
rg -n "\"/api/v1/insight\"" frontend/src/api/openapi.json -n
```

Raw output (truncated):
```text
6685:    "/api/v1/insight": {
```

Exit code: `0`

Command:
```bash
rg -n "\"/insight\"" frontend/src/api/openapi.json -n
```

Raw output:
```text
<no matches>
```

Exit code: `1`

**Notes**

- `app/static/openapi.json` currently contains `/insight`, but **it is not the canonical OpenAPI artifact**
  for clients. Canonical OpenAPI for clients is generated via `make openapi` and committed into
  `frontend/src/api/openapi.json` (per `AGENTS.md` OpenAPI policy).
- Canonical evidence is **live** `app.app.openapi()` output + the generated client artifact.

### 3.2 Auth & tier guard behavior

**Question answered:** What guard is used now? Is `_get_api_key_dynamic` used for Insight?

**Evidence — route decorators in `legacy_app.py`**

Command:
```bash
rg -n "^@app\\.post\\(|\"/api/v1/insight\"|\"/insight\"|dependencies=\\[Depends\\(require_vip_tier\\)\\]|@limit_if_available\\(RATE_LIMIT_INSIGHT\\)|include_in_schema=False" legacy_app.py -m 30
```

Raw output (truncated):
```text
2180:    "/api/v1/insight",
2181:    dependencies=[Depends(require_vip_tier)],
2185:@limit_if_available(RATE_LIMIT_INSIGHT)
```

Raw output (truncated):
```text
2192:    "/insight",
2193:    include_in_schema=False,
2195:    dependencies=[Depends(require_vip_tier)],
```

Exit code: `0`

**Evidence — `_get_api_key_dynamic` is present but not used on Insight**

Command:
```bash
rg -n "_get_api_key_dynamic" legacy_app.py | rg -n "insight" || true
```

Raw output:
```text
<empty>
```

Exit code: `0`

### 3.3 Rate limiting (cost-abuse control)

**Question answered:** Are Insight endpoints rate-limited with `RATE_LIMIT_INSIGHT` and documented as 429?

**Evidence**

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

---

## 4) Target State (Policy Alignment)

### 4.1 Canonical policy hooks (hard rules)

- **Tier policy:** LLM Insight must be **VIP-only**.
- **Rate limit policy:** All LLM endpoints must use `@limit_if_available(RATE_LIMIT_INSIGHT)` and document 429
  via `responses=RATE_LIMIT_429_RESPONSES` (root `AGENTS.md`).
- **Thin HTTP adapter policy:** No client-side (frontend/iOS) computation; clients are thin transport adapters.

### 4.2 Alignment check

Based on the evidence in §3:

- `/api/v1/insight` uses `dependencies=[Depends(require_vip_tier)]` ✅
- `/insight` uses `dependencies=[Depends(require_vip_tier)]`, is deprecated + hidden from schema ✅
- Both are decorated with `@limit_if_available(RATE_LIMIT_INSIGHT)` and declare 429 responses ✅

---

## 5) Tests (Security-Critical)

### 5.1 Tier guard matrix (FREE/PRO/VIP)

**Question answered:** Do we have tests proving FREE→403, PRO→403, VIP→200?

**Evidence — existing test file**

Anchor: `tests/test_insight_vip_guard_api.py` (contains both `/api/v1/insight` and `/insight` assertions).

**Evidence — test run**

Command:
```bash
pytest -q tests/test_insight_vip_guard_api.py tests/test_insight_error_hygiene.py
```

Raw output:
```text
.....                                                                    [100%]
```

Exit code: `0`

### 5.2 Error hygiene (no exception leak)

**Question answered:** Do Insight endpoints avoid leaking provider exception text?

Anchor: `tests/test_insight_error_hygiene.py` asserts sensitive substrings do not appear in response `detail`.

---

## 6) Decision (фиксируемое решение по `/insight`)

**Decision:** Keep `/insight` as a **deprecated legacy alias** that is:

- VIP-only (`require_vip_tier`)
- Hidden from OpenAPI (`include_in_schema=False`)
- Rate-limited (`@limit_if_available(RATE_LIMIT_INSIGHT)`)

**Rationale (security + compatibility):**

- Removes unauthenticated surface (VIP guard required).
- Preserves backward compatibility for any legacy client that might still call `/insight`.
- Avoids expanding public contract (legacy is not in OpenAPI, so new clients will not adopt it).

**Evidence anchor:** `legacy_app.py` decorators for `/insight` show `include_in_schema=False` + VIP dependency + rate limit
(see §3.2 and §3.3).

---

## 7) Ledger Drift Analysis (Why PR-646 is “already done”)

### 7.1 Ledger item text is stale vs code reality

Ledger claims:

- `/api/v1/insight` uses `_get_api_key_dynamic`
- `/insight` has no auth

But code evidence shows both endpoints are VIP-guarded and rate-limited (see §3).

### 7.2 Implementation PR already merged

**Evidence**

Command:
```bash
git show -s --format='%h %s' 98330ead
```

Raw output:
```text
98330ead P0: Enforce VIP tier for LLM Insight and close legacy /insight endpoint (#640)
```

Exit code: `0`

**Conclusion:** PR-646 should not be a runtime PR; it should close the ledger item with evidence + audit doc.

---

## 8) Exit Criteria (DoD) — Evidence Checklist

- [x] **FREE → 403**, **PRO → 403**, **VIP → 200** for `/api/v1/insight`
  Evidence: `tests/test_insight_vip_guard_api.py` + `pytest -q ...` (see §5.1)
- [x] `/api/v1/insight` does **not** use `_get_api_key_dynamic`
  Evidence: decorator uses `require_vip_tier` + `_get_api_key_dynamic` not referenced for insight routes (see §3.2)
- [x] `/insight` is **VIP-guarded** and **not exposed in OpenAPI**
  Evidence: `app.app.openapi()` membership is `False` (see §3.1), `include_in_schema=False` (see §3.2)
- [x] Rate limiting present on both Insight endpoints
  Evidence: `@limit_if_available(RATE_LIMIT_INSIGHT)` on both routes (see §3.3)
- [ ] Ledger item updated: `P0: Move LLM insight to VIP tier` → ✅ Done, with link to PR #640 and this audit
  (Docs-only change; must not include runtime code changes.)

---

## 9) PR-646 Recommended Execution (No-op prevention)

**Hard rule:** Avoid no-op runtime PRs. Therefore:

1. Create a **docs-only PR-646** containing:
   - this audit: `docs/audit/PR_646_VIP_ONLY_LLM_INSIGHT_AUDIT.md`
   - ledger update: mark item ✅ Done and link PR #640 + this audit
2. Verify docs-only scope (policy):
   - `git diff --name-only origin/main...HEAD | rg -v "\\.md$|README\\.md$|AGENTS\\.md$|RUNBOOK_AGENT\\.md$|DEPLOYMENT\\.md$"` must be empty

---

## 10) Risk Notes (P0 Security)

- **Financial risk (cost abuse):** LLM endpoints are expensive; VIP-only gating + rate limiting is the primary mitigation.
- **Security risk (data handling):** Privacy text explicitly warns that `/insight` and `/api/v1/insight` may transmit user text
  to external AI providers (anchor: `legacy_app.py` privacy info section includes these endpoints).
- **Contract risk:** Keeping `/insight` hidden from OpenAPI prevents new client adoption and limits blast radius.

### Evidence — $72k/month cost attack note

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
