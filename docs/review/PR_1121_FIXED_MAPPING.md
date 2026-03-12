# PR 1121 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 30349022
Evidence: `scripts/design/execution_adapters.py:104` and `scripts/design/execution_adapters.py:116` now derive `component_count` from the materialized render plan with a hierarchy-aware fallback, while `tests/test_design_generation_pipeline.py:182` locks the behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922264698 -> 30349022

Disposition: FIXED
Commit: 30349022
Evidence: `scripts/design/layout_templates.py:389` and `scripts/design/layout_templates.py:391` now turn unknown template keys into an explicit `ValueError`, and `tests/test_design_generation_pipeline.py:195` covers the failure contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922264703 -> 30349022

## Merge Readiness
- [x] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed
