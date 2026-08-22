# Legacy Compatibility Seam

Status: Accepted guardrail

<!-- LEGACY_SEAM_STATUS: accepted_guardrail -->
<!-- LEGACY_SEAM_RUNTIME_BEHAVIOR_CHANGED: false -->
<!-- LEGACY_SEAM_OPENAPI_CHANGED: false -->
<!-- LEGACY_SEAM_SEMANTIC_CACHE_SERVING: false -->
<!-- LEGACY_SEAM_FOODDB_CUTOVER: false -->
<!-- LEGACY_SEAM_BROAD_REFACTOR: false -->

The runtime-behavior marker above records that this compatibility seam does not
authorize a route/lifecycle/runtime expansion. It does not conceal the separately
reviewed, bounded sanitization of hidden admin error envelopes and the legacy
weekly-plan downstream error boundary documented below.

## Context

`app/bootstrap/application.py` constructs the sole production FastAPI singleton.
`app/main.py` imports it directly and owns additive composition; deployment
remains `app.main:app`. `legacy_app.py` is a transitional compatibility facade
that re-exports the same app, runtime environment, metadata, and lifespan.
Normal imports therefore share one app. The finite package facade resolves
`app.app` directly from `app.main.app` (`app/__init__.py:58-59`); a deliberate
test-only reassignment of `legacy_app.app` cannot rebind package, bootstrap, or
`app.main` authority. Plain `import app`, `dir(app)`, and unknown-name lookup do
not import `legacy_app`. Resolving `app.app` imports `app.main` without loading
`legacy_app`; the canonical bootstrap no longer reverse-imports the compatibility
facade. The eight former paid/BMI registration mirrors are absent from `app`,
`app.main`, and `legacy_app.py`. The later direct-call retirement removes only
ten additional `legacy_app.py` Python bindings; it does not remove or redirect
any HTTP path, change auth, alter OpenAPI, or change FastAPI object identity.
This bounded retirement does not prove that unknown external or dynamic Python
consumers of the removed compatibility symbols do not exist.

Application startup/shutdown behavior is canonically owned by
`app/bootstrap/lifespan.py`. `app/bootstrap/application.py` passes that exact
context manager to its constructor and `legacy_app.py` only re-exports it.
Food-search clients and the process-wide strategy adapter are acquired and
released inside that lifespan; additive route bootstrap must not create shared
runtime resources or wrap `app.router.lifespan_context`.

App-client API-key extraction and validation dependencies are canonically owned
by `app/routers/api_key.py`. Canonical routers and bootstrap code import those
callables directly. `legacy_app.py` may only re-export the exact same callable
objects while compatibility imports remain; wrappers or mutable legacy-owned
warning state would break FastAPI dependency identity.

Application metadata is canonically owned by
`app/application_metadata.py:56` and constructed through the environment-aware
factory at `app/application_metadata.py:113`. The application bootstrap builds
one immutable value and `legacy_app.py` aliases it for compatibility.

Public OpenAPI visibility, component pruning, builder ownership, and cache
reconciliation are canonically owned by `app/bootstrap/openapi.py:32` and its
validation/install/policy seams at `app/bootstrap/openapi.py:285`,
`app/bootstrap/openapi.py:310`, and `app/bootstrap/openapi.py:343`.
`app/main.py:1097` validates builder ownership before mutation, completes
additive route registration, then applies policy and installs the builder at
`app/main.py:1208-1209`. This order prevents an early partial schema while preserving
an equal cached schema object on a no-op bootstrap.

Admin scheduler access is canonically exposed by
`app/services/scheduler_access.py` as a lazy typed delegator. The core scheduler
module remains the only singleton and lifecycle owner, while `app` and
`legacy_app.py` expose the exact service callable for compatibility. Admin
operations consume that binding directly; compatibility resolver state and
module-table lookup are forbidden. This access cutover does not change routes,
auth, methods, OpenAPI, scheduler lifecycle, or worker topology. Operational
database-status, force-update, and update-check failures use stable generic 500
details while technical exceptions remain server-log-only.

