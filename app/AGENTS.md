# Agent instructions (scope: app/ and subdirectories)

## Scope and layout

- This AGENTS.md applies to: `app/` and below.
- Key directories: `app/routers/`, `app/schemas/`, `app/models/`, `app/services/`,
  `app/middleware/`, `app/core/`, `app/dependencies.py`.

## Commands (run from repo root)

- Install: `make venv`
- Dev: `make dev`
- Test: `make test`, `make test-fast`
- Coverage: `make cov`, `make cov-check`
- Lint/format: `make lint`, `make fmt`, `make fmt-check`
- Pre-commit: `make pre-commit`

## Health endpoints contract (PR-504)

| Endpoint | Purpose | DB I/O | Response |
|----------|---------|--------|----------|
| `/health` | Liveness probe | ❌ No | 200 + status/version/git_sha/timestamp |
| `/health/db` | DB readiness | ✅ Yes | 200 or 503 |
| `/ready` | Readiness alias (hidden from OpenAPI) | ✅ Yes | 200 or 503 |

**Usage:**
- Use `/health` for liveness checks (process alive, no dependencies).
- Use `/ready` or `/health/db` for readiness checks (DB available).
- Orchestrators (K8s, Docker, Caddy) should use `/ready` for traffic gating.

**Verification:**
```bash
curl -fsS https://.../health   # liveness
curl -fsS https://.../ready    # readiness (503 if DB down)
```
---

## Metrics endpoint contract (PR-505)

| Endpoint | Purpose | Format | OpenAPI |
|----------|---------|--------|---------|
| `/metrics` | Prometheus exposition | `text/plain` (Prometheus exposition; `CONTENT_TYPE_LATEST`) or JSON error | ❌ Hidden |

**Metrics collected:**
- `http_requests_total{method, route, status}`: Total HTTP request count
- `http_request_duration_seconds{method, route, status}`: Request latency histogram

**Response format:**
- **Normal**: Prometheus exposition format (`text/plain`, uses `CONTENT_TYPE_LATEST`) when exporter is available
- **Fallback**: JSON error envelope (`{"error": "Prometheus client not available", "detail": "..."}`) if exporter is unavailable
- **Fallback status code:** MUST return HTTP 200 with JSON error envelope (preferred for scrape stability)
- JSON fallback is required for testability and graceful degradation

**Allowed labels:**
- `method`: HTTP method (GET, POST, etc.)
- `route`: Route template (e.g., `/api/v1/bmi/calculate`), **not raw path**
- `status`: HTTP status code (200, 404, 500, etc.)

**Forbidden (high-cardinality):**
- ❌ Raw request path (e.g., `/api/v1/users/123`)
- ❌ Query parameters
- ❌ User IDs, IP addresses, User-Agent
- ❌ Any dynamic path segments

**Route extraction rules (canonical):**
- Route label MUST be the endpoint-level template path (APIRoute.path).
- Canonical resolution algorithm:
  1) Read `endpoint = request.scope.get("endpoint")`
  2) Iterate `request.app.router.routes` and find the `APIRoute` whose `.endpoint is endpoint`
  3) Return `APIRoute.path` (string starting with `/`)
- `request.scope["route"]` MUST NOT be treated as canonical (it may refer to mounts/prefixes).
- Always use `request.app.router.routes` (never a module-level `app`) to resolve endpoint-level template paths.
- If endpoint cannot be resolved → `route="unknown"` (raw path fallback is forbidden).
- This prevents high cardinality when routes with path parameters (e.g., `/api/v1/users/{id}`) are added.
- **Prometheus route label policy**: Route label MUST be route template only. Raw/normalized path fallback is forbidden. If route template is unavailable → route="unknown".

**Excluded paths** (not counted in metrics):
- `/metrics` (self)
- `/health`, `/ready`, `/health/db` (health checks)

**Note:** Exclusion uses normalized path (handles trailing slashes). The same set is used for both route template matching and raw path exclusion after normalization.

**Usage:**
```bash
curl -fsS https://.../metrics | grep http_requests_total
```

**Implementation:**
- Middleware: `app/middleware/metrics.py`
- Endpoint: `legacy_app.py` (hidden from OpenAPI via `include_in_schema=False`)

**Limitations:**
- Multiprocess mode not enabled: `/metrics` returns per-process metrics only.
- For multi-worker deployments (gunicorn/uvicorn workers), metrics are not aggregated across workers.
- To enable multiprocess mode: configure `prometheus_client` multiprocess mode + `PROMETHEUS_MULTIPROC_DIR` (requires explicit infra decision).

**Prometheus route label policy (enforced):**
- Route label MUST be route template only (from `APIRoute.path` via endpoint identity matching).
- Raw/normalized path fallback is **forbidden** for non-excluded requests (prevents high cardinality).
- If route template is unavailable → use `"unknown"` (never fallback to `request.url.path`).

