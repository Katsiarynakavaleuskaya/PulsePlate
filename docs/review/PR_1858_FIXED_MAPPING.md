# PR #1858 - Fixed in Commit Mapping

**Title:** `chore(deps): consolidate governed Python dependency bumps`
**Branch:** `codex/dependency-governed-consolidation`
**Scope:** Governed consolidation of Dependabot PRs `#1854`, `#1855`, `#1856`, and `#1857`.
**Primary commit:** `803bae53e`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#discussion_r3330511250 -> 8a77fea69
Disposition: FIXED
Commit: 8a77fea69
Evidence: `requirements-all.txt:14` updates the disabled `safety` comment from `safety>=3.2` to `safety>=3.8.1`, matching the governed floor in `constraints.txt`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#pullrequestreview-4397171888 -> 8a77fea69
Disposition: FIXED
Commit: 8a77fea69
Evidence: The aggregate CodeRabbit review reported the same stale disabled `safety` comment as `discussion_r3330511250`; `requirements-all.txt:14` fixes that actionable item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#pullrequestreview-4397167074
Disposition: NOT-A-BUG
Evidence: `requirements-dev.in`, `requirements-dev.txt`, `requirements-lock.txt`, `requirements-test.in`, `requirements-test.txt`, `constraints.txt`, and `docs/review/PR_DEPENDENCY_CONSOLIDATION_PREMORTEM.md` intentionally name exact dependency pins as the auditable source and validation evidence for this narrow Dependabot consolidation lane.
Reason: Sourcery's centralization suggestion is valid maintainability feedback, but implementing a new dependency-version source of truth would widen this PR beyond consolidating `#1854`-`#1857`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#pullrequestreview-4397176966
Disposition: NOT-A-BUG
Evidence: Cubic reported "No issues found" and did not request a code, test, documentation, or governance change.
Reason: No actionable Cubic finding exists to fix in this PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#discussion_r3330562319
Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor 8a77fea69 d93136f34d74a55b605db9f2b9313125591921ca` exits 0, proving the mapped CodeRabbit fix commit is reachable from the current PR head. Current-head `Merge readiness gate` also passed for run `26717975582`.
Reason: The connector comment reviewed a stale synthetic commit view; the current branch head contains the mapped fix commit and the strict guard accepted the mapping.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1858#discussion_r3330562321
Disposition: NOT-A-BUG
Evidence: `git log --format=%B -2 71e38d29a 803bae53e` shows the exact `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` trailer on the two commits materially shaped by the accepted Experiment Runner result.
Reason: The later CodeRabbit fix and review-mapping commits were post-open governance/code-review responses, not Experiment Runner-shaped implementation commits, so omitting the trailer from those commits preserves the repo attribution invariant.

## Implementation Evidence

Disposition: FIXED
Commit: 803bae53e
Evidence: `constraints.txt`, `requirements-all.txt`, `requirements-dev.in`, `requirements-dev.txt`, `requirements-test.in`, and `requirements-test.txt` carry the consolidated testing/tooling bumps from Dependabot `#1854`: `coverage>=7.14.1`, `pytest-asyncio>=1.4.0`, and `hypothesis~=6.155.1`.

Disposition: FIXED
Commit: 803bae53e
Evidence: `constraints.txt`, `requirements-all.txt`, `requirements-dev.in`, `requirements-dev.txt`, and `requirements-lock.txt` carry the governed `ruff 0.15.15` update from Dependabot `#1855` while preserving combined-lock parity.

Disposition: FIXED
Commit: 803bae53e
Evidence: `constraints.txt` carries the `safety>=3.8.1` floor from Dependabot `#1856`.

Disposition: FIXED
Commit: 803bae53e
Evidence: `constraints.txt`, `requirements-ci-lite.in`, `requirements-ci-lite.txt`, `requirements-dev.in`, and `requirements-dev.txt` carry the `diff-cover 10.3.0` update from Dependabot `#1857`.

Disposition: FIXED
Commit: 803bae53e
Evidence: `requirements-dev.txt` intentionally rejects generated unsafe `pip==26.1.1` lock churn; `tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip` passed in focused local validation and Experiment Runner oracle review.

Disposition: FIXED
Commit: 803bae53e
Evidence: `tests/test_install_locked_python_requirements.py` and `tests/test_python_supply_chain_controls.py` update focused guard expectations for `ruff 0.15.15` lock parity and `coverage[toml]==7.14.1` in the test dependency profile.