The following direct-call Python bindings are retired from `legacy_app.py`:
`admin_status`, `cleanup_expired_logs`, `debug_env`, `get_database_status`,
`force_database_update`, `check_for_updates`, `rollback_database`,
`bmi_endpoint`, `plan_endpoint`, and `bmi_endpoint_v1`. Their canonical
implementations remain callable in `app/services/admin_operations.py:27` and
`app/services/bmi_compat.py:138`; HTTP ownership remains in
`app/routers/admin_operations.py:34` and `app/routers/bmi_compat.py:21`.
The `BMIRequest` / `BMIRequestV1` schema compatibility exports and BMI
visualization exports remain explicit in `legacy_app.py:49` and
`legacy_app.py:126`. Unknown external or reflective callers remain residual
compatibility risk; this lane makes no telemetry or consumer-census claim for
them and grants no authority to retire HTTP aliases. Runtime-absence tests prove
only the imported module state produced by the current checked source and test
environment; they do not prove absence under external monkeypatching, import
hooks, or another runtime environment.

The former synchronous `legacy_app.start_background_updates` /
`legacy_app.stop_background_updates` wrappers, their private scheduler bindings,
the `app.scheduler_helpers` resolver module, and the implicit `app_module`
module-table alias are retired. Canonical startup and shutdown continue to use
direct typed hooks in `app/bootstrap/lifespan.py`; scheduler mode, ordering,
timeouts, cleanup, and worker topology are unchanged. Retained package and
legacy `get_update_scheduler` exports remain the exact callable owned by
`app/services/scheduler_access.py`.

The canonical weekly-menu builder remains owned by
`core/menu_engine.py`. The hidden legacy premium weekly-plan route obtains the
exact callable through the lazy, uncached access seam in
`app/services/legacy_premium_weekly_plan.py`; it no longer selects mutable
`app`/`legacy_app` facade state or reads the module table. The service also owns
legacy response normalization, while `app/routers/legacy_premium_weekly_plan.py`
owns the hidden HTTP compatibility boundary. Public `app.make_weekly_menu` and
`legacy_app.make_weekly_menu` symbols remain import compatibility only. Exact
canonical-module absence retains the existing unavailable `503`; broken imports
and unknown downstream errors are logged server-side and exposed only through
the stable generic `500` envelope. Route auth, VIP/FitChef execution, OpenAPI,
and application identity remain unchanged.

Legacy matplotlib/base64 BMI rendering remains owned by
`bmi_visualization.py`. `app/services/bmi_compat.py` is the sole runtime
consumer for the hidden `/bmi` compatibility route and owns the legacy response
normalization around that renderer. Public `app` and `legacy_app.py`
visualization symbols remain import compatibility only; rebinding either
facade must not influence runtime renderer selection. The structured
`BMIScaleV1Spec` path in `app/services/bmi_visualization.py` is a separate
canonical contract and is not part of this compatibility seam.

Insight request/response schema ownership is canonical in
`app/schemas/insight.py`. The thin adapter in
`app/services/insight_compat.py` owns retained direct-call behavior, provider
and transparency adapters, quota enforcement, and sanitized failure envelopes;
it delegates orchestration to `app/services/insight_application_service.py`.
The hidden router in `app/routers/legacy_insight.py` imports canonical schemas,
security, and rate-limit policy and resolves adapter callables from
`app.services.insight_compat` at request time. `legacy_app.py` exposes exact
aliases only; canonical router, schema, adapter, and service modules must never
import or dynamically look it up.

The current policy is compatibility first:

- keep existing legacy routes callable when current clients still depend on
  them;
- hide or internalize legacy surfaces from public OpenAPI when the canonical
  route family owns the public contract;
- put new canonical route growth in `app/routers/` and `app/bootstrap/`, then
  register it through `app/main.py`;
- keep product truth, entitlement truth, AI runtime truth, FoodDB authority, and
  OpenAPI contract truth out of `legacy_app.py`.

