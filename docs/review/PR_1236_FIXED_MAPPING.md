# PR 1236 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- Status: in progress; PR is draft, local gates are green, waiting for review/bot intake on the pushed head.
- Current fix commits:
  - `bfee71de` — `fix(security): unblock pip-audit baseline`
- Current scope discipline:
  - remediate `requests` baseline to `2.33.0` across tracked dependency surfaces
  - document a temporary `pip-audit` ignore for `GHSA-5239-wwwm-4pmq`
  - track ignore removal in `docs/roadmap/BACKLOG_LEDGER.md`
- Local validation executed on this lane:
  - `python3 scripts/orchestration/check_preflight.py`
  - `pytest -q tests/test_dependency_security_guard.py`
  - `pre-commit run --hook-stage pre-push pip-audit --all-files`
  - `pre-commit run --all-files`
  - `make verify`
- Required before merge:
  - refresh this artifact after bot/human review comments arrive
  - resolve threads only after disposition evidence exists
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
