# PR 1403 — Fixed in Commit Mapping

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
Notes: This replacement PR supersedes stale Dependabot PR #1399. Local validation on branch head `045f6f9d0` passed for `pre-commit run --all-files`, pre-push hooks, and `make validate-min` with `VENV_PYTHON=${VENV_PYTHON:-.venv/bin/python}`. The replacement lane keeps the diff scoped to `requirements-dev.txt` and `requirements-lock.txt`, with only `types-pyyaml 6.0.12.20250915 -> 6.0.12.20260408` and no unrelated runtime/CUDA lock regeneration. The source Dependabot branch introduced unrelated `requirements.txt` churn and failed CI bootstrap on the internal simple index while resolving `cuda-pathfinder==1.5.2`, which is outside the scope of this stub-only bump.
