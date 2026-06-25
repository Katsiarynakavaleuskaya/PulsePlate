# PR #2020 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2020
Title: `fix(ci): shard nightly full tests without xdist`
Branch: `codex/stabilize-nightly-full-tests`

## Summary

This PR stabilizes `Nightly Full Tests` by replacing the single
`pytest-xdist` full-suite invocation with the existing deterministic
process-level shard runner.

In scope:

- Wire `.github/workflows/nightly-tests.yml` to
  `scripts/ci/run_main_test_shards.py`.
- Preserve nightly depth with explicit `--marker-expression "not demo"`.
- Preserve coverage enforcement and artifacts with `coverage.xml`, terminal
  coverage, `--fail-under=97`, and opt-in `htmlcov` generation.
- Add shard runner CLI controls for nightly diagnostics without changing
  existing `CI test-main` defaults.
- Add focused regression guards for runner behavior and the nightly workflow
  contract.

Out of scope:

- PR #2017 private-index/devpi work.
- Python hash-verified lock migration.
- Dependency upgrades or fallback host changes.
- Product/runtime/OpenAPI/route behavior.
- Coverage threshold weakening, skips, xfails, or legacy cleanup.

## Implementation Commits

- `ae8e98264fa320e345a04349bf8368adb73001be` -
  `fix(ci): shard nightly full tests without xdist`
- `9352af82dc191193824ca7880170e8b9c67f21d7` -
  `test(ci): cover stale nightly html coverage cleanup`
- `0dfb47a6929c266e8378e80d55d656f32f8f10af` -
  `fix(ci): isolate nightly shard history artifacts`
- `fb6b651078fc1779a0f100bf40a345a26b515c28` -
  `docs(review): record PR 2020 post-open fixes`

## Lane Start Provenance

- Worktree: `worktrees/stabilize-nightly-full-tests`
- Branch: `codex/stabilize-nightly-full-tests`
- Packet: `artifacts/orchestration/task_packets/37eacb8df716.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Role dispatch manifest:
  `scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/37eacb8df716.json --mode runtime --implementation-owner security-auditor --pretty`
- Dispatch order completed before implementation:
  `agent-coordinator -> cursor-specialist-agent -> security-auditor -> architecture-specialist`

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/nightly-full-tests-process-shards-premortem.md`
- Decision: `proceed with changes`
- Findings closed before PR open:
  - Nightly silently becomes shallower than before: FIXED by preserving
    `not demo` through a validated runner CLI option and workflow contract test.
  - Coverage artifacts regress: FIXED by opt-in `--htmlcov`, stale `htmlcov`
    removal, and fail-closed HTML coverage diagnostics.
  - Main CI behavior widens accidentally: FIXED by preserving current runner
    defaults unless nightly opts in.
  - Workflow security weakens: FIXED by keeping existing permissions,
    private-index setup, and no new public package fallback or shell masking.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/artifacts/orchestration/experiments/nightly-full-tests-process-shards-oracle-packet.json`
- Artifact:
  `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/nightly-full-tests-process-shards-oracle-result.json`
- Status: `accepted`
- Runner mode: `oracle_only_governance_reviewer`
- Contribution kind: `oracle_review`
- Co-author required: yes
- Co-author trailer included in `ae8e98264fa320e345a04349bf8368adb73001be`:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

## Local Validation

Passed locally:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/role_dispatch_bridge.py --packet artifacts/orchestration/task_packets/37eacb8df716.json --mode runtime --implementation-owner security-auditor --pretty`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_python_supply_chain_controls.py tests/guards/test_nosec_policy_guard.py tests/guards/test_subprocess_uses_absolute_binaries.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" scripts/ci/run_main_test_shards.py --python-version "3.13" --shard-count "16" --max-parallel "4" --marker-expression "not demo" --durations-min "1.0" --report-chars "fEsxXw" --htmlcov --list-shards`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m mypy scripts/ci/run_main_test_shards.py`
- `git diff --check`
- `make validate-changed`
  - After commit, this selected
    `tests/test_ci_workflow_pr_size_governance_contract.py` and
    `tests/test_main_test_shards.py` and passed.
