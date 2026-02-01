# PR-628 — Rate-limiting for LLM + Export Endpoints (P0 CRITICAL)

**Status:** Audit closed ✅ (ready to start implementation)
**Type:** Runtime PR (security / cost-control / DoS mitigation)
**Branch:** `security/pr-628-rate-limit-llm-exports`

**Ledger (source of truth):** `docs/roadmap/BACKLOG_LEDGER.md` → **P0 CRITICAL: Rate-limiting for LLM endpoints**

---

## Context / Why now

**Problem:** LLM insight + export endpoints are **expensive** and currently **unlimited**. This enables:

- **Cost abuse** (LLM calls at scale; ledger notes “\$72k/month cost attack” risk).
- **DoS risk** (PDF/CSV endpoints can be heavy; repeated calls can exhaust CPU/memory).

**Goal (PR-628):** Enable a correct, proxy-aware rate limiter in runtime and apply limits to LLM + export surfaces, with deterministic tests and OpenAPI documentation.

---

## 1) Surface Area (candidates to rate-limit)

Format: **METHOD + PATH + file:line**

### A) LLM / Insight

| Method | Path | Evidence |
|---|---|---|
| POST | `/api/v1/insight` | `legacy_app.py:2037-2042` |
| POST | `/insight` (legacy) | `legacy_app.py:2085-2089` |

### B) Export / PDF / CSV (real routers)

| Method | Path | Evidence |
|---|---|---|
| GET | `/api/v1/plan/week/export.csv` | `app/routers/plan_export.py:347` (router prefix at `:42`) |
| GET | `/api/v1/plan/week/export.pdf` | `app/routers/plan_export.py:444` (router prefix at `:42`) |
| POST | `/api/v1/export/sign` | `app/routers/plan_export.py:561` (router prefix at `:43`) |
| GET | `/api/v1/shoplist` | `app/routers/shoplist_export.py:230` (router prefix at `:25`) |
| GET | `/api/v1/shoplist/export.csv` | `app/routers/shoplist_export.py:237` |
| GET | `/api/v1/shoplist/export.pdf` | `app/routers/shoplist_export.py:258` |

### C) Export / PDF / CSV (VIP)

| Method | Path | Evidence |
|---|---|---|
| POST | `/api/v1/vip/shoplist/export` | `app/routers/vip_shoplist.py:505` (VIP prefix: `app/routers/vip.py:127` + include: `:130`) |

### D) Export / PDF / CSV (test/demo endpoints in legacy_app.py)

These are gated by `EXPORTS_ENABLED` (see “Feature flags / route registration” below), but **still represent surface area** when enabled.

| Method | Path | Evidence |
|---|---|---|
| GET | `/api/v1/premium/exports/day/{plan_id}.csv` | `legacy_app.py:4695-4697` |
| POST | `/api/v1/export/pdf` (generic) | `legacy_app.py:4778-4781` |
| GET | `/api/v1/premium/exports/week/{plan_id}.csv` | `legacy_app.py:4830-4833` |
| GET | `/api/v1/premium/exports/day/{plan_id}.pdf` | `legacy_app.py:4941-4943` |
| GET | `/api/v1/premium/exports/week/{plan_id}.pdf` | `legacy_app.py:5026-5029` |

---

## 2) Feature flags / route registration (facts)

### A) Insight gating flag

- `FEATURE_INSIGHT` gates both insight paths:
  - `legacy_app.py:2047-2049` (`/api/v1/insight`)
  - `legacy_app.py:2095-2098` (`/insight`)

### B) VIP module gating flag

- `VIP_MODULE_ENABLED` parsed via `app/utils/feature_flags.py:24-26`
- Registration is centralized:
  - `app/routers/vip_registration.py:42-57` (includes `app/routers/vip.py` router)

### C) Legacy “exports enabled” gating

`legacy_app.py` defines:

- `EXPORTS_ENABLED` computed from `FEATURE_EXPORTS` and test/debug heuristics:
  - `legacy_app.py:4676-4693`
- When enabled, legacy “test/demo” export endpoints are defined (see surface table above).

### D) Signed export token gating (plan_export)

- `PRIVATE_EXPORTS_ENABLED` (env) parsed in `settings.py:10-14`
- Token guard logic:
  - `app/routers/plan_export.py:332-345`

---

## 3) Current State (rate limiting in runtime)

### What is true today

**Rate limiting is NOT active in runtime.**

- SlowAPI import is optional (present as dependency but not wired):
  - `legacy_app.py:144-153`
- All wiring is commented out:
  - `legacy_app.py:1022-1037`

**Evidence snippet (commented setup):**

- `legacy_app.py:1022-1037` (middleware + handler + limiter are commented)

---

## 4) Proxy Chain Facts (what the app sees)

### Caddy → Uvicorn

- Caddy reverse proxies to `app:8000`:
  - `deploy/Caddyfile:1-3` (staging)
  - `deploy/Caddyfile.production:1-3` (production)

### Uvicorn forwarded headers