**Observability security policy:**
- `/metrics` MUST NOT enforce application-level authentication (API keys, auth middleware).
- Protection of `/metrics` is an infrastructure concern:
  - ingress ACLs (Cloudflare, Caddy)
  - firewall rules
  - private networks
  - Prometheus scrape configs
- App-level guards are forbidden for `/metrics` to preserve testability and backward compatibility.
- If infrastructure-level protection is needed, implement it in a dedicated infra PR (e.g., PR-506).

**Testing requirements:**
- Tests MUST assert `/metrics` returns a Prometheus exposition response (`Content-Type` starts with `text/plain`) on happy path.
- Tests MUST NOT assert an exact `Content-Type` value (version/charset are implementation details of `prometheus_client`).
- Only assert prefix: `text/plain` for Prometheus; `application/json` for fallback.
- JSON fallback should only be tested when exporter is explicitly unavailable (mocked/uninstalled).
- This prevents regressions where fallback triggers incorrectly (e.g., import errors, missing dependencies).

**Metrics fallback contract (testability):**
- `/metrics` happy-path returns Prometheus exposition (`text/plain*`).
- JSON fallback is ONLY for exporter failures (ImportError or runtime exception from exporter).
- Tests that validate JSON fallback MUST force failure explicitly via monkeypatch
  (e.g. patch `prometheus_client.generate_latest` to raise).
- It is forbidden for tests to assume exporter is missing in CI.

**Patchability rule for optional deps (hard):**
- Do NOT `from prometheus_client import generate_latest, CONTENT_TYPE_LATEST` in modules that are tested via monkeypatch.
- Do `import prometheus_client` and reference `prometheus_client.generate_latest()` / `prometheus_client.CONTENT_TYPE_LATEST`.
- This keeps fallback paths testable (monkeypatch patches the same object used by production code).

**Import-safety for observability (hard):**
- Metrics instrumentation must not crash startup if optional deps are unavailable.
- Wrap prometheus_client imports/init in `try/except ImportError` and degrade to no-op if unavailable.
- Middleware becomes no-op (returns response without instrumentation) if metrics are unavailable.
- This ensures graceful degradation: application starts even if observability deps are missing.

**No error detail leakage (hard):**
- JSON fallback for `/metrics` must not include raw exception messages/paths in response.
- Log exceptions server-side only (use `logger.exception()`).
- Response `detail` field must be a stable, user-safe message (e.g., "Prometheus exporter unavailable").
- Never expose `str(exc)` or stack traces in JSON responses.

**Route template selection (hard):**
- If multiple route templates map to the same endpoint (e.g., `/api/v1/bmi` and `/api/v1/bmi/calculate`),
  metrics middleware MUST select the most specific template (longest `APIRoute.path`).
- This ensures consistent metric labels and prevents route label drift when alias/legacy routes exist.
- Route template must be normalized (trailing slash removed) before exclusion check and label usage.

**Middleware route label rule (hard):**
- The `route` label MUST be endpoint-level template path (APIRoute.path).
- Router prefixes or mounts are NOT acceptable as `route` labels.
- Implementation MUST match by `request.scope["endpoint"]` identity to APIRoute.endpoint.
- **Breaking change policy:** Changing a route template (e.g., `/api/v1/bmi/calculate` → `/api/v2/bmi/calculate`) is a breaking change for metrics label contract. Update tests + AGENTS.md in the same PR.

**CI red freeze (enforced):**
- If CI is red: only allow commits that make CI green (no refactors / drive-by changes).
- Only allowed commits: fixes for failing tests / lint / typecheck / coverage in the same PR.
- If you believe a test is wrong: you MUST submit the patch that corrects it in this PR (no exceptions).
- **No green, no push, no exceptions.**

**Push hygiene (required):**
- Before pushing: `git fetch origin`
- Verify tests pass: `make test-fast` + `make lint` + `make cov-check`
- Push normally: `git push` (force push is forbidden)
- If branch diverged: create fresh branch and cherry-pick (see root AGENTS.md)

---

## Conventions

- FastAPI + Pydantic v2 only; prefer `model_validator`/`field_validator`.
- Keep routers thin; push business logic into `core/` or `app/services/`.
- Use dependency injection via `Depends`; keep side effects in services.
- Use `fastapi.status` for status codes and `HTTPException` for errors.
- Keep API schema changes in sync with `app/schemas/` and tests.
- Apply tier guards (`require_pro_tier`, VIP) consistently on gated endpoints.

### Typing rule: Pydantic v2 `model_validate()` + mypy

Pydantic v2 `BaseModel.model_validate()` is typed as returning `Any` for mypy in many cases.
Therefore:

