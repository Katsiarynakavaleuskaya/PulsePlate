# PR #1654 Fixed in Commit Mapping

## Summary

Fix devcontainer-smoke CI by removing stale Yarn APT source from base image.

## Scope

- `.devcontainer/Dockerfile` only

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Validation

- `pytest -q tests/test_devcontainer_foundation.py` -- 10/10 PASS
- `pytest -q tests/test_devcontainer_smoke_workflow.py` -- 9/9 PASS
- `pre-commit run --all-files` -- all hooks PASS