## Decision

Freeze `legacy_app.py` as a compatibility seam. It may shrink or delegate more
thinly over time, but it must not grow new product behavior.

PR #2294 completed canonical FastAPI construction ownership. The bounded
`codex/retire-legacy-scheduler-app-module-compat` successor removed only the
package module alias and legacy synchronous scheduler compatibility rail. The
next bounded lane landed as PR #2309 at
`f561d37b2f0ad70b9d5ada9251572b0c9e033aac`, retiring the eight paid/BMI
registration mirrors and the canonical reverse import without changing route
registration. PR #2314 then merged at
`827f8ea0ba5bf0432e011241d08553b01fa471b1`, adding canonical PRO BMR and
nutrient-gap routes and moving the repository-owned Web Nutrition Setup BMR
consumer to the canonical namespace. The bounded
`codex/retire-legacy-admin-bmi-python-shims` successor removes only the ten
direct-call Python bindings enumerated above and adds a closed, exact-name
regression guard. All four versioned nutrition aliases and both root aliases
remain callable; versioned-alias retirement, root-alias auth/sunset, and final
legacy deletion remain separate ordered lanes behind their own evidence
(canonical route evidence: `app/routers/pro_nutrition_contracts.py:61` and
`app/routers/pro_nutrition_contracts.py:71`; bounded registrar evidence:
`app/bootstrap/pro_contracts.py:246`; Web consumer evidence:
`frontend/src/api/premium/bmr.ts:4`).

Allowed in `legacy_app.py`:

- existing compatibility aliases and response shaping;
- removal or narrowing of legacy surface;
- thin delegation to canonical routers, services, or core helpers;
- comments or markers that document the seam.

Forbidden in `legacy_app.py`:

- new `@app.*` routes;
- new `app.include_router(...)` or `app.add_api_route(...)` registrations;
- new `app.routers.*` imports for product route growth;
- new provider or LLM calls;
- new billing, entitlement, subscription, receipt, quota, or API-key behavior;
- new OpenAPI-visible public surface;
- semantic-cache serving, FoodDB cutover, DB writes, or broad refactors.

## Ownership Map

