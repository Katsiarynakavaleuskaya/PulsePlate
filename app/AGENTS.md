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

## FitChef route and runtime policy

- Current live FitChef public routes remain `/api/v1/insight/fitchef*`; new FitChef work must preserve these routes and add future structured-coach surfaces additively.
- Foundation or visual-lane PRs must not migrate FitChef traffic to `/api/v1/pro/fitchef/*` or `/api/v1/vip/fitchef/*` until a dedicated contract PR freezes those paths.
- Keep FitChef guard order aligned with the live mascot routers: tier/feature gate -> execution-mode gate -> input guard -> provider/tool execution. Do not change this precedence in docs-only PRs.
- FREE tier must not receive open-ended FitChef runtime; bounded or static guidance only.
- Route handlers must return structured response models or frozen response envelopes; UI clients must not depend on parsing raw model prose.

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
- `http_requests_total` materializes numeric `0` children for exactly the four
  versioned `POST /api/v1/premium/{bmr,targets,plate,gaps}` aliases at
  `status="200"`; absence is never interpreted as zero. Root aliases and
  canonical `/api/v1/pro/nutrition/*` routes are not seeded.

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
- Endpoint: `app/bootstrap/metrics.py` (hidden from OpenAPI via `include_in_schema=False`)

**Limitations:**
- Multiprocess mode not enabled: `/metrics` returns per-process metrics only.
- For multi-worker deployments (gunicorn/uvicorn workers), metrics are not aggregated across workers.
- To enable multiprocess mode: configure `prometheus_client` multiprocess mode + `PROMETHEUS_MULTIPROC_DIR` (requires explicit infra decision).

**Prometheus route label policy (enforced):**
- Route label MUST be route template only (from `APIRoute.path` via endpoint identity matching).
- Raw/normalized path fallback is **forbidden** for non-excluded requests (prevents high cardinality).
- If route template is unavailable → use `"unknown"` (never fallback to `request.url.path`).

**Observability security policy:**
- `/metrics` MUST enforce application-level authentication via the shared API key guard.
- `/metrics` additionally accepts the metrics-only credential from the regular,
  non-symlink file selected by `METRICS_SCRAPE_KEY_FILE` (default
  `/run/secrets/pulseplate_metrics_scrape_key`). The file contains exactly one
  32..256-byte printable non-whitespace ASCII token. Default-file absence keeps
  shared-key compatibility; explicit invalid configuration grants no dedicated
  access and fails production-like startup. The dedicated token must differ
  from `API_KEY` in production/staging and has no authority on other routes.
  The OBS1B host contract is a mode-`0700` parent directory plus a mode-`0444`
  leaf so the app and Prometheus containers can read one bind-mounted file as
  different non-root UIDs; an owner-only leaf-mode check is forbidden in this
  app-layer recognizer.
- Premium-alias evidence must derive release/image/config/volume/topology and
  retention from the live Compose containers through the absolute Docker
  executable; CLI assertions are not evidence. The expected scrape target count
  is the frozen literal `1`. Hash only the container-visible Prometheus config
  from one bounded `docker cp <id>:/etc/prometheus/prometheus.yml -` tar with
  exactly one safe regular member; host `Mounts.Source` bytes are not evidence.
  Bind both the local image ID and the bounded digest-pinned `Config.Image`
  reference. Container `promtool check service-discovery` is the delegated
  config/target recognizer and must prove one `pulseplate-api` target at
  `http://app:8000/metrics`, instance `app:8000`, interval `30s`, timeout `10s`,
  with exact Compose services `app` and `prometheus` in one project. Derive
  `observed_at`/`T1` from one
  live Prometheus `time()` anchor, pass that exact value through `--time=` to
  every later query, bind promtool to the pre-census container ID, and require an
  exact post-query container/process/runtime census match. Docker output must be
  streamed under the bounded verifier limit; output overflow, timeout, JSON
  depth exhaustion, or any runtime replacement is `HOLD`.
  Except for the job-wide one-target census, every live, continuity, restart,
  and alias current/increase/reset query is scoped to both
  `job="pulseplate-api"` and `instance="app:8000"`; alias status stays unfiltered.
