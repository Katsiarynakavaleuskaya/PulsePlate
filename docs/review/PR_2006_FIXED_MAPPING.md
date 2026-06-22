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
- Added CI-smoke coverage for the shared planning-target service and
  profile-derived weekly router branches.
- Fixed `legacy_app.py` import hygiene surfaced by local `make verify` lint.

## Out Of Scope

No FoodDB/Postgres/OFF/catalog cutover, DB migration, generated-client work,
route registration change, frontend/iOS work, AI/compliance change, or broad
legacy rewrite.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open Sourcery and CodeRabbit findings are mapped below.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#discussion_r3452568392 -> 8d972fbf9
Disposition: FIXED
Commit: 8d972fbf9
Evidence: `app/services/nutrition_targets.py` widens `PlanningTargetsPayload.macros` and `PlanningTargetsPayload.micro` through `PlanningNumeric = int | float`; targeted mypy and service/diff coverage tests passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#discussion_r3452622130 -> 366d6a18d
Disposition: FIXED
Commit: 366d6a18d
Evidence: `tests/test_pro_premium_contract_parity.py` asserts JSON `content-type` before parsing both explicit-target and profile-derived weekly parity responses; `pytest -q tests/test_pro_premium_contract_parity.py` passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#pullrequestreview-4544483234 -> 8d972fbf9
Disposition: FIXED
Commit: 8d972fbf9
Evidence: `app/services/nutrition_targets.py` widens macro/micro value types through `PlanningNumeric = int | float`; the `activity_week` return-payload key remains required because `estimate_targets_from_profile(...)` always returns the exact weekly planning payload shape, while `is_complete_planning_targets(...)` intentionally preserves existing compatibility for explicit targets that omit `activity_week`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#pullrequestreview-4544546239 -> 3f5504350
Disposition: FIXED
Commit: 3f5504350
Evidence: `tests/test_diff_coverage_pr339.py` and `tests/test_final_coverage_96.py` add explicit return/fixture type annotations; `tests/test_premium_week_endpoint_simple_96.py` no longer claims to cover an unpatched unable-to-derive branch and instead preserves current legacy alias behavior; `tests/disabled_hypothesis/test_premium_week_hypothesis_simple.py` is reverted out of the net PR diff. `pre-commit run --all-files` passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#pullrequestreview-4544563348 -> 3f5504350
Disposition: FIXED
Commit: 3f5504350
Evidence: `docs/review/PR_2006_FIXED_MAPPING.md` now uses unchecked checklist entries under `## Merge Readiness`; `pre-commit run --all-files` passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#discussion_r3452821243 -> 8362e21fe
Disposition: FIXED
Commit: 8362e21fe
Evidence: `tests/test_premium_week_endpoint_simple_96.py` asserts JSON `content-type` before parsing the legacy premium weekly alias response; `pytest -q tests/test_premium_week_endpoint_simple_96.py` passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2006#pullrequestreview-4544801394 -> 8362e21fe
Disposition: FIXED
Commit: 8362e21fe
Evidence: `tests/test_premium_week_endpoint_simple_96.py` asserts JSON `content-type` before parsing the legacy premium weekly alias response; `pytest -q tests/test_premium_week_endpoint_simple_96.py` passed.

## PulsePlate PR Review Disposition

Finding: `large-diff-risk` advisory from `pulseplate-pr-review`.

Disposition: NOT-A-BUG
Evidence: `make validate-changed` selected the changed Python test surface and
passed; focused weekly/pro/premium pytest bundles, targeted mypy,
`make openapi-check`, `pre-commit run --all-files`, and `git diff --check`
passed.
Reason: The line-count threshold is crossed by focused test updates and the
canonical review artifact, while production code scope remains limited to the
shared nutrition target service, two weekly routers, and a `legacy_app.py`
import-compat hygiene fix. No route/auth/tier, OpenAPI/client, migration,
FoodDB cutover, frontend/iOS, or broad legacy rewrite scope is included.

## Implementation Commits

- `6eec0ea99` - centralizes profile-derived weekly planning targets, updates
  PRO/premium weekly routers and tests, preserves deprecated compatibility, and
  fixes the `legacy_app.py` flake8 import-hygiene gate.
