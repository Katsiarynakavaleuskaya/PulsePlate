# PR #2061 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2061

Branch: `codex/move-business-registration-to-canonical-bootstrap`

## Summary

This PR moves business route registration ownership from `legacy_app.py` to the
canonical `app.main` bootstrap and changes `BUSINESS_MODULE_ENABLED` to an
explicit-truthy feature flag contract. The business routes stay absent by
default, `/api/v1/business/analyze` keeps `require_app_api_key`, `/status`
keeps its existing unauthenticated behavior when enabled, and final public
OpenAPI remains free of `/api/v1/business/*`.

## Scope

- Add reusable explicit-truthy env parsing in `app.utils.feature_flags`.
- Add `BUSINESS_ROUTE_SPECS` in `app/routers/business.py`.
- Register the business route family from `app/main.py` through
  `ensure_route_family_registered(...)` only when the business feature flag is
  explicitly truthy.
- Remove business router import/registration ownership from `legacy_app.py`.
- Tighten the legacy-growth guard allowlist and regression coverage for direct,
  aliased, module-qualified, dynamic, and walrus reintroduction patterns.
- Add focused business bootstrap tests and update backend routing docs.

## Out Of Scope

No Bayesian analyzer, nutrition, shopping, FoodDB, frontend, iOS, macOS, auth
redesign, generated OpenAPI/client artifact changes, middleware, lifespan, or
app-factory refactor is included.

## Implementation Commits

- `322584475a96f25dfee803979c471a92992206c4` - moves business route
  registration to canonical bootstrap, removes legacy ownership, adds the
  explicit feature-flag helper, tightens guards, updates docs, and adds focused
  route-family tests.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d880f5d825dd.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role order executed pre-open:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Experiment Runner Evidence

Artifact:
`artifacts/orchestration/experiments/results/exp-866cae82ee55.json`

- Mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Experiment ID: `exp-866cae82ee55`
- Source diff applied: `true`
- Oracle commands executed: `3`
- Contribution kind: `oracle_review`
- Co-author required: `true`
- Commit trailer present in `322584475a96f25dfee803979c471a92992206c4`.

Zero-network local attempt:
`artifacts/orchestration/experiments/results/exp-2b53d4ed97f6.json` recorded
`status=rejected`, `failure_class=infra_flake`, because the macOS local
network-disabled sandbox lacked Linux `unshare`. The accepted packet used
`network_budget=1`; oracle commands remained local deterministic checks.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `pytest -q tests/test_business_registration_bootstrap.py tests/test_business_router.py tests/test_business_router_coverage.py tests/test_legacy_growth_guard.py`
- PASS: `pytest -q tests/test_business_registration_bootstrap.py tests/test_business_router.py tests/test_business_router_coverage.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `DEV_PYTHON=<repo .venv python> make openapi-check`
- PASS: `pytest -q tests/test_openapi_determinism.py::test_openapi_pipeline_uses_current_python_for_make tests/test_openapi_determinism.py::test_openapi_and_schema_ts_are_deterministic`
- PASS: `git diff --check`
- PASS: `DEV_PYTHON=<repo .venv python> VENV_PYTHON=<repo .venv python> make validate-changed`
- PASS: `pre-commit run --all-files`

Full local `make verify` was intentionally not run under the repository local
full-verify budget rule. Heavy/current-head CI remains the merge evidence
source.

## Discussion Thread Pass

- [x] Initial fixed-mapping artifact created after PR open.
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Post-open `qa-engineer-agent` pass completed.
- [ ] Post-open `bug-hunter` pass completed.
- [ ] Post-open `security-auditor` pass completed.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, and Cubic actionables checked and dispositioned.
- [ ] Review threads checked, dispositioned, and resolved if any appear.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Initial Mapping Evidence

Disposition: NOT-A-BUG

Finding: No actionable review threads existed at initial PR creation.

Evidence: PR #2061 was opened after focused local gates, pre-open role passes,
premortem, and accepted Experiment Runner oracle evidence. Post-open review
passes and bot thread disposition remain pending in this artifact until they
are actually complete.

## Premortem Finding Closure

Disposition: FIXED

Finding: Moving business registration could accidentally default-enable hidden
business routes.

Evidence: `app/main.py` registers the business route family only when
`is_business_module_enabled()` returns true, and
`tests/test_business_registration_bootstrap.py` covers unset, empty, false,
`0`, `no`, and `off` as absent.

Disposition: FIXED

Finding: Route dependency behavior could drift during ownership migration.

Evidence: `tests/test_business_registration_bootstrap.py` verifies
`/api/v1/business/analyze` contains the same `require_app_api_key` callable in
the route dependency graph and verifies `/status` remains callable without auth
when the module is enabled.

Disposition: FIXED

Finding: Source route visibility could leak business routes into public
OpenAPI.

Evidence: `BUSINESS_ROUTE_SPECS` preserves current source visibility, and
`tests/test_business_registration_bootstrap.py` verifies final `app.openapi()`
does not expose `/api/v1/business/*`. `make openapi-check` also produced zero
generated artifact diff.

Disposition: FIXED

Finding: Legacy guard allowlists could continue to permit business router
reintroduction.

Evidence: `scripts/ci/check_legacy_growth_guard.py` removes the business router
legacy facts, and `tests/test_legacy_growth_guard.py` covers direct, aliased,
module-qualified, dynamic, and walrus reintroduction patterns.

Disposition: NOT-A-BUG

Finding: `make validate-changed` can false-green before an implementation
commit because the branch-diff selector may not see staged-only changes.

Evidence: `make validate-changed` was rerun after implementation commit
`322584475a96f25dfee803979c471a92992206c4`; it selected and passed
`tests/security/test_api_authz_contract_static.py`,
`tests/test_business_registration_bootstrap.py`, `tests/test_business_router.py`,
`tests/test_business_router_coverage.py`, and `tests/test_legacy_growth_guard.py`.

## Post-open Role Review Evidence

Pending. Required post-open pass order remains:
`qa-engineer-agent -> bug-hunter -> security-auditor`, followed by Codex
Security diff scan / finding discovery and `pulseplate-pr-review`.

## Codex Security Evidence

Pending.

## pulseplate-pr-review Disposition

Pending.

## Merge Readiness

Not ready yet.

- Local focused gates: PASS.
- Fixed mapping artifact: created.
- Current-head GitHub CI: pending.
- Post-open role/security review: pending.
- Review thread / bot actionable disposition: pending.
- Strict merge-readiness wrapper: pending.

No merge-readiness, ready, green, or mergeable claim is made by this artifact.
