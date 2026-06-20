# PR 1999 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1999

Branch: `codex/extract-route-family-bootstrap-guard`

## Summary

This PR extracts a shared static route-family bootstrap guard and migrates only
plan/shoplist export registration to it. Runtime route behavior, API-key
dependency, plan signed-token dependency, export 429 metadata, source route
OpenAPI visibility, final public OpenAPI hiding, reload idempotency, and
duplicate/foreign handler rejection are preserved.

## Scope

- Add `app/bootstrap/route_family.py` with `RouteMemberContract`,
  `ensure_route_family_registered(...)`, module+qualname callable matching, and
  recursive dependency traversal.
- Migrate only `app/main.py` plan export and shoplist export bootstrap wrappers
  to the shared static helper.
- Tighten plan source-router validation so unexpected source `APIRoute`s fail
  closed like shoplist.
- Keep dynamic legacy export aliases on their existing dedicated helper.
- Update `app/AGENTS.md` and `docs/architecture/backend_routing_map.md` for the
  canonical static-helper pattern.

## Out Of Scope

No `legacy_app.py` change, dynamic legacy alias migration, route migration, DB
migration, frontend/iOS change, generated OpenAPI/client diff, restaurant
moderation runtime work, or broad legacy refactor.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/0c79d0ade1a0.json`
- Runtime dispatch manifest:
  `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/0c79d0ade1a0.json --pretty`
- Pre-open role order executed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> qa-engineer-agent -> security-auditor -> bug-hunter`
- Starter: `check_preflight.py`, `check_agent_consistency.py`, and
  `task_bootstrap.py`; packet creation was treated as provenance only, not role
  execution.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `. .venv/bin/activate && python -m pytest -q tests/test_route_family_bootstrap.py tests/test_main_paywall_bootstrap.py tests/test_plan_export_additional.py tests/test_shoplist_export.py tests/test_export_signed.py tests/test_rate_limit_llm_and_exports_api.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py`
- PASS: `. .venv/bin/activate && python -m mypy app/bootstrap/route_family.py app/main.py`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `make openapi-check`
- PASS: `git diff --check`
- PASS: `pre-commit run --all-files`
- PASS after commit: `make validate-changed` selected
  `tests/test_main_paywall_bootstrap.py`,
  `tests/test_route_family_bootstrap.py`, and `tests/test_shoplist_export.py`
- PASS on push hook: changed-file mypy, pre-push backend pytest, full-repo
  Bandit, and Docker build test
- Not run: full `make verify`; this PR is not claiming merge readiness from
  local gates alone.

## Premortem Findings

Disposition: FIXED

Finding: static helper could accidentally absorb dynamic legacy export aliases.

Commit: `df9f7b0a0`

Evidence: `app/main.py` keeps `_include_legacy_export_alias_router_if_needed`
on the existing helper path; `app/AGENTS.md` documents that request-time rebound
aliases must not use the static helper; `docs/architecture/backend_routing_map.md`
records hidden legacy export aliases as separate compatibility routing.

Disposition: FIXED

Finding: auth, signed-token, 429 metadata, or OpenAPI hiding could drift during
deduplication.

Commit: `df9f7b0a0`

Evidence: `app/bootstrap/route_family.py` validates source route visibility and
429 metadata plus existing-route dependencies/status/visibility; `app/main.py`
declares plan CSV/PDF `_require_valid_token` only for those members; focused
pytest and `make openapi-check` passed.

Disposition: FIXED

Finding: pre-commit `make validate-changed` could false-green before first
commit because it selected no changed Python files.

Commit: `df9f7b0a0`

Evidence: the first `make validate-changed` run was treated as advisory only;
after commit, `make validate-changed` selected the changed route bootstrap tests
and passed.

## Experiment Runner Evidence

- Initial rejected artifact:
  `artifacts/orchestration/experiments/results/pr7-route-family-bootstrap-oracle-result.json`
  was rejected before oracle execution because the packet context omitted two
  changed paths. It is not used as readiness evidence.
- Accepted artifact:
  `artifacts/orchestration/experiments/results/pr7-route-family-bootstrap-oracle-result-v3.json`
- Status: accepted.
- Runner mode: `oracle_only_governance_reviewer`.
- Oracles passed:
  - `python -m pytest -q tests/test_route_family_bootstrap.py tests/test_main_paywall_bootstrap.py tests/test_plan_export_additional.py tests/test_shoplist_export.py tests/test_export_signed.py tests/test_rate_limit_llm_and_exports_api.py tests/test_legacy_growth_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/test_pro_vip_route_dependency_guard.py tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py`
  - `python -m mypy app/bootstrap/route_family.py app/main.py`
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `make openapi-check`
- Result: 4/4 oracle commands passed; `mutated_paths=[]`;
  `shared_tree_untouched=true`.
- Attribution: co-author trailer required and present on implementation commit
  `df9f7b0a0`.

## Post-Open Review Evidence

Pending. Mandatory post-open reviewer lane, Codex Security diff scan / finding
discovery, `pulseplate-pr-review`, and external bot review disposition must run
before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No review-thread or bot actionables were available when this artifact was first
created immediately after PR open. New post-open findings must be added here
with FIXED / NOT-A-BUG / DEFERRED disposition evidence before thread
resolution or merge-readiness claims.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

- [ ] Required current-head CI complete and passing
- [ ] Post-open role lane complete: `qa-engineer-agent -> bug-hunter -> security-auditor`
- [ ] Codex Security diff scan / finding discovery complete
- [ ] `pulseplate-pr-review` complete
- [ ] CodeRabbit/Sourcery/Cubic actionables dispositioned
- [ ] Strict merge readiness wrapper passes after latest review activity