- `1118b0583` - adds PR #2006 fixed-mapping governance artifact.
- `923a8fb5d` - aligns fixed-mapping artifact syntax with Phase2 gates.
- `8d972fbf9` - widens planning target numeric payload types for Sourcery
  feedback.
- `cf0a52117` - maps the fixed Sourcery typing thread in the PR #2006 mapping
  artifact.
- `366d6a18d` - asserts weekly parity response JSON content types for CodeRabbit
  feedback.
- `715735355` - maps the fixed CodeRabbit content-type thread in the PR #2006
  mapping artifact.
- `3f5504350` - addresses CodeRabbit outside-diff test/mapping findings and
  removes the disabled hypothesis file from the net PR diff.
- `42a1b4140` - maps PR #2006 review-level bot comments.
- `8362e21fe` - asserts JSON content type before parsing the legacy premium
  weekly alias response.
- `f1178c2e5` - maps the fixed CodeRabbit legacy alias finding in the PR #2006
  mapping artifact.
- `e6212bd4f` - removes async test markers from the changed diff-coverage test
  surface so CI pre-commit backend-tests do not require the optional
  `pytest-asyncio` plugin in the lint environment.
- `9e59c3791` - records the CI lint fix in the PR #2006 mapping artifact.
- `6738ed9b8` - documents the async marker/pre-commit environment rule in
  root `AGENTS.md`, `tests/AGENTS.md`, and `docs/ENGINEERING_LESSONS.md`.
- `04c500acc` - covers profile-derived planning-target service/router branches
  inside the CI smoke `tests/edges` coverage set after current-head
  `diff-coverage` reported missing lines in `app/services/nutrition_targets.py`,
  `app/routers/pro.py`, and `app/routers/premium_week.py`.

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
- `make validate-changed`
- `make lint`
- `pre-commit run --all-files`
- `git diff --check`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")" BRANCH_DIFF_MODE=1 bash scripts/run-backend-tests-pre-commit.sh`
- Pre-push hooks: changed-files mypy, backend tests, full-repo Bandit, Docker
  build test.

Current-head CI lint failure on `f1178c2e5` was fixed in `e6212bd4f` by
removing `pytest.mark.asyncio`/`async def` from the changed diff-coverage tests
selected by the pre-commit backend-tests hook. The selected bundle now has no
async test markers and passes without relying on `pytest-asyncio`.

Operator-requested process memory from the same incident is captured in
`6738ed9b8`: pre-commit-selected tests must not rely on async pytest plugin
state unless that hook environment is explicitly proven to load it.

Current-head CI `diff-coverage` failure on `31134b866` was fixed in
`04c500acc` by adding synchronous `tests/edges/test_premium_week_edges.py`
coverage for `is_complete_planning_targets(...)`,
`estimate_targets_from_profile(...)`, and the profile-derived PRO/premium weekly
router branches. Local CI-smoke coverage evidence:
`PYTHONPATH="$PWD:$PWD/tests" VIP_MODULE_ENABLED=true APP_ENV=test ENVIRONMENT=test FEATURE_PREMIUM_NUTRITION=true API_KEY=test_key PYTHONUNBUFFERED=1 PYTHONFAULTHANDLER=1 PYTHONMALLOC=malloc python -m coverage run -m pytest -q tests/edges --maxfail=3 && python -m coverage xml && diff-cover coverage.xml --compare-branch origin/main --fail-under 97 ...`
reported `app/routers/premium_week.py (100%)`, `app/routers/pro.py (100%)`,
`app/services/nutrition_targets.py (100%)`, `legacy_app.py (100%)`, total
`44` diff lines, missing `0`, coverage `100%`.

Full `make verify` was attempted once. The first run exposed the
`legacy_app.py` lint issue fixed in `6eec0ea99`. The rerun passed verify-env,
lint, mypy, and smoke tests, then entered the full pytest/diff-cov phase and was
interrupted per operator machine-heavy policy. It is not claimed as a completed
readiness signal.

## Merge Readiness

Not merge-ready yet.

Required before merge:
- [ ] Current-head CI passes.
- [ ] Bot/human review comments dispositioned.
- [ ] Post-open role passes completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan/finding discovery run if available.
- [ ] `pulseplate-pr-review` passed.
- [ ] Strict merge-readiness checks passed.
