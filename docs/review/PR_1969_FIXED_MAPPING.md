# PR 1969 Fixed in Commit Mapping

## Summary

- Scope: extract operational health/readiness route ownership from
  `legacy_app.py` into canonical `app.routers.health` plus `app/main.py`
  bootstrap.
- Branch: `codex/extract-health-readiness-routes-from-legacy`.
- Implementation commit:
  `0f69ec1855355de99f0c1cc6fd628921e49f406f`.
- Runtime paths and envelopes: unchanged for `/health`, `/api/v1/health`,
  `/health/db`, and `/ready`.
- OpenAPI/client artifacts: unchanged; the extracted routes remain hidden from
  public OpenAPI.
- Full local `make verify`: not run by explicit operator instruction for this
  machine-heavy repository. This artifact does not claim full local verify.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/54dec1a9e980.json`
- Branch: `codex/extract-health-readiness-routes-from-legacy`.
- Task class: `Backend API`.
- PR phase: `pre_open`.
- Dispatch evidence:
  `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/54dec1a9e980.json --mode runtime --implementation-owner security-auditor --implementation-owner backend-engineer --pretty`.
- Pre-open role order completed:
  `agent-coordinator -> architecture-specialist -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter`.

## Premortem Finding Closure

- Artifact: `docs/review/PR_HEALTH_READINESS_ROUTE_EXTRACTION_PREMORTEM.md`.
- Skill: `pulseplate-premortem-risk-review`.
- Mode: `pr-premortem`.
- Decision: proceed with changes. Findings are fixed or dispositioned in this
  PR diff.
- PM-HEALTH-001 OpenAPI leak risk: FIXED by `include_in_schema=False`,
  bootstrap rejection of OpenAPI-visible health router state, and
  `tests/test_app_endpoints_combined.py` OpenAPI assertions.
- PM-HEALTH-002 duplicate/foreign handler risk: FIXED by atomic
  `_include_health_router_if_needed` checks and
  `tests/test_main_paywall_bootstrap.py` negative cases.
- PM-HEALTH-003 DB readiness semantic drift: FIXED by preserving fallback,
  degraded env var, session-shape, `SELECT 1`, and `503 Database unavailable`
  behavior in `app/routers/health.py`, with `tests/test_health_db.py` coverage.
- PM-HEALTH-004 `/ready` insight runtime fallback drift: FIXED by preserving
  fail-soft fallback and warning behavior, covered by `tests/test_health_db.py`
  and `tests/test_legacy_app_diff_coverage.py`.
- PM-HEALTH-005 stale legacy guard allowlist: FIXED by shrinking
  `scripts/ci/check_legacy_growth_guard.py` and adding
  `tests/test_legacy_growth_guard.py` health/readiness reintroduction coverage.
- PM-HEALTH-006 raw `legacy_app:app` serving risk: NOT-A-BUG for this canonical
  entrypoint migration. Evidence: `docs/deploy/OPERATIONAL_SIGNALS.md` and
  `docs/architecture/LEGACY_COMPATIBILITY_SEAM.md` now name canonical health
  ownership.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/health-readiness-oracle-packet.json`.
- Artifact: `artifacts/orchestration/experiments/results/health-readiness-oracle-result.json`
- Experiment id: `exp-f74309e63c52`.
- Runner mode: `oracle_only_governance_reviewer`.
- Status: accepted.
- Oracles:
  - `python3 -m pytest -q tests/test_health_db.py tests/test_app_endpoints_combined.py tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/test_app_openapi_coverage.py tests/test_legacy_app_diff_coverage.py` returned 0.
  - `python3 scripts/ci/check_legacy_growth_guard.py` returned 0.
- Mutation boundary: `mutated_paths=[]`, `shared_tree_untouched=true`,
  `promotion_ready=false`.
- Material contribution: `oracle_review`.
- Co-author trailer required: yes, because the accepted oracle result shaped
  validation and commit decision.
- Commit trailer present on implementation commit:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- Review threads at PR open: none known.
- Bot review/actionables at PR open: pending.
- Final current-head review thread, bot actionable, and strict disposition
  checks are still required before any merge-readiness claim.

## Post-Open Role Review Evidence

- `qa-engineer-agent`: found one blocker. `tests/test_legacy_app_git_sha.py`
  still imports `legacy_app._short_git_sha`, and the implementation commit had
  removed that compatibility re-export while moving route ownership. Disposition:
  FIXED by commit `79c44aae0`, which restores the explicit
  `_short_git_sha as _short_git_sha` legacy compatibility re-export without
  returning health/readiness route ownership to `legacy_app.py`.
- `bug-hunter`: found one blocker. `_include_health_router_if_needed` accepted
  pre-existing canonical endpoint routes if those routes had
  `include_in_schema=True`, leaving health/readiness probes visible in OpenAPI.
  Disposition: FIXED by commit `a0041d9e8`, which rejects visible pre-existing
  health routes and adds
  `test_health_route_registration_rejects_visible_existing_canonical_handlers`.
