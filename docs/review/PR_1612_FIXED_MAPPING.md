# PR #1612 Fixed Mapping

## PR

- URL: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1612
- Branch: `codex/hotfix-main-coverage-floor-2`
- Title: `test(ci): restore main coverage floor`

## Scope

- Coordinator-owned hotfix continuation after `main` coverage stayed below 97%.
- Adds focused deterministic tests only.
- Does not lower coverage thresholds, weaken CI, revert prior PRs, or change runtime behavior.

## Local Evidence

- `python3 scripts/orchestration/check_preflight.py` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/pytest tests/test_utils_pack_facades_coverage.py tests/test_food_source_menustat_replacement.py tests/test_legacy_app_scheduler_non_pytest_path.py -q` PASS.
- `pre-commit run --all-files` PASS.
- Pre-push hooks PASS.
- CI-equivalent coverage probe reached total coverage `97.01%`; the local run had one worktree-environment failure because `make openapi` requires a checkout-local `.venv` in the temp worktree. GitHub current-head CI remains authoritative for that job.

## Discussion Thread Pass

No review threads yet.

## Fixed in Commit Mapping

No review threads yet.

## Merge Readiness

- [ ] Current-head PR CI is green.
- [ ] CodeRabbit/Sourcery/Cubic actionables are mapped or explicitly classified.
- [ ] `check_merge_ready.py --require-auth` passes before merge.
