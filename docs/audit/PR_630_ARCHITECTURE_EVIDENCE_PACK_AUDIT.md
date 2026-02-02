# PR-630 — Architecture Evidence Pack (Audit)

**Status:** Draft (evidence-first, no runtime changes)
**Scope:** docs + ADR + backlog ledger only (no application behavior changes).

## 1) Entrypoint SoT (runtime)

**Claim:** The canonical runtime entrypoint is `uvicorn app.main:app`.

**Evidence:**
- `Dockerfile:102-105` — CMD uses `python -m uvicorn app.main:app ...`
- `app/main.py:11-22` — defines `app` by re-exporting `legacy_app.app` and applying bootstrap.

**Risk if violated:** dual-base / multiple app instances → nondeterminism, xdist hangs, OpenAPI drift, inconsistent middleware.

## 2) Legacy bootstrap boundary (what is “legacy” allowed to do)

**Claim:** `legacy_app.py` still registers most routers and hosts compatibility shims; `app/main.py` is the canonical entrypoint wrapper that applies bootstrap (metrics + pro-contract routes).

**Evidence:**
- `app/main.py:11-22` — bootstrap is applied here (`register_metrics`, `register_pro_contract_routes`).
- `legacy_app.py:811-850` — central router registration via `app.include_router(...)` + calls to centralized VIP/PRO registration.

**Compat shims observed:**
- `app/__init__.py:44-56` — PEP 562 forwarder + `sys.modules.setdefault("app_module", legacy)`

**Risk:** compat shims without explicit boundaries become “magic layers” that hide import-order risks and break patchability.

## 3) OpenAPI schema-only mode (why it exists, what it disables)

**Claim:** OpenAPI generation is currently forced into **schema-only mode** and disables certain feature routers to avoid import-time ORM double-loading.

**Evidence:**
- `scripts/generate_openapi.py:94-113` — sets `PULSEPLATE_OPENAPI=1` and disables:
  - `FEATURE_PREMIUM_WEEK_ENABLED=false`
  - `FEATURE_BMI_PRO_ENABLED=false`
  - `BUSINESS_MODULE_ENABLED=false`
- `app/routers/pro_registration.py:26-36` — schema-only mode is honored only when:
  - `PULSEPLATE_OPENAPI=1`
  - `APP_ENV=test`
  - `ENVIRONMENT=test`
- `app/routers/pro_registration.py:76-105` — avoids importing PRO/premium routers in schema-only mode.

**Technical root cause (documented):**
- `scripts/generate_openapi.py:96-113` + `app/routers/pro_registration.py:77-80` reference import-time ORM/model hazards and “Table already defined” errors.

**Risk:** schema-only mode reduces “contract velocity” for thin clients (web/iOS) and increases silent drift risk.

## 4) Guards as enforcement (what is already enforced)

**Claim:** Architecture invariants are enforced by guard tests (not only by docs).

**Evidence:**
- One BMI engine:
  - `tests/test_bmi_canonical_guard.py:26-77` — forbids `core/bmi/*` importing `bmi_core` (legacy)
  - `tests/test_no_bmi_math_outside_core.py:31-54` — whitelist-based scan to prevent BMI math outside canonical places
- Import hygiene:
  - `tests/test_import_hygiene_guard.py:12-41` — forbids `sys.path.insert` in tests (except whitelisted)
- OpenAPI determinism:
  - `tests/test_openapi_determinism.py:16-64` — `make openapi` twice, hashes must match

**Risk:** if guards drift or are bypassed, architecture regressions reappear as production incidents.

## 5) Providers wiring truth (runtime reality)

**Claim:** LLM providers **are wired into runtime** through `legacy_app.py` insight endpoints using `llm.get_provider()`.

**Evidence:**
- `legacy_app.py:2066-2076` — `_load_llm_get_provider()` imports `llm.get_provider`
- `legacy_app.py:2098-2117` — `provider = get_provider()` and `await provider.generate(...)`
- `legacy_app.py:2168-2187` — HTTP endpoints `/api/v1/insight` and `/insight`
- `llm.py:57-79` + `91-153` — imports provider implementations and selects by `LLM_PROVIDER`

**Risk:** docs that claim “not wired” cause wrong assumptions in security/cost-control/tier design and client work.

## Exit criteria (what makes the “temporary seams” removable)

**Schema-only OpenAPI can be removed when:**
- No routers imported by `app.main:app` import SQLAlchemy models at module import time (OpenAPI generation does not hit “Table already defined”).
- `scripts/generate_openapi.py` no longer needs to force-disable feature routers.
- `tests/test_openapi_determinism.py` remains green.

**Compat shim (`sys.modules["app_module"]`) can be removed when:**
- No tests/utilities rely on patching the legacy module by that alias.
- A guard prevents new uses of that alias and documents the migration path.

**BMI whitelist can be reduced when:**
- `bmi_visualization.py` and `app/routers/bmi_pro.py` no longer contain BMI thresholds/math that should live in `core/bmi/*`.
