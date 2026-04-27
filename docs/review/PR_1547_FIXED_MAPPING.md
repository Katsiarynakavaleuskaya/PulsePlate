# PR #1547 - Fixed in Commit Mapping (canonical)

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1547>
Branch: `fix/rag-weekly-release-gates-canonical-sample`
Date: 2026-04-27

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1547#pullrequestreview-4183550480

Disposition: NOT-A-BUG
Evidence: scripts/evals/run_rag_release_gates.py:1731
Reason: Sourcery review is an auto-generated summary of the already-landed implementation (calibration threshold fix, small-fixture advisory, docs, tests); no additional code change required beyond the PR commits.

## Initial Evidence
- `pre-commit run --all-files` (PASS)
- `make validate-min` (PASS)
- `pytest -q tests/test_rag_release_gates_runner.py` (PASS)
