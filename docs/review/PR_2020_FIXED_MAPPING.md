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

- `768721bbe94e606b569a33513f6863b7a282afc7` -
  `fix(ci): shard nightly full tests without xdist`
- `0308bc80278ecb322baad64322c695f26a9e01b4` -
  `test(ci): cover stale nightly html coverage cleanup`
- `1538c543a1615977f1bb50cc8e7834d269184e3d` -
  `fix(ci): isolate nightly shard history artifacts`
- `9e21f181fac84d7d4acd8c0420efc9e7f273aa49` -
  `docs(review): record PR 2020 post-open fixes`
- `8549f0c60f34bceafdeadcb2b3833eaee7e0562c` -
  `docs(review): fix PR 2020 replay command`
- `1472836233f733c34e8839d68841ac3ec117d1c8` -
  `fix(ci): keep shard history path idempotent`
- `c006a5f2562dc5a31535bcd136d918ed0c24bb7f` -
  `fix(ci): fetch full history for nightly full tests`
- `68b20f9e714673e877d1284bcc0ae7311f48cf99` -
  `fix(ci): bound nightly shard cleanup and coverage phases`
- `8a610447a8a4b13113090d208f65ec9f4c2709a9` -
  `test(ci): guard nightly fail-closed controls`
- `f36164b0a5dca55546675befa2358fdf78d7fc40` -
  `fix(ci): avoid nightly shard pool shutdown hang`
- `7033ea15ded7616be277c2bc6b5be097ff4559dc` -
  `fix(ci): harden nightly shard inputs`

Artifact-only mapping commits may be the latest PR head while carrying no
code/test behavior. They are not used as self-referential FIXED proof; this
artifact maps the code or test commit that changed the reviewed behavior.

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
- Co-author trailer included in `768721bbe94e606b569a33513f6863b7a282afc7`:
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
- Commit hooks during `768721bbe`: YAML, formatting, lint, Bandit,
  changed-file backend tests, and conventional commit checks passed.
- Pre-push hooks: YAML, formatting, lint, changed-file mypy, pip-audit,
  backend pre-push pytest, full-repo Bandit, and Docker build test passed.
- PASS after bug-hunter hardening fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py::test_remove_previous_outputs_deletes_stale_shard_files tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after bug-hunter hardening fix: `make validate-changed`
- PASS during commit `0308bc802`: formatting, lint, changed-file backend tests,
  and conventional commit checks passed.
- PASS during push after `0308bc802`: pip-audit, backend pre-push pytest, and
  full-repo Bandit passed.
- PASS after post-open cursor and Codex Security hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after post-open cursor and Codex Security hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m mypy scripts/ci/run_main_test_shards.py`
- PASS after post-open cursor and Codex Security hardening fixes:
  `make validate-changed`
- PASS during commit `1538c543`: formatting, lint, changed-file backend tests,
  Bandit, and conventional commit checks passed.
- PASS after bug-hunter double-scope fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after bug-hunter double-scope fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m mypy scripts/ci/run_main_test_shards.py`
- PASS after bug-hunter double-scope fix:
  `make validate-changed`
- PASS during commit `147283623`: formatting, lint, changed-file backend tests,
  Bandit, and conventional commit checks passed.
- PASS after manual nightly dispatch failure fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only`
- PASS after manual nightly dispatch failure fix:
  `make validate-changed`
- PASS during commit `c006a5f`: YAML, workflow, formatting, lint,
  changed-file backend tests, and conventional commit checks passed.
- PASS after manual nightly timeout fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after manual nightly timeout fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m mypy scripts/ci/run_main_test_shards.py`
- PASS after manual nightly timeout fix: `git diff --check`
- PASS after manual nightly timeout fix: `make validate-changed`
  - This selected
    `tests/test_ci_workflow_pr_size_governance_contract.py` and
    `tests/test_main_test_shards.py` and passed.
- PASS after manual nightly timeout fix: `pre-commit run --all-files`
- PASS during commit `68b20f9e`: YAML, workflow, formatting, lint, Bandit,
  changed-file backend tests, and conventional commit checks passed.
