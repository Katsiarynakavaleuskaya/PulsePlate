# PR #2006 Fixed in Commit Mapping

## Summary

PR: `refactor(nutrition): centralize profile-derived planning targets`

Branch: `codex/centralize-profile-derived-planning-targets`

Implementation commit: `6eec0ea99`

This PR centralizes weekly-plan profile-derived nutrition target derivation and
target-shape completeness checks in `app/services/nutrition_targets.py` while
preserving canonical PRO and deprecated premium weekly endpoint behavior.

## Lane Start Provenance

- Base branch: `main`
- Start head: `2fd053128c7e5ac3d45873007867c8f4b7500f04`
- Packet: `artifacts/orchestration/task_packets/b7f6dbc6858b.json`
- Required pre-implementation role order completed:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> backend-engineer -> architecture-specialist`

## Scope

- Added `app/services/nutrition_targets.py`.
- Updated `app/routers/pro.py` and `app/routers/premium_week.py` to use the
  shared service for weekly planning target derivation/completeness.
- Updated tests to patch and validate the new service seam.
- Added profile-derived PRO/premium weekly parity coverage.
- Fixed `legacy_app.py` import hygiene surfaced by local `make verify` lint.

## Out Of Scope

No FoodDB/Postgres/OFF/catalog cutover, DB migration, generated-client work,
route registration change, frontend/iOS work, AI/compliance change, or broad
legacy rewrite.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

No review threads existed at PR open. One post-open Sourcery thread is mapped
below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#discussion_r3452568392 -> 8d972fbf9
Disposition: FIXED
Commit: 8d972fbf9
Evidence: `app/services/nutrition_targets.py` widens `PlanningTargetsPayload.macros` and `PlanningTargetsPayload.micro` through `PlanningNumeric = int | float`; targeted mypy and service/diff coverage tests passed.

## Implementation Commits

- `6eec0ea99` - centralizes profile-derived weekly planning targets, updates
  PRO/premium weekly routers and tests, preserves deprecated compatibility, and
  fixes the `legacy_app.py` flake8 import-hygiene gate.
- `1118b0583` - adds PR #2006 fixed-mapping governance artifact.
- `923a8fb5d` - aligns fixed-mapping artifact syntax with Phase2 gates.
- `8d972fbf9` - widens planning target numeric payload types for Sourcery
  feedback.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/centralize-profile-derived-planning-targets-premortem.md`
- Decision: `proceed with changes`
- Findings closed before PR open:
  - Stale router-local test patch points: fixed by moving active patches to
    `app.services.nutrition_targets`.
  - `make validate-changed` false-green risk: mitigated with explicit focused
    pytest/mypy/pre-commit evidence.
  - Existing `legacy_app.py` lint failure: fixed in `6eec0ea99`.
  - Experiment Runner source diff visibility: fixed by staging the coherent diff
    before oracle-only evidence.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/exp-ed836b5c000a.json`
- Artifact: `artifacts/orchestration/experiments/results/exp-ed836b5c000a.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer included in `6eec0ea99`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Validation

Passed locally:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `. .venv/bin/activate && pytest -q tests/test_nutrition_targets_service.py tests/test_diff_coverage_pr339.py tests/test_pro_router.py tests/test_premium_week_router.py tests/test_premium_week_router_isolated.py tests/edges/test_premium_week_edges.py tests/test_pro_premium_contract_parity.py tests/test_weekly_plan_endpoints_error_envelope_diff_coverage.py tests/test_weekly_plan_postprocess_error_envelope_diff_coverage.py`
- `. .venv/bin/activate && pytest -q tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/test_paid_route_guards.py`
- `. .venv/bin/activate && mypy app/services/nutrition_targets.py app/routers/pro.py app/routers/premium_week.py`
- `make openapi-check`
- `make lint`
- `pre-commit run --all-files`
- `git diff --check`
- Pre-push hooks: changed-files mypy, backend tests, full-repo Bandit, Docker
  build test.

`make validate-changed` passed but selected no Python files in the local branch
state, so it is explicitly not treated as sufficient evidence for this PR.

Full `make verify` was attempted once. The first run exposed the
`legacy_app.py` lint issue fixed in `6eec0ea99`. The rerun passed verify-env,
lint, mypy, and smoke tests, then entered the full pytest/diff-cov phase and was
interrupted per operator machine-heavy policy. It is not claimed as a completed
readiness signal.

## Merge Readiness

Not merge-ready yet.

Required before merge:
- Current-head CI must pass.
- Bot/human review comments must be dispositioned.
- Post-open role passes must run:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- Codex Security diff scan/finding discovery must run if available.
- `pulseplate-pr-review` must run.
- Strict merge-readiness checks must pass.