- ❌ Do NOT: `return SomeModel.model_validate(x)` (can trigger `no-any-return`)
- ✅ Do: assign to a typed local first:

```py
result: SomeModel = SomeModel.model_validate(x)
return result
```

For repeated patterns in a file, extract a helper:

```py
def _to_response(data: object) -> SomeResponse:
    """Convert service result to response schema."""
    resp: SomeResponse
    resp = SomeResponse.model_validate(data, from_attributes=True)
    return resp
```

Avoid `# type: ignore[no-any-return]` and prefer typed locals over `cast()`.

## Export/PDF invariants (hard rules) (PR-8b / PR-8c)

### PDF export must be import-safe

- `reportlab` must be imported lazily (inside the handler/function), never at module import time.
- Use `_lazy_reportlab()` helper in `app/services/shoplist_export/pdf_export.py` for lazy imports.
- `ImportError` for optional PDF deps must return HTTP `501 Not Implemented` (no auto-install, no fallback hacks).
- Export modules/routers must have no import-time side effects beyond normal router registration.

### Determinism and data preparation

- PDF/CSV prepared output must be deterministic (use a canonical stable sort; e.g. `store_id → aisle → food_id`).
- Keep data preparation in a pure function (no `reportlab`) so tests can validate determinism without rendering.
- Use `build_pdf_lines()` in `pdf_export.py` to prepare `PdfLine` objects before rendering.
- Sorting key: `(store_id == "", store_id, aisle == "", aisle, food_id)` (non-empty values first).

### Product layout (PR-8b)

- PDF layout must group by `store → aisle` with clear visual hierarchy.
- Include subtotals per aisle and grand total at the end.
- Currency formatting: use `_fmt_money()` with quantize to 0.01, include currency code when available.
- Do not include exception details in error messages (security: no info leak).

### Contract freeze

- VIP auth behavior (`403`) and the VIP error response shape are contract-frozen; do not change without a dedicated PR.

## VIP contract + router invariants (PR-8c / #456)

### VIP error contract (frozen)

- VIP tier denial is `403` (do not use `401` for “has auth but not VIP”).
- VIP error responses must preserve the established envelope contract:
  - `status: "error"`, `code`, `message`
  - legacy aliases must remain: `detail == message`, `error == code` (see `app/contracts/vip_contract.py`).

### Router registration (centralized + idempotent)

- VIP router registration must be centralized via `app/routers/vip_registration.py:register_vip_routes`.
- Do not scatter conditional `include_router(...)` calls across modules; keep registration explicit and safe to call multiple times.

## No duplicated business logic (app vs core)

- Routers and services must not re-implement domain logic.
- If logic is needed in multiple endpoints, put it into `core/` and call it.
- BMI math (formulas/thresholds/grouping/interpretation) MUST live only in `core/bmi/*`; `app/*` is adapters/rendering only.
- `legacy_app.py` is compatibility-only: do not add new behavior there unless it is purely shim/bridge.
  - **Exception (approved)**: Observability endpoints (`/metrics`, `/health`, `/ready`, `/health/db`) are infrastructure concerns and may be added to `legacy_app.py` for operational visibility.

## Common pitfalls

- Import Hygiene: do NOT reintroduce dynamic module loading in `app/__init__.py`
  (no `spec_from_file_location`, no `exec_module`, no sys.path hacks).
- `import app` is a PEP 562 shim: `app.app` MUST point to `legacy_app.app`, and
  missing symbols are forwarded via `__getattr__`.
- Feature flags (e.g. exports) may be evaluated at import time; tests must set
  `TESTING=true` before importing `app`/`legacy_app` (handled in `tests/conftest.py`).

## app package public surface contract

`app/__init__.py` must remain an import shim/forwarder.
It MUST NOT use dynamic module execution (spec/module_from_spec/exec_module).

If tests import symbols from `app`, update:

- `tests/test_app_public_surface.py`
- `tests/test_repo_policy_guards.py` (required exports set)

### Required symbols (forwarded via PEP 562 __getattr__)

Tests expect these symbols to exist in `app` namespace:

- `app.app` (FastAPI instance)
- `resolve_attr`
- `make_weekly_menu`
- `build_nutrition_targets`
- `get_update_scheduler`

### Quick verification

```bash
# Check what tests require from app
rg -n "from app import \(|from app import " tests -S
rg -n "app\.(build_nutrition_targets|get_update_scheduler|resolve_attr|make_weekly_menu)" tests -S

# Smoke test
python - <<'PY'
import app
need = ["resolve_attr","make_weekly_menu","build_nutrition_targets","get_update_scheduler"]
print("missing:", [n for n in need if not hasattr(app, n)])
PY
```

## Feature map