- Protection of `/metrics` is defense-in-depth and includes infrastructure controls:
  - ingress ACLs (Cloudflare, Caddy)
  - firewall rules
  - private networks
  - Prometheus scrape configs
- App-level guards are required to reduce reconnaissance surface when infrastructure ACLs drift.
- Explicit test bypass is allowed only via `METRICS_TEST_BYPASS=true` during pytest-scoped execution.
- `METRICS_TEST_BYPASS` is test-only and MUST NOT be enabled in staging or production.

**Testing requirements:**
- Tests MUST assert `/metrics` returns a Prometheus exposition response (`Content-Type` starts with `text/plain`) on happy path.
- Tests MUST NOT assert an exact `Content-Type` value (version/charset are implementation details of `prometheus_client`).
- Only assert prefix: `text/plain` for Prometheus; `application/json` for fallback.
- JSON fallback should only be tested when exporter is explicitly unavailable (mocked/uninstalled).
- This prevents regressions where fallback triggers incorrectly (e.g., import errors, missing dependencies).
- Zero-series tests must use an isolated Prometheus registry and distinguish
  `None` (absent labelset) from numeric `0.0`; auth tests must prove the
  metrics-only token cannot authenticate an ordinary protected endpoint.
- Every premium-alias evidence JSON is an asset with `asset_type`, ordered
  fingerprint-only `upstream_assets`, `policy_version`, `idempotency_key`, and
  explicit replay/admission behavior. Its deterministic `fingerprint` hashes the
  canonical JSON projection excluding only the `fingerprint` field. First write
  is new-only `0600` + `fsync`; an identical same-idempotency replay is verified
  without a write, while malformed, different-idempotency, or divergent existing
  output fails closed. A failed direct `O_EXCL` write is never auto-unlinked: the
  exact mode-`0600` canonical partial/complete file remains as evidence and a
  retry fails closed unless it validates as an identical replay; identical replay
  fsyncs the already-open file and pinned directory descriptor before returning.
- Before publication or replay, validate the exact evidence schema and top-level
  field set, mode/decision/reason vocabulary, static-false authority, and every
  checks/identity/topology/retention/target/alias/window type and finite value;
  recomputing a fingerprint never legitimizes an unknown or widened shape.

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
- See root `AGENTS.md` — `Git workflow (single-developer safe mode)` for push hygiene.

---

## Conventions

- FastAPI + Pydantic v2 only; prefer `model_validator`/`field_validator`.
- Keep routers thin; push business logic into `core/` or `app/services/`.
- Use dependency injection via `Depends`; keep side effects in services.
- Use `fastapi.status` for status codes and `HTTPException` for errors.
- Keep API schema changes in sync with `app/schemas/` and tests.
- Apply tier guards (`require_pro_tier`, VIP) consistently on gated endpoints.
- Tier resolution policy: DB-first when `SUBSCRIPTION_DB_ENABLED=true`.
- **DB lookup policy** (when enabled): `ERROR` and `INVALID_TIER` are **fail-closed** (no env
  fallback). `MISS` may fallback only during migration; plan DB-authoritative follow-up.
- Never fail-open on tier checks.

## Billing truth close-out policy

- Protected PRO/VIP access must derive only from persisted backend entitlement state.
- Manual verified compat may unlock legacy paid rows only when `activated_at` is present and usable.
- Rows without usable activation evidence must fail closed and must not unlock protected routes.
- Apple upstream transport failures must return deterministic backend error envelopes.
- Activation readback endpoints expose the current entitlement view unless a different contract is documented explicitly.

## WebSocket realtime hardening (PR-783 follow-up)

- Any change to `/ws` message handling MUST include deterministic tests for:
  - one success path (e.g. `ping` -> `pong`), and
  - one fail-closed path (e.g. malformed version / disallowed event / policy close).
