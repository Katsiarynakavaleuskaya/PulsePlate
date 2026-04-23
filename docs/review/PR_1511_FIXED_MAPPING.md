# PR #1511 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511>
Branch: `codex/main-ci-py312-timeout-root-cause`
Date: 2026-04-23

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

- Status: Draft PR opened for current-head GitHub CI proof. No human or bot
  review actionables were present when this artifact was created.
- Current implementation commit: `80b51e5ca`.

## Fixed in Commit Mapping

- No actionable review threads yet.

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path tests/test_ci_workflow_pr_size_governance_contract.py --path docs/orchestration --path docs/roadmap/BACKLOG_LEDGER.md` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `PYENV_VERSION=3.12.7 python -m pytest -q tests/test_py312_main_shards.py tests/test_ci_workflow_pr_size_governance_contract.py` PASS.
- `PYENV_VERSION=3.12.7 python scripts/ci/run_py312_main_shards.py --list-shards --shard-count 2` PASS.
- `pre-commit run --all-files --show-diff-on-failure` PASS.
- `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed` PASS.
- Push pre-push hooks PASS: yaml, workflow check, black, ruff, mypy changed
  files, pip-audit, backend pre-push pytest, full-repo bandit, docker build
  test.

## Deferred Follow-up

- `make verify` is deferred while PR #1511 is draft because the governing
  failure mode is the full main-suite Python 3.12 runtime budget. Current-head
  GitHub CI is the heavy signal for this lane.
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-py312-xdist-root-cause-hardening`
  remains the follow-up anchor for any future pytest-xdist restoration audit.

## Merge Readiness

- [ ] Current-head `test-main (3.12, 60)` completes without timeout.
- [ ] Current-head `test-main (3.12, 60)` has no xdist worker-node termination.
- [ ] `test-main (3.11, 60)` and `test-main (3.13, 90)` do not regress.
- [ ] CodeRabbit, Sourcery, and Cubic actionables are mapped or explicitly
  marked no-actionable.
- [ ] Final check pass completed after latest bot/review activity.
- [ ] Waited at least one review cycle before merge.