| Feature | Owner | Key paths | Entrypoints | Tests | Docs |
|--------|-------|-----------|-------------|-------|------|
| BMI/body composition | backend | `core/bmi_*.py`, `core/bmi_extras.py`, `bmi_core.py`, `bodyfat.py` | `app/routers/bmi_pro.py` | `tests/test_bmi_*.py`, `tests/test_bodyfat.py` | - |
| Nutrition logging | backend | `app/routers/nutrition_log.py`, `app/models/events.py`, `app/schemas/nutrition_log.py` | `app/routers/nutrition_log.py` | `tests/test_nutrition_log_*.py` | - |
| Meal planning | backend | `core/meal_planner.py`, `core/weekly_plan*.py`, `core/menu_engine*.py` | `app/routers/premium_week.py` | `tests/test_premium_week_*.py`, `tests/test_menu_engine_*.py` | - |
| Food database | backend | `core/food_db*.py`, `core/food_apis/`, `data/food_db.csv`, `app/services/food_store.py` | `app/routers/foods.py` | `tests/test_food_db*.py`, `tests/test_food_apis*.py` | - |
| Recipe synthesis | backend | `core/recipe_synth.py`, `core/recipe_db*.py` | `app/routers/recipes.py` | `tests/test_recipe_*.py` | - |
| Shopping lists | backend | `core/shoplist.py`, `app/routers/shopping_list_pro.py`, `app/routers/shoplist_day.py`, `app/routers/shoplist_export.py` | `app/routers/shopping_list_pro.py` | `tests/test_shopping_list_*.py`, `tests/test_shoplist_*.py` | - |
| Premium/Pro features | backend | `app/routers/*_pro.py`, `core/bmi_extras_pro.py`, `app/middleware/api_tiers.py` | `app/routers/pro.py`, `app/routers/premium_week.py`, `app/routers/vip.py` | `tests/test_*_pro*.py`, `tests/test_premium_week_*.py` | - |
| User management | backend | `app/routers/users.py`, `app/schemas/users.py`, `core/models.py` | `app/routers/users.py` | `tests/test_users_*.py` | - |
| i18n/localization | backend | `core/i18n.py`, `core/meal_i18n.py` | `core/i18n.py` | `tests/test_i18n*.py` | - |
| Bayesian analyzers | backend | `core/*_bayesian_analyzer.py`, `core/bayes/` | `app/routers/bayes_adherence.py` | `tests/test_bayes_*.py`, `tests/test_bayesian_*.py` | - |
| Export/reports | backend | `core/exports*.py`, `app/routers/plan_export.py`, `app/routers/shoplist_export.py` | `app/routers/plan_export.py` | `tests/test_exports*.py` | - |
| LLM integration | backend | `llm.py`, `core/rag/`, `providers/` | `llm.py`, `mcp_pulseplate_server.py` | `tests/test_*rag*.py` | - |

## App Import Hygiene (quick checks)

Run from repo root.

### No dynamic module loading in app package

```bash
git grep -nE "spec_from_file_location|module_from_spec|exec_module\(" -- app || true
```

### app shim contract must hold

```bash
python - <<'PY'
import os
os.environ["TESTING"] = "true"
import app, legacy_app
assert app.app is legacy_app.app
print("OK: app.app is legacy_app.app")
PY
```

## Security hotfix rules (PR-501)

### Dockerfile runtime stage

- __No blanket `apt-get upgrade`__ in runtime — reduces drift and improves reproducibility.
- For CVE fixes with available patches: install the affected package explicitly after `apt-get update`.
- After update, `apt-get install <pkg>` fetches the latest patched version from Debian repos.

### Frontend-generated artifacts

- `frontend/public/mockServiceWorker.js` is __generated by MSW CLI__ — never edit manually.
- Regenerate via: `cd frontend && npx msw init public`
- CI uses `npm ci` (lockfile enforced) to prevent version drift.

### CVE claim policy

- Do not claim a CVE is "fixed" unless the distro security tracker shows a fixed version for our base distribution.
- Check: [Debian Security Tracker](https://security-tracker.debian.org/) before claiming remediation.
- If no fixed version exists yet: document as "unpatched/mitigation", add tracking issue, schedule base image bump once fixed lands.

### No-fix-yet CVE policy

When a CVE has no fix available in the base distro:

1. **Do NOT** add fake "install/upgrade" commands — they don't help and add churn.
2. **Document** in Dockerfile with tracking link.
3. **Dismiss** GitHub alert with reason "Fix not available / vulnerable in distro".
4. **Create tracking issue** to revisit on base image bump.

Example (CVE-2025-13151 / libtasn1):
- Package comes transitively via `libgnutls30` (required for TLS)
- No patched version in Debian bookworm as of 2026-01
- Documented in Dockerfile, tracking issue created, revisit monthly