- Protocol version rules are strict:
  - if `version` key is present and not a string -> reject (policy close),
  - legacy fallback is allowed only for explicitly supported legacy messages.
- Per-process active connection cap is mandatory for `/ws`:
  - use `WS_MAX_CONNECTIONS` policy setting,
  - reject over-cap connections fail-closed with policy close (1008),
  - release tracker state in `finally` on every exit path.
- Idle-timeout policy for `/ws` must remain deterministic:
  - use `WS_IDLE_TIMEOUT_SECONDS` with default `0` (explicitly disabled),
  - if timeout is enabled (`>0`), close idle connections fail-closed with policy close (1008),
  - tests for timeout branches must not use `sleep()`; use deterministic timeout injection/mocking.
- WebSocket response serialization should be deterministic (`sort_keys=True` where applicable)
  so tests and cross-runtime behavior remain stable.

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
- FastAPI method/path duplicates are forbidden. When a route family is touched,
  the registrar must either prove exact idempotent ownership or fail closed on
  partial registration, duplicate source routes, foreign existing handlers, or
  missing required dependencies. Never leave duplicate routes as "known inherited"
  behavior after they surface in a PR.
- Router/bootstrap production code must not accept `None`, empty placeholder
  routers, fake keys, or softened compatibility branches as success. If a
  canonical route family is enabled, missing or empty route owners are
  configuration errors and must fail closed; update stale tests instead of
  weakening runtime invariants.

### Static route-family bootstrap guard

- Exact static route families registered from `app/main.py` should use
  `app/bootstrap/route_family.py` with `RouteMemberContract` and
  `ensure_route_family_registered(...)`.
- Use this helper only for fixed source routers with stable path/method/OpenAPI
  visibility/status-code/dependency contracts. It validates source routers before
  registration and validates existing app routes for idempotency, partial
  registration, duplicate/foreign handlers, required dependency drift, response
  metadata drift, and OpenAPI visibility drift.

### Canonical HTTP middleware ownership

- HTTP middleware implementations belong in `app/middleware/*`, and their
  registration order belongs to the canonical
  `app/bootstrap/http_stack.py` registrar invoked from `app/main.py`.
  `legacy_app.py` must not register middleware directly or indirectly.
- New custom HTTP middleware should use pure ASGI unless the PR documents why
  `BaseHTTPMiddleware` is required. Middleware changes must prove ordering,
  idempotency, partial-state failure, non-HTTP behavior, streaming behavior,
  OpenAPI neutrality, and sensitive-log minimization.
- Do not add a second request-lifecycle logging layer when canonical metrics,
  request telemetry, and tracing already provide the required signal.

### Canonical application lifecycle ownership

- Application startup/shutdown ownership belongs in `app/bootstrap/lifespan.py`.
  `app/bootstrap/application.py` passes that exact context manager to the sole
  production `FastAPI(...)` constructor; `legacy_app.py` only re-exports it.
- Shared clients and process-wide adapters must be acquired during lifespan
  startup, never additive route bootstrap or module import, and released with
  deterministic reverse-order cleanup after partial startup and cancellation.
- Startup failure policy must remain explicit: security, production DB, and
  template failures are fail-closed; optional background updates are
  best-effort only where the existing contract says so.
- Canonical lifecycle dependencies must be direct typed callables. Do not
  resolve them through `sys.modules`, caller frames, `app_module`, the `app`
  facade, or legacy monkeypatch precedence.
- `app/bootstrap/application.py` owns construction, runtime-env setup, metadata,
  and the singleton only. `app/main.py` composes a supplied app without rebinding
  its canonical `app`; `legacy_app.py` remains a compatibility re-export.
- `tests/test_application_instance_ownership.py` scans `legacy_app.py` and
  `app/**/*.py` for only the three declared direct `FastAPI` call shapes. It is
  not a Python interpreter; any novel semantic carrier requires rescope.