- Staging: `--proxy-headers --forwarded-allow-ips="caddy"`
  - `deploy/docker-compose.staging.yaml:18-21`
- Production: `--proxy-headers --forwarded-allow-ips="172.30.100.0/24"`
  - `deploy/docker-compose.production.yaml:20-24`

### Cloudflare

Cloudflare is referenced as part of production infra posture:

- `deploy/Caddyfile.production:5-6` (“complements Cloudflare”)

No explicit Caddy rule for `CF-Connecting-IP` is present; therefore the app must assume only standard forwarded headers unless explicitly added.

---

## 5) Client Key Strategy (rate-limit key_func)

### Existing foundation (usable today)

There is already a proxy-aware “client key” helper:

- `_client_fingerprint()` in `core/fingerprint_security.py:179-226`

Key properties:

- Trusts `X-Forwarded-For` **only when** the immediate `request.client.host` is in `TRUSTED_PROXIES`.
- Otherwise falls back to `request.client.host`.
- Returns a **pseudonymous fingerprint** (hashed), not the raw IP (privacy-friendly).

### Critical gap (must fix for PR-628)

`TRUSTED_PROXIES` matching is currently **exact-string only** (no CIDR). That is fragile for production where:

- `--forwarded-allow-ips` is configured as a **CIDR network** in production docker-compose,
- proxy/container IPs are not stable single values,
- exact-IP allowlists tend to break after redeploy/network changes.

**Requirement for PR-628:** add **CIDR support** for trusted proxies, and in trusted-proxy mode prefer:

1) `CF-Connecting-IP` (when present)
2) `X-Forwarded-For` (first IP)
3) fallback `request.client.host`

---

## 6) Test Strategy (deterministic 429)

### Current state

- No existing tests validating real 429 from SlowAPI (only import/coverage tests).
- Existing `TestClient` fixture exists:
  - `tests/conftest.py:443-446`

### Required tests (DoD-level)

1) **LLM endpoints rate-limit behavior**
   - `200` up to threshold
   - `429` after threshold
   - Apply to both:
     - `/api/v1/insight`
     - `/insight`

2) **Export endpoints rate-limit behavior**
   - `200` up to threshold
   - `429` after threshold
   - Include:
     - plan export (`/api/v1/plan/*`)
     - shoplist export (`/api/v1/shoplist/*`)
     - VIP shoplist export (`/api/v1/vip/shoplist/export`)
     - legacy demo exports if they remain enabled in test/debug

3) **Client key correctness behind proxies**
   - Unit tests for key resolution when request comes from a trusted proxy, including:
     - `CF-Connecting-IP`
     - `X-Forwarded-For` (single and multi-hop)
     - fallback behavior for malformed headers

### Determinism / shared state constraint

SlowAPI limiter state must not leak across tests. Tests must ensure:

- per-test isolation of limiter storage, OR
- explicit reset of limiter state between tests.

---

## 7) OpenAPI / Error Contract Notes (429)

Current project baseline for standard FastAPI errors uses:

- `HTTPException` → `{"detail": "..."}` (e.g. `tests/test_api.py:61-71` and insight hygiene tests).

**PR-628 requirement:** 429 should be represented in OpenAPI for at least:

- `/api/v1/insight`
- export endpoints under `/api/v1/export/*` and `/api/v1/plan/*`

and should return a stable JSON payload (minimum acceptable):

```json
{"detail": "Rate limit exceeded"}
```

---

## 8) Definition of Done (PR-628)

- SlowAPI is active in runtime (Limiter + middleware + 429 handler).
- Proxy-aware key function works behind Cloudflare/Caddy/Uvicorn and does not collapse all users under one IP.
- Limits applied to:
  - `/api/v1/insight` and `/insight`
  - all export endpoints listed in section “Surface Area”
- Deterministic tests for 200→429 exist and pass.
- OpenAPI documents 429 (minimum on insight + export).
- Governance: `AGENTS.md` rule added: “expensive endpoints MUST be rate-limited + MUST have 429 tests”.

---

## 9) Risks / Non-goals

### Risks

- Incorrect proxy trust config can:
  - under-limit (attackers evade), or
  - over-limit (all clients share one key → false positives).
- State leakage in tests can create flakes if limiter storage isn’t isolated.

### Non-goals (explicit)

- Changing product tier access for insight (next P0 is “Move insight to VIP tier”).
- Adding Redis as a mandatory dependency for rate limiting (unit tests should not require Redis).
- Refactoring exports/insight business logic (adapter-only change + infra middleware).

---

## References

- Ledger: `docs/roadmap/BACKLOG_LEDGER.md` (P0 CRITICAL: Rate-limiting for LLM endpoints)
- LLM endpoints: `legacy_app.py` (`/api/v1/insight`, `/insight`)
- SlowAPI wiring (commented): `legacy_app.py:1022-1037`
- Client fingerprint helper: `core/fingerprint_security.py:_client_fingerprint`
- Proxy infra:
  - `deploy/Caddyfile`, `deploy/Caddyfile.production`
  - `deploy/docker-compose.staging.yaml`, `deploy/docker-compose.production.yaml`