- PASS after Codex Security current-head test-gap fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest -q tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py`
- PASS after Codex Security current-head test-gap fixes: `make validate-changed`
  - This selected
    `tests/test_ci_workflow_pr_size_governance_contract.py` and
    `tests/test_main_test_shards.py` and passed.
- PASS after Codex Security current-head test-gap fixes: `git diff --check`
- PASS after Codex Security current-head test-gap fixes:
  `pre-commit run --all-files`
- PASS during commit `8a610447`: formatting, lint, changed-file backend
  tests, and conventional commit checks passed.
- PASS after current-head nightly parent-hang fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py -q`
- PASS after current-head nightly parent-hang fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; MYPYPATH=. "$VENV_PYTHON" -m mypy --explicit-package-bases --no-incremental --cache-dir=/dev/null scripts/ci/run_main_test_shards.py tests/test_main_test_shards.py`
- PASS after current-head nightly parent-hang fix:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" scripts/ci/run_main_test_shards.py --python-version 3.13 --shard-count 16 --max-parallel 4 --marker-expression 'not demo' --durations-min 1.0 --report-chars fEsxXw --htmlcov --list-shards`
- PASS after current-head nightly parent-hang fix: `make validate-changed`
  - This selected
    `tests/test_ci_workflow_pr_size_governance_contract.py` and
    `tests/test_main_test_shards.py` and passed.
- PASS after current-head nightly parent-hang fix:
  `pre-commit run --all-files`
- PASS during commit `f36164b0`: formatting, lint, changed-file backend tests,
  Bandit, and conventional commit checks passed.
- PASS guard-first after CodeRabbit hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist tests/guards/test_security_devtooling_regression_guards.py::test_changed_docs_do_not_add_local_users_absolute_paths -q`
- PASS after CodeRabbit hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" -m pytest tests/test_main_test_shards.py tests/test_ci_workflow_pr_size_governance_contract.py -q`
- PASS after CodeRabbit hardening fixes:
  `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; MYPYPATH=. "$VENV_PYTHON" -m mypy --explicit-package-bases --no-incremental --cache-dir=/dev/null scripts/ci/run_main_test_shards.py tests/test_main_test_shards.py`
- PASS after CodeRabbit hardening fixes: `make validate-changed`
  - This selected
    `tests/test_ci_workflow_pr_size_governance_contract.py` and
    `tests/test_main_test_shards.py` and passed.
- PASS after CodeRabbit hardening fixes: `pre-commit run --all-files`
- PASS during commit `7033ea15`: YAML, workflow, formatting, lint, Bandit,
  changed-file backend tests, and conventional commit checks passed.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2020#discussion_r3476816398 -> 7033ea15ded7616be277c2bc6b5be097ff4559dc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2020#discussion_r3476816414 -> 7033ea15ded7616be277c2bc6b5be097ff4559dc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2020#pullrequestreview-4573974281 -> 7033ea15ded7616be277c2bc6b5be097ff4559dc
Disposition: FIXED
Commit: 7033ea15ded7616be277c2bc6b5be097ff4559dc
Evidence: `.github/workflows/nightly-tests.yml` sets `persist-credentials: false`; `scripts/ci/run_main_test_shards.py::validate_durations_min` rejects non-finite values; tests cover both contracts.

## Post-Open Role Findings

Finding: `bug-hunter` noted that stale shard coverage and JUnit cleanup were
covered, but stale `htmlcov` cleanup did not yet have a direct regression test.

Disposition: FIXED
Commit: `0308bc80278ecb322baad64322c695f26a9e01b4`
Evidence: `tests/test_main_test_shards.py::test_remove_previous_outputs_deletes_stale_shard_files`
now creates `htmlcov/index.html` and asserts `remove_previous_outputs(...)`
removes the stale `htmlcov` directory before a new run.

Finding: post-open `cursor-specialist-agent` noted that process-level nightly
parallelism could make every shard write to the same `BAYESIAN_HISTORY_PATH`
when `BAYESIAN_PERSIST=1`.

