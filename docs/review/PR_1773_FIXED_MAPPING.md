<!-- markdownlint-disable MD013 MD034 -->
# PR #1773 - Fixed in Commit Mapping

**PR:** Add oracle-only Experiment Runner PR participation
**Branch:** `codex/experiment-runner-oracle-only-pr-participation`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Post-open `qa-engineer-agent -> bug-hunter` pass completed
- [ ] CodeRabbit, Sourcery, Cubic, and review-thread no-actionable status verified

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 783ee256eecb7d8c65852fecbb2f4b8e4f214715
Evidence: `scripts/orchestration/experiment_contract.py:226` now calls `git --literal-pathspecs ls-files --error-unmatch -- <paths>`, and `tests/test_experiment_runner.py:273` covers `:(glob)` pathspec magic rejection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3270121817 -> 783ee256eecb7d8c65852fecbb2f4b8e4f214715
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3270168271 -> 783ee256eecb7d8c65852fecbb2f4b8e4f214715
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#pullrequestreview-4323820483 -> 783ee256eecb7d8c65852fecbb2f4b8e4f214715

Disposition: FIXED
Commit: 8806dd1f2c71ce725fab4b8834c18b2cdd00610f
Evidence: `scripts/orchestration/experiment_runner.py:268` normalizes invalid packet `runner_mode` values for rejection artifacts, `scripts/orchestration/experiment_runner.py:594` uses the stable oracle-only `candidate_patch` marker for oracle-only candidate-API rejection, and `tests/test_experiment_runner.py:427` plus `tests/test_experiment_runner.py:457` validate both rejection artifacts with `validate_experiment_result`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271443753 -> 8806dd1f2c71ce725fab4b8834c18b2cdd00610f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271443760 -> 8806dd1f2c71ce725fab4b8834c18b2cdd00610f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271463092 -> 8806dd1f2c71ce725fab4b8834c18b2cdd00610f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271463098 -> 8806dd1f2c71ce725fab4b8834c18b2cdd00610f

Disposition: FIXED
Commit: fe943dc8e4469d349c65b493a7f2bc3451e2aacc
Evidence: `scripts/orchestration/experiment_runner.py:264` now handles non-dict packets before `.get()`, and `tests/test_experiment_runner.py:524` validates the non-dict invalid-packet rejection artifact with `validate_experiment_result`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271463082 -> fe943dc8e4469d349c65b493a7f2bc3451e2aacc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#pullrequestreview-4325482196 -> fe943dc8e4469d349c65b493a7f2bc3451e2aacc

Disposition: FIXED
Commit: 2de4809281ebb35a6ec49b75775eaa13f685854e
Evidence: `scripts/orchestration/experiment_contract.py:245` defaults only missing/`None` runner modes and rejects explicit non-string or unknown values, `scripts/orchestration/experiment_runner.py:264` normalizes invalid experiment IDs to a schema-valid sentinel, and `tests/test_experiment_runner.py:254` plus `tests/test_experiment_runner.py:494` cover both cases.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271489521 -> 2de4809281ebb35a6ec49b75775eaa13f685854e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1773#discussion_r3271489523 -> 2de4809281ebb35a6ec49b75775eaa13f685854e

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md --path docs/orchestration/GOVERNED_NON_HUMAN_IDENTITY_POLICY.md --path scripts/AGENTS.md --path scripts/orchestration/experiment_runner.py --path tests/test_experiment_runner.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/check_experiment_runner_identity.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_experiment_bootstrap.py tests/test_experiment_promote.py tests/test_experiment_notify.py tests/test_experiment_pipeline.py tests/test_experiment_runner_identity_policy.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py tests/test_experiment_runner_identity_policy.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_experiment_bootstrap.py tests/test_experiment_promote.py tests/test_experiment_notify.py tests/test_experiment_pipeline.py tests/test_experiment_runner_identity_policy.py` after fixing CodeRabbit/Cubic pathspec findings
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py` after fixing CodeRabbit/Cubic pathspec findings
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_experiment_bootstrap.py tests/test_experiment_promote.py tests/test_experiment_notify.py tests/test_experiment_pipeline.py tests/test_experiment_runner_identity_policy.py` after fixing Codex rejection-artifact findings
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m flake8 scripts/orchestration/experiment_runner.py tests/test_experiment_runner.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py`
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_experiment_runner.py tests/test_experiment_bootstrap.py tests/test_experiment_promote.py tests/test_experiment_notify.py tests/test_experiment_pipeline.py tests/test_experiment_runner_identity_policy.py` after fixing Cubic non-dict packet and Codex sentinel findings
- PASS: `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m flake8 scripts/orchestration/experiment_contract.py scripts/orchestration/experiment_runner.py tests/test_experiment_runner.py`
- PASS: `pre-commit run mypy --hook-stage pre-push --files scripts/orchestration/experiment_contract.py scripts/orchestration/experiment_runner.py`
- PASS: `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks including changed-file mypy, pip-audit, backend tests, full-repo Bandit, and Docker build test

## Validation Caveats

Bare `make validate-changed` in this secondary worktree forced
`VENV_PYTHON="python3"` and failed on missing `fastapi`; the repo-vendored
interpreter override above is the successful equivalent for this worktree.

CodeRabbit CLI review timed out locally with review ID
`db6a3353-c90e-4c98-91ea-bb0e42e736ac`. GitHub PR status reported CodeRabbit
`SUCCESS`, Sourcery `SKIPPED`, and Cubic `SUCCESS` before this artifact update.
