# PR 1824 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1824
- Branch: `codex/main-coverage-scripts-ci-omit`
- Initial implementation commit: `008f7aa503d0d4002224b0ab36317a7cd4bf4a18`
- Mapping artifact commit: `96957c48572f44c3337ce08790df9a47c5e046af`

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/9498199b884d.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Main failure run classified: `26372552018`
- Experiment Runner oracle: `exp-0fc34adf981f`
- Final requested role order: `agent-coordinator -> dev-operator -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter`
- Mandatory post-open role order: `qa-engineer-agent -> bug-hunter -> security-auditor`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1824#discussion_r3295362610 -> 94dccc287fe159efe4d6d28f55134d736dd13586
Disposition: FIXED
Commit: 94dccc287fe159efe4d6d28f55134d736dd13586
Evidence: `scripts/run-backend-tests-pre-commit.sh` checks `SKIP_TESTS=1` before resolving repo Python or validating pytest availability; `tests/test_pre_commit_hook_python_resolver.py` covers the ordering contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1824#discussion_r3295372251 -> 8e788421892cd895301b37fa43c4d0af7fd60435
Disposition: FIXED
Commit: 8e788421892cd895301b37fa43c4d0af7fd60435
Evidence: `scripts/hooks/repo_python.sh` now immediately fails when an explicit absolute `VENV_PYTHON` or `DEV_PYTHON` override is not executable; `tests/test_pre_commit_hook_python_resolver.py` covers the fail-closed override behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1824#discussion_r3295372256 -> 8e788421892cd895301b37fa43c4d0af7fd60435
Disposition: FIXED
Commit: 8e788421892cd895301b37fa43c4d0af7fd60435
Evidence: `tests/test_pre_commit_hook_python_resolver.py` quotes the resolver path with `shlex.quote(...)` before passing it to `bash -lc`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1824#pullrequestreview-4353462449 -> 8e788421892cd895301b37fa43c4d0af7fd60435
Disposition: FIXED
Commit: 8e788421892cd895301b37fa43c4d0af7fd60435
Evidence: CodeRabbit's review-level actionable was the aggregate wrapper for `discussion_r3295372251` and `discussion_r3295372256`; both findings are fixed and mapped above.

## Main Failure Evidence

- `main` run `26372552018` at `2b34747eed264efd60e56502d8094521d1c0828e` failed `test-main (3.11, 60)` with:
  - `tests/test_qoder_dispatch_bridge.py::test_manifest_enforces_mandatory_tail_for_partial_requested_order_from_json_packet`
  - `tests/test_render_codex_start_prompt.py::test_packet_prompt_enforces_mandatory_tail_for_partial_requested_order`
- The same run failed `test-main (3.12, 90)` and `test-main (3.13, 90)` on the render role-order check.
- Disposition: FIXED
- Commit: `008f7aa503d0d4002224b0ab36317a7cd4bf4a18`
- Evidence:
  - `scripts/orchestration/qoder_dispatch_bridge.py` normalizes requested role order so `security-auditor` cannot remain before `bug-hunter` in the canonical post-open tail.
  - `tests/test_qoder_dispatch_bridge.py` covers explicit invalid security-before-bug ordering.
  - `tests/test_render_codex_start_prompt.py` covers packet prompt normalization to `qa-engineer-agent -> bug-hunter -> security-auditor`.

## Hook / FastAPI Drift Evidence

- Disposition: FIXED
- Commit: `008f7aa503d0d4002224b0ab36317a7cd4bf4a18`
- Evidence:
  - `scripts/hooks/repo_python.sh` resolves current checkout `.venv`, shared root `.venv` from `worktrees/...`, and fails closed locally when neither exists.
  - `.githooks/pre-commit`, `.githooks/pre-commit-unified`, `scripts/run-backend-tests-pre-commit.sh`, and `Makefile` run Python tools through the resolved interpreter.
  - `tests/test_pre_commit_hook_python_resolver.py` covers shared worktree `.venv`, relative override rejection, local fail-closed behavior, commit-hook `GIT_*` env handling, hook entrypoints, and Makefile contracts.
  - `docs/PRE_COMMIT_HOOKS.md` documents the resolver and FastAPI/import-drift rationale.

## Experiment Runner Evidence

Artifact: `artifacts/orchestration/experiments/results/exp-0fc34adf981f.json`

- Artifact class: local, gitignored
- Status: accepted
- Contribution kind: `oracle_review`
- Co-author trailer required and included in `008f7aa503d0d4002224b0ab36317a7cd4bf4a18`.
- Oracle command:
  - `python -m pytest -q tests/test_qoder_dispatch_bridge.py tests/test_render_codex_start_prompt.py tests/test_experiment_runner.py::test_python_oracle_path_prefix_uses_shared_worktree_root_venv tests/test_pre_commit_hook_python_resolver.py`

## Local Validation

- `python3 scripts/orchestration/check_preflight.py` PASS
- `python scripts/orchestration/check_agent_consistency.py` PASS
- Focused pytest through repo resolver PASS
- `bash -n .githooks/pre-commit .githooks/pre-commit-unified scripts/run-backend-tests-pre-commit.sh scripts/hooks/repo_python.sh` PASS
- `pre-commit run --all-files` PASS
- `make validate-changed` PASS after commit
- Commit hooks PASS
- Pre-push hooks PASS, including mypy changed-files, pip-audit, backend pre-push pytest, full-repo Bandit, and docker build test

## Advisory Agent Findings

- QA post-change pass: no blocking findings; required reruns completed.
- Bug-hunter finding: ambient Python / Makefile resolver false-green fixed in `008f7aa503d0d4002224b0ab36317a7cd4bf4a18`.
- Security finding: local system Python fallback removed for hook execution; resolver now fails closed locally.
- Security ordering concern: NOT-A-BUG for this PR because current canonical post-open tail and the operator plan require `qa-engineer-agent -> bug-hunter -> security-auditor`.

## Merge Readiness

- Current state: not merge-ready.
- Required before merge:
  - Current-head PR CI complete.
  - Mandatory post-open role pass complete.
  - Bot comments and review threads checked and dispositioned.
  - PR body mirror updated from this artifact after review activity.
  - `check_merge_ready.py --require-auth` passes.
  - Mandatory wait-window after latest review or bot activity.
