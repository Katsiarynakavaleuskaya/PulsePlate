# PR #1641 Fixed in Commit Mapping

## Summary

PR #1641 fixes the import hygiene guard failure on `main` by removing
`sys.path.insert` from `tests/evals/conftest.py` and removing the stale
allowlist entry from `tests/test_repo_policy_guards.py`.

## Root Cause

`tests/evals/conftest.py` mutated `sys.path` to make `scripts.evals.*`
importable. The import hygiene guard (`tests/test_import_hygiene_guard.py`)
forbids this pattern in test files. The mutation was redundant because
`pyproject.toml` already sets `pythonpath = "."`.

## Scope

- `tests/evals/conftest.py`
- `tests/test_repo_policy_guards.py`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1641#discussion_r3177732677
  Disposition: FIXED
  Commit: 3fab25392
  Evidence: docs/review/PR_1641_FIXED_MAPPING.md (artifact updated with canonical format)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1641#discussion_r3177732679
  Disposition: FIXED
  Commit: 3fab25392
  Evidence: docs/review/PR_1641_FIXED_MAPPING.md (Discussion Thread Pass section added)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1641#pullrequestreview-4215974470
  Disposition: NOT-A-BUG
  Evidence: CodeRabbit review summary — no actionable items
  Reason: Review summary approving the change, no code modifications needed

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1641#pullrequestreview-4215975347
  Disposition: NOT-A-BUG
  Evidence: Cubic review summary — inline comments addressed in commit 3fab25392
  Reason: Summary references inline comments already mapped above as FIXED

## Validation

- `pytest -q tests/test_import_hygiene_guard.py` — PASS
- `pytest -q tests/test_repo_policy_guards.py` — PASS
- `pytest -q tests/evals/` — PASS (53 tests)
- `make validate-min` — PASS
- `pre-commit run --all-files` — PASS

## Merge Readiness

- [x] CI green
- [x] import hygiene guard green
- [x] review mapping artifact created
- [x] no actionable bot comments remain
- [ ] mandatory wait-window elapsed
