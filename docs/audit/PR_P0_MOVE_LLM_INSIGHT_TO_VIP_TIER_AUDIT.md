# PR (P0): Move LLM insight to VIP tier — Audit (evidence-first)

**Date:** 3 February 2026
**Branch:** `fix/p0-vip-guard-insight`
**Ledger item (source of truth):** `docs/roadmap/BACKLOG_LEDGER.md` → “P0 CRITICAL: Move LLM insight to VIP tier”

### Goal

- Make all LLM-backed “insight” endpoints **VIP-only** to prevent FREE/PRO access to expensive LLM calls.
- Ensure there is **no public unguarded** insight path.
- Keep scope tight: adapter/guard only + tests + OpenAPI regen.

---

## 1) Which handlers exist (evidence)

### `/api/v1/insight`

- **Defined in:** `legacy_app.py` (route wrapper around `insight_v1`)
- **Evidence anchor:** `@app.post("/api/v1/insight")` decorator and its `dependencies=[Depends(require_vip_tier)]`
- **Current guard:** `Depends(require_vip_tier)` (**tier-aware** VIP-only)

### `/insight` (legacy)

- **Defined in:** `legacy_app.py` (route wrapper around `insight`)
- **Evidence anchor:** `@app.post("/insight")` decorator and its `dependencies=[Depends(require_vip_tier)]`
- **Current guard:** `Depends(require_vip_tier)` (VIP-only), plus feature-flag gate inside handler (`FEATURE_INSIGHT`)

---

## 2) Client usage (thin clients)

### Frontend (React)

- No direct usage found in `frontend/src/**` (only in generated OpenAPI artifacts).
- Evidence: search for `/insight` and `/api/v1/insight` matches only:
  - `frontend/src/api/openapi.json`
  - `frontend/src/api/schema.ts`

### iOS (Swift)

- No usage found in `ios/**` (no string matches for `insight` endpoints).

Implication: we can safely **hide legacy `/insight` from OpenAPI** (and keep/guard it for backward
compat only), without breaking known clients.

---

## 3) Current auth/tier logic (evidence)

- VIP tier dependency exists and is canonical:
  - `app/middleware/api_tiers.py:205+` (`require_vip_tier`)
- Test fixtures for tiered access exist:
  - `tests/conftest.py:539-566` (`pro_headers`, `vip_headers`)

---

## 4) Decision (scope)

### Decision: `/api/v1/insight`

- Replace `_get_api_key_dynamic` gate with `require_vip_tier()` to enforce VIP-only.

### Decision: `/insight`

- Keep endpoint as legacy compatibility shim **but VIP-guard it** and set `include_in_schema=False`
  so it is not emitted into public OpenAPI (thin-client policy: deprecated/legacy paths hidden).

---

## 5) Test strategy (deterministic)

Add/adjust tests to cover:

- **FREE** (no headers) → `403`
- **PRO** (`pro_headers`) → `403`
- **VIP** (`vip_headers`) → `200` (with provider stubbed to avoid external calls)

Also update existing insight safety tests (`tests/test_insight_error_hygiene.py`) to call the endpoints
with `vip_headers`, so the tests continue to validate “no error detail leakage” under the new guard.

---

## 6) OpenAPI contract

- `/api/v1/insight` remains public but becomes VIP-guarded via `require_vip_tier` dependency.
- `/insight` becomes `include_in_schema=False` (hidden; legacy only).
- Exception (policy note): `/api/v1/insight` remains the canonical path but is VIP-guarded; no `/api/v1/vip/insight`
  is introduced in this P0 PR.
- Regenerate artifacts via `make openapi` and commit:
  - `frontend/src/api/openapi.json`
  - `frontend/src/api/schema.ts`

---

## 7) DoD

- FREE/PRO cannot call insight: `403`
- VIP can call insight: `200`
- No public unguarded `/insight` (either removed or VIP-guarded + hidden)
- Targeted pytest suite green + `make verify` green
