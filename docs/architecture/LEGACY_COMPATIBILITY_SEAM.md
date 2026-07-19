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

`legacy_app.py` is still the runtime compatibility base for the FastAPI app.
`app/main.py` imports `legacy_app.app`, applies canonical additive bootstrap, and
owns new canonical route registration. This is a transitional seam, not the
desired final architecture.

Application startup/shutdown behavior is canonically owned by
`app/bootstrap/lifespan.py`. `legacy_app.py` only passes that context manager to
its existing `FastAPI(...)` instance until app-factory ownership is inverted.
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
factory at `app/application_metadata.py:113`. `legacy_app.py:504` consumes that
immutable source while it remains the sole FastAPI-instance constructor and
temporarily exposes the same compatibility metadata values.

Public OpenAPI visibility, component pruning, builder ownership, and cache
reconciliation are canonically owned by `app/bootstrap/openapi.py:32` and its
validation/install/policy seams at `app/bootstrap/openapi.py:285`,
`app/bootstrap/openapi.py:310`, and `app/bootstrap/openapi.py:343`.
`app/main.py:1311` validates builder ownership before mutation, completes
additive route registration, then applies policy and installs the builder at
`app/main.py:1409`. This order prevents an early partial schema while preserving
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
| Existing legacy compatibility aliases | `legacy_app.py` | Runtime compatibility only; no growth. |
| Canonical app bootstrap | `app/main.py` | Additive, idempotent registration over the compatibility base. |
| New route implementations | `app/routers/` | Canonical route families own new behavior. |
| Operational health/readiness routes | `app/routers/health.py` + `app/main.py` | Runtime paths unchanged; no legacy decorator ownership. |
| Infra and observability bootstrap | `app/bootstrap/` | Register from canonical entrypoint, not from `legacy_app.py`. |
| Application lifecycle and shared resources | `app/bootstrap/lifespan.py` | One explicit startup/shutdown owner; deterministic reverse-order cleanup. |
| App-client API-key dependencies | `app/routers/api_key.py` | Canonical owner; legacy compatibility is identity-preserving re-export only. |
| Application metadata | `app/application_metadata.py` | Immutable source; every FastAPI projection receives fresh nested mutable inputs. |
| Public OpenAPI policy and builder | `app/bootstrap/openapi.py` | Validate before mutation; install after complete route bootstrap; stale/foreign state fails closed. |
| Admin scheduler access | `app/services/scheduler_access.py` | Lazy typed delegation only; core owns singleton/lifecycle and compatibility exports preserve service-callable identity. |
| Legacy weekly-menu builder access | `core/menu_engine.py` + `app/services/legacy_premium_weekly_plan.py` | Core owns the builder; the service provides lazy exact-callable access and response normalization; facade exports are compatibility only. |
| Legacy BMI visualization access | `bmi_visualization.py` + `app/services/bmi_compat.py` | The renderer owns chart generation; the service consumes local bindings and normalizes compatibility responses; facade exports are compatibility only. |
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
reverse imports and lookups, and bounded ordinary alias forms.

It is not a Python sandbox, abstract interpreter, or proof against intentionally
obfuscated source. Descriptor, metaclass, closure, arbitrary container or data-flow,
`eval` / `exec`, and equivalent reflective constructions remain subject to human
review and repository security tooling.

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