Disposition: FIXED
Commit: `1538c543a1615977f1bb50cc8e7834d269184e3d`
Evidence: `scripts/ci/run_main_test_shards.py::shard_bayesian_history_path`
scopes enabled Bayesian history persistence per shard, and
`tests/test_main_test_shards.py::test_build_shard_env_scopes_bayesian_history_when_persisting`
locks the nightly `/tmp/test_execution_history-py313-shard-3.json` shape.

Finding: post-open `cursor-specialist-agent` noted the validation commands in
this artifact were not directly replayable from the isolated worktree because
they used `.venv/bin/python` while the shared repo virtualenv is resolved by
`scripts/hooks/repo_python.sh`.

Disposition: FIXED
Commit: `8549f0c60f34bceafdeadcb2b3833eaee7e0562c`
Evidence: local validation commands in this artifact now use
`VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; "$VENV_PYTHON" ...`.

Finding: Codex Security diff-scan worker candidate `CAND-PR2020-01` noted that
the workflow was fail-closed, but the workflow contract test did not assert
`test_exit_code=$?` and `exit "$test_exit_code"`.

Disposition: FIXED
Commit: `1538c543a1615977f1bb50cc8e7834d269184e3d`
Evidence:
`tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist`
now asserts the `set +e` runner invocation, captured exit code, restored
`set -e`, and explicit `exit "$test_exit_code"` propagation.

Finding: post-open `bug-hunter` noted that `BAYESIAN_HISTORY_PATH` was scoped in
the parent shard process and then scoped a second time in explicit child mode,
turning `/tmp/test_execution_history-py313-shard-3.json` into
`/tmp/test_execution_history-py313-shard-3-py313-shard-3.json`.

Disposition: FIXED
Commit: `1472836233f733c34e8839d68841ac3ec117d1c8`
Evidence: `scripts/ci/run_main_test_shards.py::shard_bayesian_history_path`
now returns an already shard-scoped history path unchanged, and
`tests/test_main_test_shards.py::test_build_shard_env_keeps_parent_scoped_bayesian_history_idempotent`
covers the parent-to-child env path.

Finding: manual `Nightly Full Tests` dispatch `28159837728` on head
`7a690b9e010c4d1d231af6c80b9d91ec40edeed6` failed in shard 16 because
`tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only`
could not inspect `origin/main...HEAD` in the shallow `workflow_dispatch`
checkout: `fatal: origin/main...HEAD: no merge base`.

Disposition: FIXED
Commit: `c006a5f2562dc5a31535bcd136d918ed0c24bb7f`
Evidence: `.github/workflows/nightly-tests.yml` now checks out full history
with `fetch-depth: 0`, matching existing CI jobs that need `origin/main`
merge-base visibility. The workflow contract test
`tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist`
asserts the full-history checkout, and the previously failing guard passed
locally with
`tests/test_design_automation_next_lane_docs.py::test_kimi_protocol_current_diff_stays_docs_only`.

Finding: manual `Nightly Full Tests` dispatch `28163474872` on head
`f359d81c084aab519de84667ae6bf00ce63fc7c1` and current-head dispatch
`28178861034` on head `906d50cec85ea2392fdf5672b63dd6c5cfefcd87` were canceled
by the 90 minute job timeout after all 16 process shards had already reported
`exit_code=0`; no post-shard `coverage combine/xml/html/report` diagnostics or
coverage artifacts were emitted. The `28178861034` log proved the prior
process-pool cleanup patch was insufficient: shard 16 finished at
`2026-06-25T15:33:00Z`, but the parent runner did not reach coverage before the
job canceled at `2026-06-25T16:20:38Z`.

Disposition: FIXED
Commit: `f36164b0a5dca55546675befa2358fdf78d7fc40`
Evidence: `scripts/ci/run_main_test_shards.py` no longer wraps shard
subprocesses in `ProcessPoolExecutor`. The parent runner now owns the shard
process groups directly, starts up to `--max-parallel`, polls child exit codes,
terminates running process groups on shard timeout, fail-fast cancellation, or
SIGTERM/SIGINT, and proceeds directly to the bounded coverage phases after all
child processes exit successfully. The prior coverage subprocess diagnostics
from `68b20f9e714673e877d1284bcc0ae7311f48cf99` remain in place. Regression
coverage:
`tests/test_main_test_shards.py::test_run_all_shards_stops_refilling_after_first_failure`,
`tests/test_main_test_shards.py::test_run_all_shards_times_out_and_reports_selected_files`,
`tests/test_main_test_shards.py::test_run_all_shards_combines_serial_coverage_before_parallel_shards`,
and
`tests/test_main_test_shards.py::test_run_all_shards_generates_htmlcov_when_requested`.

