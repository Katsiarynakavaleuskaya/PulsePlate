# PR #1511 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511>
Branch: `codex/main-ci-py312-timeout-root-cause`
Date: 2026-04-23

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: Current-head GitHub CI proof completed for commit `b3edd4ff`;
  required post-proof review cycle is still pending.
- Current implementation commit: `b3edd4ff`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 853694874
Evidence: CodeRabbit actionables fixed in workflow, runner, packet, and tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3133512254 -> 853694874
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3133512268 -> 853694874
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3133512274 -> 853694874
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#pullrequestreview-4165580559 -> 853694874

Disposition: FIXED
Commit: e5673b71c
Evidence: Review actionables fixed in shard runner, tests, packet, backlog, and mapping wording.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136788725 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136788739 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136788760 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136799288 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136811065 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#discussion_r3136811075 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#pullrequestreview-4169448952 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#pullrequestreview-4169459758 -> e5673b71c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1511#pullrequestreview-4169472607 -> e5673b71c

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path tests/test_ci_workflow_pr_size_governance_contract.py --path docs/orchestration --path docs/roadmap/BACKLOG_LEDGER.md` PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` PASS.
- `PYENV_VERSION=3.12.7 python -m pytest -q tests/test_py312_main_shards.py tests/test_ci_workflow_pr_size_governance_contract.py` PASS.
- `PYENV_VERSION=3.12.7 python scripts/ci/run_py312_main_shards.py --list-shards --shard-count 2` PASS.
- `pre-commit run --all-files --show-diff-on-failure` PASS.
- `VENV_PYTHON=.venv/bin/python make validate-changed` PASS.
- Push pre-push hooks PASS: yaml, workflow check, black, ruff, mypy changed
  files, pip-audit, backend pre-push pytest, full-repo bandit, docker build
  test.
- Additional main evidence from 2026-04-23: run `24854923154`, job
  `72765173124`, failed `test-main (3.12, 60)` with `Segmentation fault
  (core dumped)` at roughly 20% under the sequential no-xdist coverage command.
- QA post-open review found that PR CI skipped `test-main`; fixed by adding
  `run_main_ci_diagnostic` routing so PRs changing the main-CI Python 3.12
  runner/workflow contract execute the `test-main` matrix before merge.
- CodeRabbit review `4165580559` fixed by `853694874`.
- Current-head CI run `24859466516` on commit `b3edd4ff` passed:
  `test-main (3.12, 60)` in `37m42s`, `test-main (3.11, 60)` in `6m58s`,
  `test-main (3.13, 90)` in `1h21m9s`, `coverage-pr` in `13s`, and
  `diff-coverage` in `55s`.

## Deferred Follow-up

- `make verify` is deferred because the governing failure mode is the full
  main-suite Python 3.12 runtime budget. Current-head GitHub CI is the heavy
  signal for this lane.
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-py312-xdist-root-cause-hardening`
  remains the follow-up anchor for any future pytest-xdist restoration audit.

## Merge Readiness

- [ ] Current-head `test-main (3.12, 60)` completes without timeout.
- [ ] Current-head `test-main (3.12, 60)` has no xdist worker-node termination.
- [ ] `test-main (3.11, 60)` and `test-main (3.13, 90)` do not regress.
- [ ] CodeRabbit, Sourcery, and Cubic actionables are mapped or explicitly
  marked non-actionable.
- [ ] Final check pass completed after latest bot/review activity.
- [ ] Waited at least one review cycle before merge.