| Surface | Owner | Rule |
| --- | --- | --- |
| Existing legacy compatibility aliases | `legacy_app.py` | Runtime compatibility only; no growth; paid/BMI registration mirrors are retired. |
| FastAPI construction | `app/bootstrap/application.py` | Sole production constructor; no routes, middleware, OpenAPI, or resources. |
| Canonical app composition | `app/main.py` | Additive, idempotent registration on the supplied app; never rebind the singleton. |
| Package app facade | `app/__init__.py` | Finite lazy exports; `app.app` resolves only from `app.main.app`; no `app_module` alias. |
| New route implementations | `app/routers/` | Canonical route families own new behavior. |
| Operational health/readiness routes | `app/routers/health.py` + `app/main.py` | Runtime paths unchanged; no legacy decorator ownership. |
| Infra and observability bootstrap | `app/bootstrap/` | Register from canonical entrypoint, not from `legacy_app.py`. |
| Application lifecycle and shared resources | `app/bootstrap/lifespan.py` | One explicit startup/shutdown owner; deterministic reverse-order cleanup. |
| App-client API-key dependencies | `app/routers/api_key.py` | Canonical owner; legacy compatibility is identity-preserving re-export only. |
| Application metadata | `app/application_metadata.py` | Immutable source; every FastAPI projection receives fresh nested mutable inputs. |
| Public OpenAPI policy and builder | `app/bootstrap/openapi.py` | Validate before mutation; install after complete route bootstrap; stale/foreign state fails closed. |
| Hidden admin/debug routes | `app/routers/admin_operations.py` | Canonical HTTP owner; route methods, auth, hidden OpenAPI posture, and response contracts remain unchanged. |
| Admin/debug operations | `app/services/admin_operations.py` | Canonical direct-call owner; the seven former `legacy_app.py` bindings are retired. |
| Admin scheduler access | `app/services/scheduler_access.py` | Lazy typed delegation only; core owns singleton/lifecycle and compatibility exports preserve service-callable identity. |
| Scheduler startup/shutdown | `app/bootstrap/lifespan.py` + `core/food_apis/scheduler.py` | Direct typed hooks only; no legacy sync wrappers, helper resolver, module-table lookup, or caller-frame precedence. |
| Legacy weekly-menu builder access | `core/menu_engine.py` + `app/services/legacy_premium_weekly_plan.py` | Core owns the builder; the service provides lazy exact-callable access and response normalization; facade exports are compatibility only. |
| Legacy BMI visualization access | `bmi_visualization.py` + `app/services/bmi_compat.py` | The renderer owns chart generation; the service consumes local bindings and normalizes compatibility responses; facade exports are compatibility only. |
| Legacy BMI routes and direct-call runtime | `app/routers/bmi_compat.py` + `app/services/bmi_compat.py` | HTTP routes remain unchanged; the three former `legacy_app.py` endpoint bindings are retired while schemas and visualization exports remain. |
| Insight API contract | `app/schemas/insight.py` | Canonical request/response ownership; legacy compatibility exports preserve exact class identity and wire shape. |
| Insight compatibility routes | `app/routers/legacy_insight.py` | The two hidden VIP routes own route-level guards and consume canonical adapter attributes at request time; the legacy facade is not a runtime dependency. |
| Insight compatibility runtime | `app/services/insight_compat.py` + `app/services/insight_application_service.py` | The adapter owns retained callables and HTTP/error seams; the application service and `core/ai` retain orchestration truth. Facade rebinding and reverse imports are forbidden. |
| PRO targets/gaps API contracts | `app/schemas/premium_contracts.py` | Canonical request/response ownership; legacy imports preserve the existing wire shapes without parallel schema definitions. |
| PRO targets/gaps runtime | `app/services/pro_nutrition_targets.py` + `core/nutrition_utils.py` | The service owns typed targets/gaps orchestration and stable error envelopes; core owns shared kcal/micronutrient helpers; legacy exports are exact aliases or thin route shims only. |
| PRO targets/gaps routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | Canonical targets/gaps and retained compatibility routes call the service directly; the canonical family uses `require_pro_tier`, while legacy API-key behavior remains unchanged. |
| PRO Plate API contract | `app/schemas/premium_contracts.py` | The existing `PlateRequest` / `PlateResponse` wire shapes remain shared by canonical and retained routes. |
| PRO Plate runtime | `app/services/pro_nutrition_plate.py` + `core/` nutrition modules | The service owns typed Plate orchestration, bounded fallbacks, required sanitization, and stable error envelopes through direct core dependencies resolved per call; facade lookup, module-table lookup, mutable dependency registries, and import-time callable caches are forbidden. Legacy Plate service exports are exact aliases or thin compatibility wrappers only. |
| PRO Plate routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | Canonical and retained Plate handlers call the canonical service directly. Existing PRO-tier/API-key divergence, deprecation metadata, response models, and OpenAPI visibility remain unchanged. |
| Premium BMR API contract | `app/schemas/bmr.py` | Both retained request DTOs enforce the same finite core boundaries; the existing `BMRResponse` wire shape remains shared. |
| Premium BMR runtime | `app/services/pro_nutrition_bmr.py` + `core/bmr.py` | The service owns request-time feature gating, defensive dependency validation, localization, response assembly, and stable fail-closed errors through direct core callables resolved per call. Dynamic facade/module lookup, synthetic success stubs, and fallback TDEE values are forbidden. |
| PRO and retained BMR routes | `app/routers/pro_nutrition_contracts.py` + `app/routers/legacy_premium_nutrition.py` | `/api/v1/pro/nutrition/bmr` is the public PRO contract and Web consumer target. `/api/v1/premium/bmr` retains the app-client API-key dependency, `/premium_bmr` remains the historical public exception, and all three delegate directly to the same feature-gated service. |
| Domain logic | `core/` and `app/services/` | Backend truth stays outside route shims. |
| Public API contract | Backend OpenAPI gates | Legacy aliases must not become client contract truth. |