Finding: Codex Security current-head file review noted that the nightly
workflow contract test observed the current fail-closed workflow, but did not
explicitly guard `permissions: contents: read` or the absence of
`continue-on-error`.

Disposition: FIXED
Commit: `8a610447a8a4b13113090d208f65ec9f4c2709a9`
Evidence:
`tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist`
now asserts the nightly workflow permission block stays exactly
`{"contents": "read"}` and asserts `continue-on-error` is absent from both the
`tests` job and the full-suite step.

Finding: Codex Security current-head file review noted that shard timeout tests
proved the `124` timeout result, but did not prove that timed-out child
processes are terminated.

Disposition: FIXED
Commit: `8a610447a8a4b13113090d208f65ec9f4c2709a9`
Evidence: `tests/test_main_test_shards.py::test_run_shard_fails_timeout_even_with_clean_artifacts`
and `tests/test_main_test_shards.py::test_run_shard_fails_timeout_without_clean_artifacts`
now assert the timeout path calls `_terminate_process_group(...)`.
`tests/test_main_test_shards.py::test_terminate_process_group_sends_sigterm_on_posix`
and
`tests/test_main_test_shards.py::test_terminate_process_group_escalates_to_sigkill_on_timeout`
cover the POSIX SIGTERM and SIGKILL escalation behavior directly.

Finding: Codex Security current-head file review noted that the latest
artifact-only mapping head may not appear in its own implementation commit
list.

Disposition: NOT-A-BUG
Evidence: This artifact now explicitly states that artifact-only mapping commits
may be the latest PR head and are not used as self-referential FIXED proof. The
behavior-changing Codex Security fixes are mapped to
`8a610447a8a4b13113090d208f65ec9f4c2709a9`.
Reason: Requiring the artifact to map its own final docs-only mapping commit
would create an endless self-reference loop and would not improve disposition
proof quality.

Finding: CodeRabbit review comment
`discussion_r3476816398` noted that `actions/checkout` persisted GitHub
credentials in the nightly workflow even though the job only needs read-only
checkout access.

Disposition: FIXED
Commit: `7033ea15ded7616be277c2bc6b5be097ff4559dc`
Evidence: `.github/workflows/nightly-tests.yml` now keeps `fetch-depth: 0` for
merge-base visibility while setting `persist-credentials: false`, and
`tests/test_ci_workflow_pr_size_governance_contract.py::test_nightly_full_tests_uses_process_shards_without_xdist`
guards the checkout contract.

Finding: CodeRabbit review comment
`discussion_r3476816414` noted that `--durations-min nan` or infinite values
could pass CLI validation and poison deterministic shard ordering.

Disposition: FIXED
Commit: `7033ea15ded7616be277c2bc6b5be097ff4559dc`
Evidence: `scripts/ci/run_main_test_shards.py::validate_durations_min` now
requires a finite non-negative value, and
`tests/test_main_test_shards.py::test_main_rejects_unsafe_cli_values` covers
`nan`, `inf`, and `-inf`.

## Security Notes

- Workflow permissions remain `contents: read`.
- Nightly checkout keeps full history for merge-base guards while disabling
  persisted checkout credentials.
- Dependency install continues through the existing `python-setup` action and
  private-index env flow.
- No public PyPI fallback, no dependency upgrade, no `continue-on-error`, and no
  `|| true` masking were added.
- The shard runner no longer uses a process pool around subprocess shards; the
  parent process owns and terminates child process groups directly.
- The new post-shard coverage subprocess is bounded by
  `MAIN_TEST_COVERAGE_TIMEOUT_SECONDS`, uses argv-list execution with
  `sys.executable -m coverage`, does not invoke a shell, and includes a scoped
  Bandit justification on the subprocess call.

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
