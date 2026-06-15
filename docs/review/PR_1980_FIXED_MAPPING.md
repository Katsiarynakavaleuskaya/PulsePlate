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
- PR body mirror note: the Experiment Runner artifact line must stay
  parser-safe as `Artifact: artifacts/orchestration/experiments/results/exp-71172ed5d6c9.json`
  with no trailing punctuation after the artifact path.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Post-open `qa-engineer-agent` pass completed and produced actionable
  CodeRabbit/parser findings now mapped below.
- Post-open `bug-hunter` pass completed with PASS: no actionable P0/P1 bug
  remains in the PR diff, and the three CodeRabbit fixes are addressed.
- Post-open `security-auditor` pass completed with PASS: no actionable
  security/auth/secret/OpenAPI exposure issue remains in the PR diff.
- Codex Security diff scan / finding discovery completed with no reportable
  findings.
- `pulseplate-pr-review` completed with one advisory large-diff planning note,
  dispositioned as NOT-A-BUG below.
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

## Post-Open Role Review Evidence

- `qa-engineer-agent`: HOLD until CodeRabbit/parser fixes were applied.
  Disposition: FIXED by commit
  `4a650a5f2457d4a6292b5082c4dfaf72b143832a` for scheduler alias seam,
  JSON Content-Type assertions, and deterministic `/debug_env` happy path;
  fixed mapping/parser shape was corrected in commit
  `fbabe5ef8557070619d6a80270cfe8f66df433cb`.
- `bug-hunter`: PASS. Evidence: confirmed no actionable P0/P1 bug remains,
  all seven admin/debug runtime routes are canonical, hidden from OpenAPI, and
  the three CodeRabbit fixes are addressed. Focused probe and pytest passed.
- `security-auditor`: PASS. Evidence: confirmed six protected operational
  routes use API-key dependency, `/debug_env` is env-gated with limited payload,
  live OpenAPI has no leaks, and scheduler seam remains server-internal.

## Codex Security Diff Scan / Finding Discovery

- Skill: `codex-security:security-diff-scan`.
- Scope: PR diff `origin/main...HEAD` for source-like changed files:
  `app/main.py`, `app/routers/admin_operations.py`,
  `app/services/admin_operations.py`, and `legacy_app.py`.
- Scan directory:
  `/tmp/codex-security-scans/extract-admin-debug-operational-routes-from-legacy/pr-1980-admin-debug-operational-routes-fbabe5ef8`.
- Markdown report:
  `/tmp/codex-security-scans/extract-admin-debug-operational-routes-from-legacy/pr-1980-admin-debug-operational-routes-fbabe5ef8/report.md`.
- HTML report:
  `/tmp/codex-security-scans/extract-admin-debug-operational-routes-from-legacy/pr-1980-admin-debug-operational-routes-fbabe5ef8/report.html`.
- Work ledger:
  `/tmp/codex-security-scans/extract-admin-debug-operational-routes-from-legacy/pr-1980-admin-debug-operational-routes-fbabe5ef8/artifacts/02_discovery/work_ledger.jsonl`.
- Result: PASS, no reportable findings. Every `deep_review_input.csv` row has
  a completion receipt, discovery emitted no candidates, and the final markdown
  report passed `validate_report_format.py`.

## PulsePlate PR Review

- Skill: `pulseplate-pr-review`.
- Context: `/tmp/pulseplate_pr_1980_review_context.json`.
- Markdown report: `/tmp/pulseplate_pr_1980_review_report.md`.
- JSON report: `/tmp/pulseplate_pr_1980_review_report.json`.
- Finding: one advisory `note` for large-diff review planning because the diff
  exceeds the 800 changed-line threshold.
- Disposition: NOT-A-BUG.
- Evidence: this PR is intentionally the bounded seven-route admin/debug
  operational extraction slice. The line count is dominated by targeted route
  extraction, bootstrap fail-closed tests, legacy guard shrink, focused endpoint
  tests, and this canonical review artifact. Focused local gates,
  post-open role reviews, Codex Security, and `make validate-changed` passed.

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`.
- PASS: `.venv/bin/python -m pytest -q tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_admin_endpoints_97.py tests/test_app_endpoints_combined.py::TestDebugEndpoint tests/test_openapi_namespace_guards.py`
  (`115 passed`) before post-open review fixes.
- PASS: `.venv/bin/python -m pytest -q tests/test_admin_endpoints_97.py::TestAdminEndpoints tests/test_app_endpoints_combined.py::TestDebugEndpoint tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_openapi_namespace_guards.py`
  after CodeRabbit/QA fixes.
- PASS: `.venv/bin/python scripts/ci/check_legacy_growth_guard.py`.
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`.
- PASS: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1980`.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: reproduced CI `diff-coverage` locally with coverage over
  `tests/test_main_paywall_bootstrap.py`, `tests/test_app_endpoints_combined.py`,
  and `tests/test_legacy_app_diff_coverage.py`; `diff-cover coverage.xml
  --compare-branch origin/main --fail-under 97 ...` reported 100% coverage for
  `app/main.py`, `app/routers/admin_operations.py`,
  `app/services/admin_operations.py`, and `legacy_app.py`.
- PASS during push hooks: mypy, pip-audit, backend pre-push pytest,
  full-repo Bandit, and Docker build test.
- Deferred: full local `make verify` under the operator-approved
  machine-heavy exception; current-head CI plus strict merge wrapper are the
  heavy signal.

## Merge Readiness

Not merge-ready yet. Required before merge:

- [ ] Current-head required CI green with no pending required jobs.
- [x] Post-open role loop completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [ ] CodeRabbit, Sourcery, Cubic, and human/bot comments have no unresolved
  actionable items, or every item is dispositioned above.
- [ ] `check_merge_ready.py --require-auth` passes after latest review activity.
- [ ] Mandatory wait window completes after latest bot/review activity.
