<!-- markdownlint-disable MD013 MD034 -->
# PR 1764 Fixed In Commit Mapping

- PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1764>
- Branch: `codex/main-pip-coverage-lock-drift`
- Title: `fix(ci): align dependency profile guards`
- Implementing commit: `c2d3e04fea960fc0da20f8c14b485254f1ff7399`
- Scope: `requirements-dev.txt` and `tests/test_python_supply_chain_controls.py`. No runtime application source, CI workflow, OpenAPI, frontend, iOS, auth, billing, quota, or deployment behavior changed.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Initial current-head governance pass found no actionable human review threads. Internal role-agent findings were handled before PR governance: the unsafe-package block marker was restored above `setuptools` after removing only the `pip==26.1.1` unsafe pin, and the stale coverage-profile guard expectation now matches `requirements-test.txt`.

External CodeRabbit, Sourcery, and Cubic reviews remain merge-blocking until their current-head statuses are terminal and reviewed.

## Fixed in Commit Mapping

- No actionable review comments

## Local Validation Evidence

- Pre-flight: `python3 scripts/orchestration/check_preflight.py` - PASS.
- Task bootstrap: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase pre_open` - packet `c14abe6261f9`.
- Post-open governance bootstrap: `python3 scripts/orchestration/task_bootstrap.py ... --pr-phase post_open_review` - packet `bf2a10fedcf4`.
- Agent consistency: `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- Focused regression: `. .venv/bin/activate && pytest -q tests/test_dependency_security_guard.py::test_repo_managed_lock_surfaces_do_not_pin_pip tests/test_python_supply_chain_controls.py::test_test_dependency_profile_is_split_from_dev_tooling` - PASS.
- Dependency security guard bundle: `. .venv/bin/activate && pytest -q tests/test_dependency_security_guard.py tests/test_python_supply_chain_controls.py::test_test_dependency_profile_is_split_from_dev_tooling` - PASS.
- Changed-file validation after commit: `DEV_PYTHON=.venv/bin/python VENV_PYTHON=.venv/bin/python make validate-changed` - PASS; ran `tests/test_python_supply_chain_controls.py`.
- Pre-commit: `PRE_COMMIT_HOME=/tmp/pulseplate-precommit-main-pip-coverage pre-commit run --all-files` - PASS.
- Commit hooks: `git commit -m "fix(ci): align dependency profile guards"` - PASS.
- Pre-push hooks: `git push -u origin codex/main-pip-coverage-lock-drift` - PASS, including pip-audit, backend pre-push tests, and full Bandit.

### Machine-heavy / operator-approved narrow gate

- Full local `make verify` is deferred per the operator-approved machine-safe policy and root `AGENTS.md` machine-heavy PR exception. This PR uses focused local gates plus current-head GitHub CI as the heavy matrix/full coverage signal.

## Security Notes

- Supply-chain: repo-managed lock surfaces no longer pin `pip==...`, preserving the fail-closed guard for GHSA-58qw-9mgm-455v-pip.
- The unsafe-package marker remains above `setuptools==78.1.1`, preserving lockfile transparency for the remaining unsafe block.
- The coverage guard update mirrors the current `requirements-test.txt` lock value `coverage[toml]==7.14.0`; it does not introduce or upgrade dependencies.

## Risks / Rollback

- Risk: another dependency-profile drift exists outside the two failing main-CI assertions.
- Rollback: revert implementing commit `c2d3e04fea960fc0da20f8c14b485254f1ff7399`; no runtime behavior changed.

## Merge Readiness

- [x] Pre-flight + agent consistency: PASS.
- [x] Canonical artifact: this file (`docs/review/PR_1764_FIXED_MAPPING.md`).
- [x] PR body mirror: will be updated from this artifact before pushing this commit.
- [ ] Current-head CI: pending rerun after this artifact lands.
- [ ] Bot summaries reviewed (CodeRabbit / Sourcery / Cubic): pending terminal statuses.
- [ ] Strict review-thread disposition: pending `check_review_threads_disposition.py --require-auth`.
- [ ] Strict merge readiness: pending `check_merge_ready.py --require-auth`.

## Deferred / Follow-ups

- None.