- `pre-commit run --all-files`
- Commit hooks during `ae8e98264`: YAML, formatting, lint, Bandit,
  changed-file backend tests, and conventional commit checks passed.
- Pre-push hooks: YAML, formatting, lint, changed-file mypy, pip-audit,
  backend pre-push pytest, full-repo Bandit, and Docker build test passed.
- PASS after bug-hunter hardening fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py::test_remove_previous_outputs_deletes_stale_shard_files tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after bug-hunter hardening fix: `make validate-changed`
- PASS during commit `9352af82`: formatting, lint, changed-file backend tests,
  and conventional commit checks passed.
- PASS during push after `9352af82`: pip-audit, backend pre-push pytest, and
  full-repo Bandit passed.
- PASS after post-open cursor and Codex Security hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after post-open cursor and Codex Security hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m mypy scripts/ci/run_main_test_shards.py`
- PASS after post-open cursor and Codex Security hardening fixes:
  `make validate-changed`
- PASS during commit `0dfb47a`: formatting, lint, changed-file backend tests,
  Bandit, and conventional commit checks passed.

Full local `make verify` was not run under the operator-approved
machine-heavy CI/tooling exception. Current-head CI is the required heavy
parity signal before any merge-readiness claim.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Any later bot, human, CodeRabbit, Sourcery, Cubic, Codex Security, QA,
bug-hunter, security-auditor, or `pulseplate-pr-review` finding remains
blocking until fixed or formally dispositioned with evidence.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Findings

Finding: `bug-hunter` noted that stale shard coverage and JUnit cleanup were
covered, but stale `htmlcov` cleanup did not yet have a direct regression test.

Disposition: FIXED
Commit: `9352af82dc191193824ca7880170e8b9c67f21d7`
Evidence: `tests/test_main_test_shards.py::test_remove_previous_outputs_deletes_stale_shard_files`
now creates `htmlcov/index.html` and asserts `remove_previous_outputs(...)`
removes the stale `htmlcov` directory before a new run.

Finding: post-open `cursor-specialist-agent` noted that process-level nightly
parallelism could make every shard write to the same `BAYESIAN_HISTORY_PATH`
when `BAYESIAN_PERSIST=1`.

Disposition: FIXED
Commit: `0dfb47a6929c266e8378e80d55d656f32f8f10af`
Evidence: `scripts/ci/run_main_test_shards.py::shard_bayesian_history_path`
scopes enabled Bayesian history persistence per shard, and
`tests/test_main_test_shards.py::test_build_shard_env_scopes_bayesian_history_when_persisting`
locks the nightly `/tmp/test_execution_history-py313-shard-3.json` shape.

Finding: post-open `cursor-specialist-agent` noted the validation commands in
this artifact were not directly replayable from the isolated worktree because
they used `.venv/bin/python` while the shared repo virtualenv is resolved by
`scripts/hooks/repo_python.sh`.

Disposition: FIXED
Commit: `fb6b651078fc1779a0f100bf40a345a26b515c28`
Evidence: local validation commands in this artifact now use
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" ...`.

Finding: Codex Security diff-scan worker candidate `CAND-PR2020-01` noted that
the workflow was fail-closed, but the workflow contract test did not assert
`test_exit_code=$?` and `exit "$test_exit_code"`.

Disposition: FIXED
Commit: `0dfb47a6929c266e8378e80d55d656f32f8f10af`
Evidence:
`tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist`
now asserts the `set +e` runner invocation, captured exit code, restored
`set -e`, and explicit `exit "$test_exit_code"` propagation.

## Security Notes

- Workflow permissions remain `contents: read`.
- Dependency install continues through the existing `python-setup` action and
  private-index env flow.
- No public PyPI fallback, no dependency upgrade, no `continue-on-error`, and no
  `|| true` masking were added.
- Runner subprocess behavior remains argv-list based with `sys.executable` and
  no new subprocess or `# nosec` surface.

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