- A lifespan-only PR must not also change FastAPI instance identity, OpenAPI
  policy, deployment entrypoints, or worker topology.

### Canonical application metadata and OpenAPI ownership

- Application metadata belongs in `app/application_metadata.py`; keep its source
  values immutable and create fresh nested dict/list constructor inputs for each
  FastAPI instance. The application bootstrap resolves the runtime environment
  and builds metadata once; compatibility modules alias that value.
- Public-path filtering, schema-reference pruning, and the custom OpenAPI builder
  belong in `app/bootstrap/openapi.py`. `legacy_app.py` may temporarily re-export
  the exact canonical objects, but wrappers or rebinding are forbidden.
- Canonical bootstrap order is fail-closed: validate the live builder before any
  mutation, register all routes, apply public OpenAPI input policy, then install
  the canonical builder. `app/__init__.py` must not install or mutate OpenAPI.
- Builder ownership requires exact live-marker identity, same-app binding, and a
  versioned structural protocol. Bump the protocol whenever builder semantics
  change; stale, partial, foreign, or wrong-app states must raise.
- OpenAPI requests remain cache-backed. Bootstrap may preserve an existing cache
  object only when a freshly generated complete filtered schema is equal; an
  unknown first-install cache or any public schema drift must be replaced.
- Effective included-router visibility changes must update both the live FastAPI
  route context and its `original_route`; OpenAPI hiding is never authorization.

## No duplicated business logic (app vs core)

- Routers and services must not re-implement domain logic.
- If logic is needed in multiple endpoints, put it into `core/` and call it.
- BMI math (formulas/thresholds/grouping/interpretation) MUST live only in `core/bmi/*`; `app/*` is adapters/rendering only.
- `legacy_app.py` is compatibility-only: do not add new behavior there unless it is purely shim/bridge.
  - Observability and operational endpoints are infrastructure concerns, but their route
    ownership belongs in canonical routers/bootstrap such as `app/routers/health.py`
    and `app/main.py`, not new `legacy_app.py` decorators.
- After a legacy route owner moves into `app/routers/*`, request/response schemas
  belong in `app/schemas/*` and reusable behavior helpers belong in
  `app/services/*`; `legacy_app.py` may only re-export or delegate unless a PR
  documents a narrower exception.
- Premium BMR orchestration belongs to `app/services/pro_nutrition_bmr.py`,
  while formulas remain in `core/bmr.py`. Both retained BMR routes call that
  service directly and share the request-time premium-nutrition feature gate;
  `sys.modules`/facade lookup, mutable dependency registries, patch-sensitive
  gate bypasses, synthetic success stubs, and fallback calorie values are
  forbidden.
- Legacy AI/insight routes must not own provider orchestration in
  `legacy_app.py`. `app/schemas/insight.py` owns the request/response models,
  `app/services/insight_compat.py` owns retained compatibility callables and
  their patchable runtime dependencies, and reusable orchestration stays in
  `app/services/insight_application_service.py` and `core/ai/*`.
  `legacy_app.py` may only expose exact canonical aliases for documented
  direct-import compatibility. Any AI route extraction must preserve
  wellness-only transparency, input guards, quota/rate-limit behavior, provider
  fallbacks, and OpenAPI hiding; do not introduce new provider behavior,
  semantic-cache serving, or medical/therapy claims in a route-ownership PR.
  The canonical router resolves transparency, quota, and retained callables
  from `app.services.insight_compat` at request time and reads the shared input
  guard from `app.security.agent_input_guard`; tests patch those exact consumer
  modules, never facade bindings, module tables, or per-carrier resolvers.

## Common pitfalls

### Canonical app-client API-key dependency ownership

- `api_key_header`, `get_api_key`, `_get_api_key_dynamic`,
  `validate_app_api_key`, and `require_app_api_key` belong to
  `app/routers/api_key.py` and remain separate compatibility/security contracts.
- Canonical routers and bootstrap code import these callables directly from the
  canonical module, never from `legacy_app.py` or through legacy-module
  `getattr` lookup.
