# PR-628: Rate-limiting for LLM + Export Endpoints (cost + DoS control)

## Summary

Enable runtime rate limiting for **expensive endpoints** (LLM insight + PDF/CSV exports) to prevent cost-abuse and DoS. This PR wires SlowAPI in the FastAPI app, implements a proxy-aware client key, applies limits to the identified surface area, and adds deterministic `429` tests + OpenAPI documentation.

**Audit:** `docs/audit/PR_628_RATE_LIMIT_LLM_EXPORTS_AUDIT.md`

**Branch:** `security/pr-628-rate-limit-llm-exports`

---

## Context

This PR implements the first unclosed **P0 CRITICAL** item from `docs/roadmap/BACKLOG_LEDGER.md` (“Rate-limiting for LLM endpoints”).

Key facts established in audit:

- SlowAPI is installed but **disabled in runtime** (wiring commented in `legacy_app.py`).
- LLM surface includes **two** real endpoints: `/api/v1/insight` and legacy `/insight`.
- Export surface is mixed: real routers + VIP export + legacy test/demo exports.
- Existing proxy-aware client key helper exists but needs **CIDR support** for trusted proxy matching.

---

## Scope (what this PR does)

### 1) Enable SlowAPI in runtime

- Create `Limiter` with canonical `key_func`
- Attach `SlowAPIMiddleware`
- Register `RateLimitExceeded` handler returning HTTP `429` with JSON `{"detail": ...}`

### 2) Canonical rate-limit client key (proxy-aware)

Implement `rate_limit_client_key(request)` based on `core.fingerprint_security._client_fingerprint`, adding:

- Trusted proxy matching with **CIDR support**
- Trusted proxy header precedence:
  1) `CF-Connecting-IP`
  2) `X-Forwarded-For` (first)
  3) fallback `request.client.host`

### 3) Apply limits to expensive endpoints

- LLM:
  - `POST /api/v1/insight`
  - `POST /insight` (legacy)
- Exports:
  - plan export endpoints (`/api/v1/plan/*`)
  - shoplist export endpoints (`/api/v1/shoplist/*`)
  - VIP shoplist export (`/api/v1/vip/shoplist/export`)
  - legacy demo exports if enabled in test/debug (`/api/v1/premium/exports/*`, `/api/v1/export/pdf`)

### 4) Tests (deterministic)

- `200` up to threshold, then `429` after threshold for:
  - insight endpoints
  - representative export endpoints (including VIP export)
- Unit tests for client key resolution behind trusted proxy:
  - CIDR match correctness
  - header precedence
  - malformed header fallback

### 5) OpenAPI + governance

- Document `429` responses in OpenAPI (minimum on insight + export).
- Update `AGENTS.md` (commit: `docs(agents): update instructions`): document `limit_if_available` / `RATE_LIMIT_429_RESPONSES` policy + deterministic 429 test guidance.

---

## Non-goals (explicit)

- Moving insight to VIP tier (next P0 PR).
- Introducing mandatory Redis dependency for limiter storage in unit tests.
- Refactoring insight/export business logic beyond adapter-level changes.

---

## Test plan

## PR-628 — Final Verification

**Local verification:**

```bash
pytest -q tests/test_rate_limit_client_key.py tests/test_rate_limit_llm_and_exports.py
# Result: [100%] ✅
```

**Sanity:**

- Все rate-limited handlers имеют `request: Request` / `websocket` (slowapi requirement).
- В `AGENTS.md` добавлено правило: *no smoke-only substitutes* для deterministic 429 tests.

### Local (required)

```bash
make test-fast
make diff-cov
pre-commit run --all-files
```

### What to verify manually (optional)

- `POST /api/v1/insight`:
  - returns `200` before threshold
  - returns `429` after threshold
- One export endpoint (CSV or PDF) returns `429` after threshold

---

## DoD Evidence (expected for PR)

- SlowAPI middleware + handler are active in runtime and return `429`.
- Client key works behind Cloudflare/Caddy/Uvicorn (not “everyone under one IP”).
- All audited endpoints are rate-limited (see audit surface table).
- Deterministic tests cover 200→429 and key function behavior.
- OpenAPI includes `429` responses (minimum for insight + export).
- `AGENTS.md` policy updated.

---

## Deferred / Follow-ups

- P0 CRITICAL: Move LLM insight to VIP tier (separate PR; tracked in ledger).
