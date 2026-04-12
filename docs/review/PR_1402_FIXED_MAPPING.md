# PR 1402 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- No actionable review comments

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [ ] `make verify` green
Notes: This replacement PR supersedes stale Dependabot PR #1397. Local validation on branch head `304abcb3c` passed for `pre-commit run --all-files`, `pytest -q tests/test_repo_policy_guards.py`, and `make validate-min VENV_PYTHON=.venv/bin/python`. The replacement lane keeps the diff scoped to `requirements-dev.in`, `requirements-dev.txt`, and `requirements-lock.txt`, with only `ruff 0.15.9 -> 0.15.10` and no runtime/CUDA drift.