- `legacy_app.py` may temporarily re-export the exact callable objects; wrappers
  are forbidden because FastAPI dependency overrides key on callable identity.
- API keys are app-client credentials, not authenticated user/principal truth.
- Unexpected validation failures must keep stable generic client envelopes and
  must not log key values, exception messages, or credential-bearing traceback.

### Canonical admin scheduler access

- `core/food_apis/scheduler_runtime.py` owns scheduler-mode resolution and the
  attempt-scoped update lease. Exact modes are `external`, `in_process_dev`,
  and `disabled`; aliases, whitespace-normalized values, and unknown values
  fail closed. Production/staging forbid `in_process_dev`.
- `core/food_apis/scheduler.py` owns the scheduler singleton, update algorithms,
  and the no-ingress worker CLI. `--serve` is external-mode-only; `--once`
  permits `external` or `disabled` and runs one leased due-check.
- Production API processes use `external` mode and must not import or own the
  periodic scheduler loop. `app/bootstrap/lifespan.py` loads scheduler hooks
  only for explicit non-production `in_process_dev` mode.
- The API singleton does not install process signal handlers. Direct scheduler
  construction preserves the compatibility default; the dedicated worker owns
  its own signal handlers.
- PostgreSQL coordination uses one stable repository-owned 64-bit advisory key.
  Acquisition, the complete scheduled/admin update operation, and unlock must
  use the same dedicated SQLAlchemy session/connection. Unknown acquire or
  release state invalidates the connection and fails closed. Process-local
  locking is allowed only in explicit non-production development/test runtime.
- The lease proves only that cooperating paths using the same PostgreSQL
  database and key do not execute the guarded body concurrently while the
  owning session remains valid. It is not exactly-once delivery, leader
  election, fencing, fairness, worker-health, or multi-host cache coherence.
- Canonical compose deployments in `external` mode run one `worker` service
  from the exact backend image, without ports or ingress, after migrations and
  API readiness. The worker is behind the opt-in `scheduler-external` profile;
  deploy scripts explicitly target it only for external ownership. In
  `disabled` mode, the deployment removes the stopped worker container, and
  unprofiled full-stack startup must not select it, so daemon restart cannot
  revive stale external configuration. API and worker share the named food-cache
  volume; this remains a single-host topology.
- `app/services/scheduler_access.py` is a lazy, typed delegator; it must not add
  cache, override registry, fallback state, or lifecycle logic.
- Admin services import and await the scheduler-access callable at their use
  site. Do not reintroduce `sys.modules` lookup, compatibility getter selection,
  or synchronous getter support.
- `app.get_update_scheduler`, `legacy_app.get_update_scheduler`, and
  `app.services.scheduler_access.get_update_scheduler` must be the exact same
  callable. Identity with the core getter is intentionally not required across
  the lazy boundary.
- `admin_status` preserves intentional `HTTPException` pass-through and maps an
  unavailable scheduler to stable `503 Scheduler unavailable`. Database status,
  update check, and non-contention force-update failures must log technical
  failures and expose only stable generic `500` details. Definite canonical
  lease contention from admin force-update or rollback maps to deterministic
  `409 update_already_in_progress`; uncertain lease state remains a generic
  server failure.

### Canonical legacy weekly-menu builder access

- `core/menu_engine.py` owns `make_weekly_menu`; the hidden legacy weekly-plan
  route resolves it only through the lazy, uncached getter in
  `app/services/legacy_premium_weekly_plan.py`.
- The getter must return the exact core callable. Only absence of `core` or
  `core.menu_engine` may produce an unavailable result; missing exports, plain
  `ImportError`, transitive `ModuleNotFoundError`, and non-callable exports are
  broken-runtime failures.
- Production resolution must not inspect `sys.modules`, `app`, `app_module`,
  `legacy_app`, package dictionaries, mutable overrides, registries, or cached
  fallback state. Public `app.make_weekly_menu` and
  `legacy_app.make_weekly_menu` remain compatibility exports, not route
  authority.
