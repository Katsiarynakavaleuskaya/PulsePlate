# PR #1516 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the draft PR was opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Initial Implementation Commits

- `5fddee3e5` - `fix(ci): shard python 3.13 main tests`
- `cb5524107` - `fix(ci): keep py312 shard wrapper executable`

## Post-Open Review Dispositions

Disposition: FIXED
Commit: cb5524107
Evidence: `scripts/ci/run_py312_main_shards.py`; `tests/test_main_test_shards.py`; `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python scripts/ci/run_py312_main_shards.py --shard-count 1 --list-shards`.
Reason: Bug-hunter found that direct execution of the legacy Python 3.12 wrapper failed because `scripts` was not on `sys.path`; the wrapper now inserts the repo root before importing the shared runner and the test suite covers direct file execution.

## Local Validation

- [x] `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path scripts/ci/run_main_test_shards.py --path scripts/ci/run_py312_main_shards.py --path tests/test_main_test_shards.py --path tests/test_ci_workflow_pr_size_governance_contract.py --path tests/test_ci_risk_profile.py --path docs/orchestration --path docs/roadmap/BACKLOG_LEDGER.md --path AGENTS.md --path RUNBOOK_AGENT.md`
- [x] `python3 scripts/orchestration/check_agent_consistency.py`
- [x] `/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_main_test_shards.py tests/test_ci_risk_profile.py tests/test_ci_workflow_pr_size_governance_contract.py`
- [x] `make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python`
- [x] `pre-commit run --all-files`
- [x] Pre-push hook passed, including mypy, pip-audit, backend tests, bandit, and docker build test.
- [x] `check_pr_body_phase2_gates.py` passed against the updated PR body after
      exact Phase2 checklist and `No actionable review comments` wording were
      mirrored in PR #1516.

## Local make verify Deferral

Full local `make verify` is intentionally deferred for this machine-heavy
CI/tooling lane by operator instruction. Merge readiness must use canonical
current-head GitHub CI parity as the heavy signal: `lint`, `typecheck`, the
relevant `test-main` matrix, `diff-coverage` at >=97%, applicable
security/governance checks, and `check_merge_ready.py --require-auth`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] Current-head `test-main (3.13, 90)` completes with meaningful headroom
- [ ] Current-head `test-main (3.12, 60)` does not regress
- [ ] Python 3.11 does not regress
- [ ] All review threads resolved on GitHub after disposition updates
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least
      one review cycle before merging
- [ ] `check_merge_ready.py --pr-number 1516 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth` PASS
