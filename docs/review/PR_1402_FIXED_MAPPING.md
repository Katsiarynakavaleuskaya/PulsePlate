# PR 1402 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1402#pullrequestreview-4094866103
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1402#discussion_r3069267988
Disposition: FIXED
Commit: 95158a8d6
Evidence: docs/review/PR_1402_FIXED_MAPPING.md local validation note uses `VENV_PYTHON=.venv/bin/python`, not an absolute `/Users/...` path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1402#pullrequestreview-4094868024
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1402#discussion_r3069270438
Disposition: FIXED
Commit: 95158a8d6
Evidence: docs/review/PR_1402_FIXED_MAPPING.md local validation note uses `VENV_PYTHON=.venv/bin/python`, not an absolute `/Users/...` path.

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [ ] `make verify` green
Notes: This replacement PR supersedes stale Dependabot PR #1397. Local validation on branch head `304abcb3c` passed for `pre-commit run --all-files`, `pytest -q tests/test_repo_policy_guards.py`, and `make validate-min VENV_PYTHON=.venv/bin/python`. The replacement lane keeps the diff scoped to `requirements-dev.in`, `requirements-dev.txt`, and `requirements-lock.txt`, with only `ruff 0.15.9 -> 0.15.10` and no runtime/CUDA drift.