- Keep the route's API-key dependency and request-time VIP gate ahead of
  builder resolution. Only the two reviewed static downstream `422` details
  may cross the route boundary; all other downstream HTTP or unexpected errors
  use the fixed server log and generic client `500` contract.
- A builder-access cutover must not change the core menu algorithm, canonical
  VIP/FitChef execution, route registration, OpenAPI, or FastAPI app identity.

- Import Hygiene: do NOT reintroduce dynamic module loading in `app/__init__.py`
  (no `spec_from_file_location`, no `exec_module`, no sys.path hacks).
- `import app` is a finite PEP 562 facade: in normal runtime `app.app`,
  `legacy_app.app`, `app.main.app`, and the bootstrap singleton are identical.
  The package facade always resolves `app.app` from `app.main.app`; a test-only
  reassignment of `legacy_app.app` cannot rebind package, bootstrap, or
  `app.main` authority. Plain `import app`, `dir(app)`, and unknown-name lookup
  must not import `legacy_app`, and the retired `app_module` alias must never be
  installed in `sys.modules`. Only the explicit compatibility exports below may
  resolve via `__getattr__`. Ordinary package globals and Python-created submodule
  bindings are not compatibility exports. Names that are neither existing
  package attributes nor explicit compatibility exports must raise a
  facade-owned `AttributeError`; unknown-name lookup and `dir(app)` must not
  import or enumerate `legacy_app`.
- Feature flags (e.g. exports) may be evaluated at import time; tests must set
  `TESTING=true` before importing `app`/`legacy_app` (handled in `tests/conftest.py`).
- AgentGuard runtime/test bypasses must not key off `TESTING=true` alone:
  live bridge suppression is allowed only for pytest-scoped execution
  (`PYTEST_CURRENT_TEST` present), while targeted bridge coverage must opt in
  explicitly via `GOPLUS_AGENTGUARD_IN_TESTS=true`.

## app package public surface contract

`app/__init__.py` must remain a finite explicit compatibility facade.
It MUST NOT use dynamic module execution (spec/module_from_spec/exec_module).

If tests import symbols from `app`, update:

- `tests/test_app_public_surface.py`
- `tests/test_repo_policy_guards.py` (required exports set)

### Complete compatibility surface

The facade-owned compatibility surface is exactly this 16-name set. Ordinary
package globals and Python-created submodule bindings are outside this contract:

- `app.app` (FastAPI instance)
- `resolve_attr`
- `make_weekly_menu`
- `build_nutrition_targets`
- `metrics`
- `lifespan`
- `get_update_scheduler`
- `api_key_header`
- `get_api_key`
- `_get_api_key_dynamic`
- `get_bodyfat_router`
- `MATPLOTLIB_AVAILABLE`
- `generate_bmi_visualization`
- `BMIRequest`
- `_is_truthy`
- `_macros_to_kcal`

### Quick verification

```bash
# Check what tests require from app
rg -n "from app import \(|from app import " tests -S
rg -n "app\.(build_nutrition_targets|get_update_scheduler|resolve_attr|make_weekly_menu)" tests -S

# Smoke test
python - <<'PY'
import app
need = [
    "app", "resolve_attr", "make_weekly_menu", "build_nutrition_targets",
    "metrics", "lifespan", "get_update_scheduler", "api_key_header",
    "get_api_key", "_get_api_key_dynamic", "get_bodyfat_router",
    "MATPLOTLIB_AVAILABLE", "generate_bmi_visualization", "BMIRequest",
    "_is_truthy", "_macros_to_kcal",
]
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

### app facade contract must hold

```bash
python - <<'PY'
import os
os.environ["TESTING"] = "true"
import app, legacy_app
from app.bootstrap.application import app as canonical_app
from app.main import app as main_app
assert canonical_app is main_app is app.app is legacy_app.app
print("OK: one canonical app across normal runtime facades")
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