## Guard Contract

`scripts/ci/check_legacy_growth_guard.py` enforces this seam with static source
analysis. It parses `legacy_app.py` and the canonical lifecycle/food-search
bootstrap modules without importing application modules. It compares route,
router-import, and sensitive-call facts against the frozen baseline and rejects
legacy lifecycle implementations, startup/shutdown event registration, or
hidden `lifespan_context` mutation. It also rejects legacy API-key dependency
implementations and canonical `app/**` reverse imports or dynamic lookups for
those callables. Current facts may disappear as the seam shrinks; new facts fail
closed with repo-relative diagnostics.

For the ten retired direct-call bindings, the guard has a deliberately bounded
finite mechanical claim over the exact repo-relative `legacy_app.py` source
only. It freezes the exact ten-name set, uses the existing `_assigned_names`
collector for statically visible ordinary module-scope `Name` Store/Del
bindings, rejects explicit `global` declarations for a protected name, rejects
all star imports, and rejects a statically bound module-level `__getattr__`.
Unreadable source and `SyntaxError` fail closed. Comments, strings, function or
class locals without `global`, foreign object attributes, underscore/different
names, and canonical owner modules outside `legacy_app.py` are outside this
finite binding set.

The containing `legacy_app.py` module is parsed into an AST, but the
retired-binding rule does not recognize or interpret dynamic carrier families:
`globals()` / `locals()` / `vars()`, `sys.modules`, module `__dict__`, `setattr`
/ `delattr` in bare, imported, qualified, aliased, destructured, chained, or
bound forms, mapping `update` / `__setitem__` / `__ior__`, `eval` / `exec`,
import hooks, reflection, arbitrary helpers, and external monkeypatching. The
rule neither accepts nor certifies those families and makes no completeness
claim about them. Any new or changed dynamic namespace carrier in
`legacy_app.py`, and any dynamic carrier intended to bind or rebind one of the
ten protected names, requires manual STOP and review.

The same guard now verifies application-metadata/OpenAPI ownership: extracted
functions cannot be redefined or rebound in legacy, `app/main.py` must import
the canonical OpenAPI lifecycle directly, the package facade cannot install OpenAPI,
and canonical modules cannot reverse-import the compatibility app. The check is
bounded AST analysis and intentionally does not interpret arbitrary Python.

The guard does not authorize runtime behavior. It only prevents unreviewed seam
growth while later extraction PRs move routes behind canonical routers.

## Static Guard Threat Model

The legacy growth guard is an architectural regression detector for trusted,
reviewed repository source. It detects explicit ownership violations, direct
reverse imports and lookups, and the finite ordinary module bindings described
above.

It is not a Python sandbox, abstract interpreter, or proof against intentionally
obfuscated source. Descriptor, metaclass, closure, arbitrary container or
data-flow, `eval` / `exec`, dynamic import consumers, and equivalent reflective
constructions remain residual risk subject to human review and repository
security tooling. The exact-name binding guard must not be widened to imply a
complete census of open-world namespace mutation or runtime consumers.

Runtime contract tests, callable-identity tests, code review, targeted security
review, and current-head CI remain authoritative.

## Exit Criteria

Retire this seam only when all are true:

1. `app/main.py` no longer depends on `legacy_app.app` as the runtime base.
2. Remaining compatibility aliases are either removed or implemented as bounded
   canonical router shims.
3. OpenAPI namespace guards stay deterministic after removal.
4. Auth, billing, export, insight, food-data, and websocket contracts have route
   parity coverage for any moved surface.
5. Backlog or PR governance records the final compatibility retirement evidence.

## Validation

Use:

```bash
python3 scripts/ci/check_legacy_growth_guard.py
pytest -q tests/test_legacy_growth_guard.py
```

This guard does not open runtime behavior, OpenAPI, semantic-cache serving,
FoodDB cutover, or broad refactor scope.
