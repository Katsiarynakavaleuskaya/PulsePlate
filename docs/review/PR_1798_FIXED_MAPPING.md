<!-- markdownlint-disable MD013 -->
# PR 1798 Fixed Mapping

## Summary

PR: #1798
Title: `feat(design): add visual regression decision gate`

This artifact is the canonical Fixed in Commit Mapping source of truth for PR #1798.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Local Evidence

- Commit: `5edc0a8c4`
- Task packet: `artifacts/orchestration/task_packets/8b20d2c58929.json`
- Experiment Runner evidence: `artifacts/orchestration/experiments/results/exp-884d61c8da9a.json`
- Validator evidence: `python scripts/design/design_visual_regression_decisions.py validate docs/orchestration/contracts/design_visual_regression_decisions.v1.json` -> `PASS: design visual regression decisions valid`
- Focused tests: `python -m pytest -q tests/test_design_visual_regression_decisions.py` -> `41 passed`
- Focused existing tests: `python -m pytest -q tests/test_design_bridge_coverage_inventory.py tests/test_design_component_registry.py tests/test_design_automation_next_lane_docs.py` -> passed
- Changed validation: `make validate-changed` -> passed
- Pre-commit: `pre-commit run --all-files` -> passed

## Deferred / Follow-ups

- Accessibility regression decision gate remains next.
- Token/runtime parity follows visual and accessibility gates.

## Merge Readiness

Not merge-ready at artifact creation. Current-head CI, bot review disposition, review-thread disposition guard with auth, strict merge-readiness wrapper with auth, and wait-window remain pending.
