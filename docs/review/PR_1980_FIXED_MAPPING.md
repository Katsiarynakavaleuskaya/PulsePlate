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

- Branch: `codex/extract-admin-debug-operational-routes-from-legacy`
- PR open base: `98a39596f583cbf8924d5d9749efda5c993ad8eb`
- Implementation commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
- Bootstrap packet: `artifacts/orchestration/task_packets/ee38f1c196fd.json`
- Premortem artifact:
  `artifacts/orchestration/premortem/pr2-admin-debug-operational-routes-premortem.md`
- Experiment Runner packet:
  `artifacts/orchestration/experiments/exp-71172ed5d6c9.json`
- Experiment Runner result:
  `artifacts/orchestration/experiments/results/exp-71172ed5d6c9.json`
- Machine-heavy exception: full local `make verify` intentionally deferred
  under the operator-approved narrow backend extraction scope. Focused local
  gates and current-head CI remain required.

## Discussion Thread Pass

- [x] Pre-open bootstrap role order completed:
  `agent-coordinator -> backend-engineer -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter`.
- [x] `agent-coordinator`: confirmed seven-route extraction scope, touched
  surfaces, role order, and DoD.
- [x] `backend-engineer`: required tracking new router/service modules and
  reviewing API-key response parity. New files are included in commit
  `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`; security pass accepted auth body
  behavior.
- [x] `architecture-specialist`: accepted canonical `app.main:app` route
  ownership and required guard threshold correction. Guard threshold fixed in
  commit `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`.
- [x] `security-auditor`: accepted API-key fail-closed behavior, debug gating,
  and hidden live OpenAPI surface; required `api_key` guard baseline `15`.
- [x] `qa-engineer-agent`: required deterministic valid-key cleanup coverage
  and static OpenAPI disposition. Cleanup route tests and NOT-A-BUG static
  OpenAPI disposition are recorded below.
- [x] `bug-hunter`: found no concrete blocking runtime regression after fixes.
- [ ] Post-open role loop pending:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan / finding discovery pending.
- [ ] `pulseplate-pr-review` pending.
- [ ] GitHub review comments and bot actionables pending current-head review.

### Fixed in Commit Mapping

- Pre-open backend finding: new canonical modules were untracked.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `app/routers/admin_operations.py` and
`app/services/admin_operations.py` are created in the implementation commit.

- Pre-open architecture/security finding: legacy sensitive API-key app-surface
limit was over-tightened to `14`.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `scripts/ci/check_legacy_growth_guard.py` uses `api_key: 15`; the
guard CLI passed after the fix.

- Pre-open QA finding: `/admin/logs/cleanup` needed deterministic valid-key
execution coverage.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `tests/test_admin_endpoints_97.py` covers valid-key cleanup success
and invalid `data_class` behavior through the canonical route/service path.

- Pre-open architecture finding: direct raw `legacy_app.app` no longer owns the
seven moved runtime routes.
Disposition: NOT-A-BUG
Evidence: repo runtime entrypoints use canonical `app.main:app`; tests and
OpenAPI guards validate canonical runtime ownership. This PR intentionally moves
route ownership out of `legacy_app.py` and leaves direct-call shims for imported
functions.
Reason: direct raw legacy ASGI runtime compatibility is not the canonical
runtime contract for this extraction lane.

- Pre-open QA finding: `app/static/openapi.json` still lists stale admin/debug
paths.
Disposition: NOT-A-BUG
Evidence: live `app.main.app.openapi()` and `frontend/src/api/openapi.json`
contain no extracted admin/debug paths; `tests/test_openapi_namespace_guards.py`
asserts live OpenAPI absence.
Reason: the PR plan explicitly treats live OpenAPI and generated frontend
OpenAPI as contract surfaces; static `app/static/openapi.json` cleanup is out of
scope for this lane.

## Premortem Finding Closure

- F1: Admin/debug routes accidentally exposed in public OpenAPI.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `app/routers/admin_operations.py` marks routes hidden;
`app/main.py` rejects visible family registration; focused OpenAPI tests pass.

- F2: Auth drift weakens protected admin routes.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: protected route tests assert 403 for missing/invalid `X-API-Key` and
valid-key behavior through scheduler/retention stubs.

- F3: Scheduler monkeypatch seams break.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `app/services/admin_operations.py` resolves legacy/app scheduler
seams before default fallback; focused admin tests pass with patched scheduler.

- F4: Legacy guard shrink over-tightens the sensitive baseline.
Disposition: FIXED
Commit: `71980c45ae3ef83fa6cfbf0d9fa5e7d2a3e46c7b`
Evidence: `scripts/ci/check_legacy_growth_guard.py` uses `api_key: 15`; the
guard CLI passed.

- F5: Stale static OpenAPI mistaken for contract truth.
Disposition: NOT-A-BUG
Evidence: live OpenAPI and generated frontend OpenAPI remain free of the moved
admin/debug paths; static cleanup is out of scope.
Reason: this lane's contract surfaces are live `app.main.app.openapi()` and
generated frontend OpenAPI.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/exp-71172ed5d6c9.json`
- Mode: `oracle_only_governance_reviewer`
- Status: accepted
- Contribution: `commit_decision`
- Co-author required: true; implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
- Accepted oracle commands:
  - `python3 scripts/ci/check_legacy_growth_guard.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`

## Validation Evidence

- PASS: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_admin_endpoints_97.py tests/test_app_endpoints_combined.py::TestDebugEndpoint tests/test_openapi_namespace_guards.py`
  (`115 passed`)
- PASS: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during push hooks: mypy, pip-audit, backend pre-push pytest,
  full-repo Bandit, and Docker build test.
- Deferred: full local `make verify` under the operator-approved
  machine-heavy exception; current-head CI plus strict merge wrapper are the
  heavy signal.

## Merge Readiness

Not merge-ready yet. Required before merge:

- [ ] Current-head required CI green with no pending required jobs.
- [ ] Post-open role loop completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [ ] Codex Security diff scan / finding discovery completed.
- [ ] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, Cubic, and human/bot comments have no unresolved
  actionable items, or every item is dispositioned above.
- [ ] `check_merge_ready.py --require-auth` passes after latest review activity.
- [ ] Mandatory wait window completes after latest bot/review activity.