Disposition: FIXED
Commit: 803bae53e
Evidence: `docs/review/PR_DEPENDENCY_CONSOLIDATION_PREMORTEM.md` records dependency-lane failure modes for lock drift, private-index lag, unsafe pip lock churn, runtime-scope leakage, and SQLite scope leakage.

## Role-Agent / Premortem Pass

- `agent-coordinator` - completed; decision: proceed with PR1 only and keep runtime/toolchain alignment as PR2.
- `dev-operator` - completed; validation plan and stop conditions recorded, including staged/unstaged reconciliation and private-index validation.
- `architecture-specialist` - completed; required preserving `ruff==0.15.15` in `requirements-lock.txt` and rejecting unsafe `pip==26.1.1` lock churn.
- `app-store-release-agent` - completed; no direct iOS/Fastlane/App Store release-surface blocker found.
- `qa-engineer-agent` - completed; required ruff lock parity, unsafe pip removal, and focused dependency guard validation.
- `bug-hunter` - completed; confirmed the same ruff parity, staged pip, and premortem packet issues before they were fixed.
- `security-auditor` - completed; confirmed no direct dependency security stop after unsafe pip and ruff parity fixes, with private-index validation still required.
- Post-open `qa-engineer-agent` - completed; confirmed the CodeRabbit safety-comment finding was valid and in scope.
- Post-open `bug-hunter` - completed; confirmed the local safety-comment fix needed a new post-comment commit and mapping update.
- Post-open `security-auditor` - completed; confirmed the safety-comment fix was adequate, Sourcery centralization is NOT-A-BUG for this lane, and no security/supply-chain blocker remains after mapping.
- `pulseplate-premortem-risk-review` - completed in `docs/review/PR_DEPENDENCY_CONSOLIDATION_PREMORTEM.md`.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/0bec9cf9c850.json`
- Note: `scripts/orchestration/start_pr_lane.sh` was attempted first but did not produce a worktree in this host; manual branch/worktree creation was used after repo `check_preflight.py` and `task_bootstrap.py` completed.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/dependency-consolidation-oracle-result.json`
- Mode: `oracle_only_governance_reviewer`
- Result: accepted; 2/2 oracle commands passed; shared tree untouched; `coauthor_required=true`.
- Commit trailer used: `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` on commits `803bae53e` and `71e38d29a`.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --path ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python scripts/orchestration/check_experiment_runner_identity.py` - PASS.
- `.venv/bin/python scripts/ci/install_locked_python_requirements.py --preflight-only` - PASS.
- Private-index exact-wheel probe via `PULSEPLATE_PYTHON_INDEX_URL` for local CPython 3.13 macOS wheels - PASS.
- Private-index exact-wheel probe via `PULSEPLATE_PYTHON_INDEX_URL` for CPython 3.13 manylinux x86_64 wheels - PASS.
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py::test_repo_ruff_private_proxy_pin_is_not_stale_emergency_fallback tests/test_install_locked_python_requirements.py::test_repo_quality_tooling_profile_matches_dependabot_replacement_contract tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_python_supply_chain_controls.py::test_test_dependency_profile_is_split_from_dev_tooling` - PASS.
- `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/test_dependency_security_guard.py tests/test_repo_policy_guards.py` - PASS.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS after `.secrets.baseline` was refreshed by `detect-secrets`.
- Pre-push hooks - PASS, including pip-audit, backend tests, full-repo bandit, and docker build test.
- Post-open focused validation after CodeRabbit fix:
  - `python3 scripts/orchestration/check_preflight.py --path requirements-all.txt --path docs/review/PR_1858_FIXED_MAPPING.md` - PASS.
  - `.venv/bin/python -m pytest -q tests/test_install_locked_python_requirements.py::test_repo_quality_tooling_profile_matches_dependabot_replacement_contract tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_python_supply_chain_controls.py::test_test_dependency_profile_is_split_from_dev_tooling` - PASS.
  - `make validate-changed` - PASS.

## Machine-Heavy Gate Deferral

Full local `make verify` was started and passed `verify-env`, lint, mypy, and `test-fast`, then the full coverage/diff-cov run was stopped at operator direction because this repository has 10k+ tests and this dependency/tooling lane uses narrow local gates plus current-head CI. This artifact does not claim local full-verify readiness.

Merge readiness still requires current-head CI parity, no unresolved review threads, no actionable bot findings, strict merge-readiness checks, and the mandatory wait-window.