- `security-auditor`: found one procedural blocker. The remote PR ref still
  pointed at `79c44aae0` while local reviewed `HEAD` included the
  bug-hunter fix and mapping evidence. Disposition: FIXED by pushing through
  current PR head `8be6db630b1fb257be583d0d76a8aee8f6590a66`. Security-auditor
  found no security code blockers on that local reviewed head.

## Codex Security Diff Scan / Finding Discovery

- Skill: `codex-security:security-diff-scan`.
- Scope: PR diff `origin/main...HEAD` for source-like changed files
  `app/main.py`, `app/routers/health.py`, and `legacy_app.py`.
- Report: `/tmp/codex-security-scans/BMI-App_2025_clean/pr-1969-health-readiness-routes/report.md`.
- HTML report: `/tmp/codex-security-scans/BMI-App_2025_clean/pr-1969-health-readiness-routes/report.html`.
- Work ledger:
  `/tmp/codex-security-scans/BMI-App_2025_clean/pr-1969-health-readiness-routes/artifacts/02_discovery/work_ledger.jsonl`.
- Result: PASS, no reportable findings. Every diff-scoped source-like row has
  a completion receipt, and discovery produced no plausible candidates requiring
  validation or attack-path analysis.
- Validator:
  `python3 .../codex-security/0.1.8/scripts/validate_report_format.py --report-md /tmp/codex-security-scans/BMI-App_2025_clean/pr-1969-health-readiness-routes/report.md`: PASS.

## PulsePlate PR Review

- Skill: `pulseplate-pr-review`.
- Context: `/tmp/pulseplate_pr_1969_review_context.json`.
- Markdown report: `/tmp/pulseplate_pr_1969_review_report.md`.
- JSON report: `/tmp/pulseplate_pr_1969_review_report.json`.
- Result: one advisory `note` for large-diff review planning because the PR
  diff exceeds the 800 changed-line threshold.
- Disposition: NOT-A-BUG.
- Evidence: this PR is intentionally the bounded health/readiness extraction
  slice; the oversized line count is dominated by review/governance artifacts
  (`docs/review/PR_1969_FIXED_MAPPING.md` and
  `docs/review/PR_HEALTH_READINESS_ROUTE_EXTRACTION_PREMORTEM.md`) plus tests.
  The code scope remains the planned canonical route extraction, bootstrap
  guard, legacy handler removal, and guard shrink. Focused gates and
  post-open role reviews have run.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- `python3 scripts/orchestration/check_preflight.py`: PASS after rebase onto
  `origin/main`.
- `.venv/bin/python -m py_compile app/routers/health.py app/main.py legacy_app.py scripts/ci/check_legacy_growth_guard.py`: PASS.
- `.venv/bin/python -m pytest -q tests/test_health_db.py tests/test_app_endpoints_combined.py tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/test_app_openapi_coverage.py tests/test_legacy_app_diff_coverage.py`: PASS.
- `.venv/bin/python scripts/ci/check_legacy_growth_guard.py`: PASS.
- `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`: PASS after rebase and after the typed helper fix.
- `PRE_COMMIT_HOME=/tmp/pre-commit-health-readiness-routes .venv/bin/pre-commit run --all-files`: PASS.
- `PRE_COMMIT_HOME=/tmp/pre-commit-health-readiness-routes .venv/bin/pre-commit run mypy --hook-stage pre-push --files app/routers/health.py app/main.py legacy_app.py`: PASS after the typed helper fix.
- `.venv/bin/python -m pytest -q tests/test_legacy_app_git_sha.py`: PASS after
  commit `79c44aae0`.
- `.venv/bin/python -m pytest -q tests/test_main_paywall_bootstrap.py::test_health_route_registration_rejects_visible_existing_canonical_handlers tests/test_main_paywall_bootstrap.py::test_health_route_registration_is_idempotent`: PASS after commit `a0041d9e8`.
- `git push` pre-push hooks: PASS for mypy, pip-audit, backend pytest,
  full-repo bandit, and Docker build test.

## Machine-Heavy Verify Deferral

- Full local `make verify` was not run by explicit operator instruction because
  this repository has a very large test suite and this lane is using narrow
  backend/API validation.
- The accepted local validation authority for this PR before merge discussion is
  focused tests, guard script, `make validate-changed`, pre-commit, current-head
  CI parity, review disposition governance, and strict merge-readiness wrapper.
- No response, PR body, or mapping artifact may claim full local `make verify`
  passed.

## Merge Readiness

- [x] Post-open required role pass:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Codex Security diff scan / finding discovery.
- [x] `pulseplate-pr-review`.
- [ ] Current-head CI terminal success.
- [ ] PR body Phase2 gate against the live PR body.
- [ ] Strict review-thread disposition with auth.
- [ ] Strict merge-readiness wrapper with auth.
- [ ] CodeRabbit / Sourcery / Cubic / Codex review actionables checked and
  mapped or dispositioned on the current head.
- [ ] Mandatory wait-window after latest bot/review activity completed.

## Deferred / Follow-ups

- None for this slice.
