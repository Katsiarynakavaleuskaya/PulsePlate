# PR 1980 Fixed in Commit Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980>

## Summary

This PR extracts seven admin/debug operational routes from `legacy_app.py` into
canonical hidden FastAPI router/service ownership:

- `GET /debug_env`
- `GET /api/v1/admin/status`
- `POST /admin/logs/cleanup`
- `GET /api/v1/admin/db-status`
- `POST /api/v1/admin/force-update`
- `GET /api/v1/admin/check-updates`
- `POST /api/v1/admin/rollback`

Runtime behavior, API-key fail-closed behavior, debug gating, scheduler seams,
and public OpenAPI invisibility are preserved. BMI/planning, exports, FoodDB,
insight, premium, billing, tiering, scheduler migration, auth policy redesign,
and client changes are out of scope.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/ee38f1c196fd.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Branch: `codex/extract-admin-debug-operational-routes-from-legacy`
- PR open base: `98a39596f583cbf8924d5d9749efda5c993ad8eb`
- Task class: `Backend API`
- PR phase: `pre_open`
- Pre-open role order completed:
  `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- Machine-heavy exception: full local `make verify` intentionally deferred
  under the operator-approved narrow backend extraction scope. Focused local
  gates and current-head CI remain required.

## Premortem Finding Closure

- Artifact:
  `artifacts/orchestration/premortem/pr2-admin-debug-operational-routes-premortem.md`.
- F1 admin/debug routes accidentally exposed in public OpenAPI: FIXED by hidden
  router declarations, bootstrap visibility rejection, and OpenAPI tests.
- F2 auth drift weakens protected admin routes: FIXED by preserving
  `Depends(require_app_api_key)` and valid/missing/invalid key tests.
- F3 scheduler monkeypatch seams break: FIXED by service-level scheduler seam
  resolution and admin endpoint tests.
- F4 legacy guard shrink over-tightens sensitive baseline: FIXED by retaining
  the correct `api_key: 15` legacy sensitive count.
- F5 stale static OpenAPI mistaken for contract truth: NOT-A-BUG. Live
  `app.main.app.openapi()` and generated frontend OpenAPI are this PR's
  contract surfaces.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-71172ed5d6c9.json`
- Packet: `artifacts/orchestration/experiments/exp-71172ed5d6c9.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `commit_decision`
- Co-author required: true; implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Accepted oracle commands:
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Post-open `qa-engineer-agent` pass completed and produced actionable
  CodeRabbit/parser findings now mapped below.
- Remaining post-open role loop is still pending:
  `bug-hunter -> security-auditor`.
- Codex Security diff scan / finding discovery and `pulseplate-pr-review` are
  still pending.
- GitHub review threads must not be resolved until the mapped fix commit is
  pushed and the strict disposition guard is rerun.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 4a650a5f2457d4a6292b5082c4dfaf72b143832a
Evidence: app/services/admin_operations.py preserves app_module scheduler alias selection and tests/test_admin_endpoints_97.py covers it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980#discussion_r3412526359 -> 4a650a5f2457d4a6292b5082c4dfaf72b143832a

Disposition: FIXED
Commit: 4a650a5f2457d4a6292b5082c4dfaf72b143832a
Evidence: tests/test_admin_endpoints_97.py asserts JSON Content-Type before new admin route json parsing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980#discussion_r3412526368 -> 4a650a5f2457d4a6292b5082c4dfaf72b143832a

Disposition: FIXED
Commit: 4a650a5f2457d4a6292b5082c4dfaf72b143832a
Evidence: tests/test_app_endpoints_combined.py explicitly enables ENABLE_DEBUG_ENDPOINT for the debug happy path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980#discussion_r3412526373 -> 4a650a5f2457d4a6292b5082c4dfaf72b143832a

Disposition: NOT-A-BUG
Evidence: CodeRabbit issue comment is walkthrough and pre-merge checklist metadata; actionable file comments are mapped above.
Reason: No additional code action beyond the mapped review comments.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980#issuecomment-4706585012

Disposition: NOT-A-BUG
Evidence: Codex connector issue comment reports code-review usage limit only.
Reason: Not an actionable code review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1980#issuecomment-4706584230

## Pre-Open Role Finding Closure

- `agent-coordinator`: confirmed the seven-route extraction scope, touched
  surfaces, role order, and DoD.
- `backend-engineer`: required tracking new router/service modules and reviewing
  API-key response parity. New modules are included in commit
  `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`; security pass accepted auth
  body behavior.
- `architecture-specialist`: accepted canonical `app.main:app` route ownership
  and required guard threshold correction. Guard threshold is fixed in commit
  `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`.
- `security-auditor`: accepted API-key fail-closed behavior, debug gating, and
  hidden live OpenAPI surface; required `api_key` guard baseline `15`.
- `qa-engineer-agent`: required deterministic valid-key cleanup coverage and
  static OpenAPI disposition. Both are captured in implementation tests and
  premortem closure above.
- `bug-hunter`: found no concrete blocking runtime regression after fixes.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_admin_endpoints_97.py tests/test_app_endpoints_combined.py::TestDebugEndpoint tests/test_openapi_namespace_guards.py`
  (`115 passed`) before post-open review fixes.
- PASS: `.venv/bin/python -m pytest -q tests/test_admin_endpoints_97.py::TestAdminEndpoints tests/test_app_endpoints_combined.py::TestDebugEndpoint tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_openapi_namespace_guards.py`
  after CodeRabbit/QA fixes.
- PASS: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS during push hooks: mypy, pip-audit, backend pre-push pytest,
  full-repo Bandit, and Docker build test.
- Deferred: full local `make verify` under the operator-approved
  machine-heavy exception; current-head CI plus strict merge wrapper are the
  heavy signal.

## Merge Readiness

Not merge-ready yet. Required before merge:

- [ ] Current-head required CI green with no pending required jobs.
- [ ] Remaining post-open role loop completed:
  `bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, Cubic, and human/bot comments have no unresolved
  actionable items, or every item is dispositioned above.
- [ ] `check_merge_ready.py --require-auth` passes after latest review activity.
- [ ] Mandatory wait window completes after latest bot/review activity.
