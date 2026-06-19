# PR 1997 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1997

Branch: `codex/shrink-legacy-export-router-registration-seam`

## Summary

This PR moves canonical `plan_export` router registration ownership from
`legacy_app.py` into canonical `app/main.py` bootstrap. It preserves the public
method/path surface, app-level API-key dependency, weekly export signed-token
guard, rate-limit metadata, route-level OpenAPI visibility, final public OpenAPI
hiding, and hidden legacy export aliases.

## Scope

- Remove only `export_router` / `plan_router` import and registration from
  `legacy_app.py`.
- Add `PLAN_EXPORT_ROUTE_SPECS` in `app/routers/plan_export.py`.
- Register `export_router` and `plan_router` from `app/main.py` through an
  idempotent fail-closed helper.
- Tighten `scripts/ci/check_legacy_growth_guard.py` so reintroduced legacy
  imports/includes fail.
- Add focused bootstrap, guard, export auth/dependency, 429 metadata, and
  OpenAPI-hiding tests.
- Update `docs/architecture/backend_routing_map.md` for route ownership truth.

## Out Of Scope

No OAuth/OIDC rewrite, auth rewrite, tier semantics change, dependency update,
semantic cache, FoodDB, frontend/iOS work, or re-extraction of legacy export
aliases.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/437b193fba29.json`
- Runtime dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/437b193fba29.json --mode runtime --implementation-owner security-auditor --implementation-owner backend-engineer --pretty`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Starter: `check_preflight.py`, `check_agent_consistency.py`, and
  `task_bootstrap.py`; packet creation was treated as provenance only, not role
  execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `. .venv/bin/activate && pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_app_endpoints_combined.py tests/test_plan_export_additional.py tests/test_export_signed.py tests/test_legacy_export_aliases.py tests/test_rate_limit_llm_and_exports_api.py tests/security/test_api_auth_tier_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py tests/test_week_export_csv.py tests/test_signed_links.py`
  (`256 passed`)
- PASS: `. .venv/bin/activate && pytest -q tests/test_rate_limit_llm_and_exports_api.py::test_plan_week_export_csv_rate_limited_200_then_429 tests/test_rate_limit_llm_and_exports_api.py::test_export_sign_rate_limited_200_then_429`
- PASS: `make openapi && git diff --exit-code -- frontend/src/api/openapi.json frontend/src/api/schema.ts`
- PASS: `make validate-changed`; note: selected no files, so it is not treated
  as sufficient changed-surface evidence for this PR.
- PASS: `pre-commit run --all-files`
- PASS: commit/push hooks, including changed-file backend tests,
  changed-file mypy, full-repo Bandit, pip-audit, and Docker build test.

## Machine-Heavy Verification Deferral

Operator override applies: no deliberate full local `make verify` for this PR.
The accidental earlier `make verify` invocation is discarded and is not PR-5
gate evidence; it failed on inherited `legacy_app.py` lint unrelated to this
validation plan. Current-head CI parity, post-open review disposition, strict
merge-readiness, and the mandatory wait-window still apply before any merge
claim.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/artifacts/orchestration/experiments/pr5_plan_export_registration_oracle_packet.json`
- Result artifact:
  `artifacts/orchestration/experiments/results/exp-7a6bc3ab3b0e.json`
- Status: accepted.
- Oracles passed:
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_plan_export_additional.py tests/security/test_api_auth_tier_contract_pack.py`
  - `pytest -q tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py`
- Attribution: no co-author trailer. The oracle was validation evidence and did
  not materially shape code, tests, mapping, or commit decisions.

## Premortem Findings

Disposition: FIXED

Finding: `PR5-P1-001` reported that the reviewed diff was only in the working
tree and would be omitted if the PR opened before commit/push.

Commit: a90daa4ad

Evidence: implementation commit `a90daa4ad` contains the eight tracked PR files,
and `git push -u origin codex/shrink-legacy-export-router-registration-seam`
created the remote branch.

Disposition: NOT-A-BUG

Finding: `PR5-P2-001` noted that the authz contract pack uses
`ApiExposure.PUBLIC_OPENAPI` for `/api/v1/export/sign` because that registry
tracks source `APIRoute.include_in_schema`, while final `app.openapi()` hides the
path.

Evidence: `tests/test_plan_export_additional.py` asserts both source
`include_in_schema` preservation and final public OpenAPI hiding for all
canonical plan/export routes. This is intended route metadata behavior, not
final schema exposure.

Disposition: FIXED

Finding: `PR5-P2-002` requested deterministic export rate-limit behavior checks.

Evidence: `. .venv/bin/activate && pytest -q tests/test_rate_limit_llm_and_exports_api.py::test_plan_week_export_csv_rate_limited_200_then_429 tests/test_rate_limit_llm_and_exports_api.py::test_export_sign_rate_limited_200_then_429`
passed after the premortem.

## Post-Open Review Evidence

Pending. This artifact was created immediately after PR open and before
post-open bot/human review. Mandatory post-open role review and Codex Security
scan/finding discovery remain required before merge-readiness.

## Discussion Thread Pass

- [x] Initial discussion-thread pass completed
- [x] Fixed in commit mapping artifact created

No GitHub review threads existed at artifact creation time. Review threads must
not be resolved without disposition evidence and this pass must be repeated
after any new bot or human review activity.

## Fixed in Commit Mapping

No GitHub review-thread mappings yet.

## Deferred / Follow-Ups

No product follow-up. Full local `make verify` remains deferred by operator
override as documented above.

## Merge Readiness

Status: NOT READY while post-open role review, Codex Security scan/finding
discovery, current-head CI, bot/human review disposition, strict
merge-readiness, and the mandatory wait-window remain pending.

Required before merge:

- Fresh current-head PR CI parity.
- No unresolved actionable human or bot review comments.
- Strict merge-readiness with auth passes.
- Mandatory wait-window after latest review/bot activity.
