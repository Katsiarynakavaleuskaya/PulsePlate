# System Overview (C4-lite)

**Goal:** give a quick, stable picture of PulsePlate architecture and the key enforced invariants.

## Anchors (stable)

- [Canonical entrypoint](#canonical-entrypoint)
- [Routing map](#routing-map-source-of-truth)
- [OpenAPI generation mode](#openapi-generation-mode-current)

## Containers / Modules (high level)

- **Clients**
  - `frontend/` (React): thin HTTP adapter + OpenAPI-generated types
  - `ios/` (SwiftUI): thin HTTP adapter (`APIClient`) + MVVM UI
- **Backend**
  - `app/` (FastAPI adapters): routers, schemas, middleware, bootstrap
  - `core/` (domain): BMI engine, nutrition logic, i18n, business rules
  - `providers/` (LLM providers): Grok/Ollama/Pico/Stub (env-selected via `llm.py`)
- **Infra**
  - DB (SQLite/Postgres depending on env)
  - External APIs (USDA/OpenFoodFacts/LLM, etc.)

## Canonical entrypoint

- Runtime and OpenAPI generation use `app/main.py` as the canonical ASGI entrypoint (`uvicorn app.main:app`).
- `app/main.py` re-exports the FastAPI instance from `legacy_app.py` and applies bootstrap (metrics + contract routes).

## Routing map (source of truth)

See: `docs/architecture/backend_routing_map.md` (evidence-driven router registration map).

## Architecture diagram (Mermaid)

```mermaid
flowchart LR
  subgraph Clients
    FE[frontend/ (React)]
    IOS[ios/ (SwiftUI)]
  end

  subgraph Backend
    ENTRY[app/main.py (canonical entrypoint)]
    LEG[legacy_app.py (FastAPI app instance)]
    API[app/ (routers + bootstrap)]
    CORE[core/ (domain engine)]
    LLM[llm.py (provider factory)]
    PROV[providers/ (LLM adapters)]
  end

  DB[(DB)]
  EXT[(External APIs / LLM)]

  FE -->|HTTP (OpenAPI types)| ENTRY
  IOS -->|HTTP (thin client)| ENTRY

  ENTRY -->|re-exports app + applies bootstrap| LEG
  LEG -->|include_router / route handlers| API

  API -->|delegates business rules| CORE
  API -->|/insight uses factory| LLM
  LLM --> PROV

  CORE --> DB
  PROV --> EXT
```

## OpenAPI generation mode (current)

OpenAPI generator runs in **full-schema mode** (schema-only mode removed in PR-631).

**Evidence (file:line):**
- Anchor (stable): `scripts/generate_openapi.py -> main()` (FULL schema mode + env pinning)
  - Evidence: `scripts/generate_openapi.py:94`
- Anchor (stable): `tests/test_openapi_determinism.py -> test_openapi_and_schema_ts_are_deterministic()`
  - Evidence: `tests/test_openapi_determinism.py:17`

Historical ADR: `docs/architecture/ADR-002-openapi-schema-only-mode.md` (superseded).

## Enforced invariants (selected, evidence-driven)

- **One BMI Engine**
  - BMI formulas/thresholds must live in `core/bmi/*` only; guards:
    - `tests/test_bmi_canonical_guard.py:26-77`
    - `tests/test_no_bmi_math_outside_core.py:31-54`
- **Import hygiene / no dynamic module loading**
  - Tests forbid `sys.path.insert` and dynamic import execution patterns; guard:
    - `tests/test_import_hygiene_guard.py:12-41`
- **OpenAPI determinism**
  - `make openapi` must be deterministic; guard:
    - Anchor (stable): `tests/test_openapi_determinism.py -> test_openapi_and_schema_ts_are_deterministic()`
      - Evidence: `tests/test_openapi_determinism.py:17` (hash comparison)
- **Rate limiting for expensive endpoints**
  - LLM/exports endpoints must be rate-limited and have deterministic 429 tests; rate limiting is proxy-aware and privacy-friendly.

## Maintenance rule

Checklist (lightweight):
- [ ] If you change any of the following, update this doc **or** state “no system-overview update needed” in the PR description:
- entrypoint (`uvicorn ...`)
- tier namespaces (`/api/v1/bmi/*`, `/api/v1/pro/*`, `/api/v1/vip/*`)
- rate-limit wiring for LLM/exports
- OpenAPI generation mode (schema-only vs full schema)
