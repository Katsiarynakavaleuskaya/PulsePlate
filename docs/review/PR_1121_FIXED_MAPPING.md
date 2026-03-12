# PR 1121 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 30349022
Evidence: `scripts/design/execution_adapters.py:106` and `scripts/design/execution_adapters.py:118` now derive `component_count` from the materialized render plan with a hierarchy-aware fallback, while `tests/test_design_generation_pipeline.py:199` locks the behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922264698 -> 30349022

Disposition: FIXED
Commit: 30349022
Evidence: `scripts/design/layout_templates.py:389` and `scripts/design/layout_templates.py:392` now turn unknown template keys into an explicit `ValueError`, and `tests/test_design_generation_pipeline.py:216` covers the failure contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922264703 -> 30349022

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `scripts/design/generate_figma_instructions.py:513` and `scripts/design/generate_figma_instructions.py:540` now publish the canonical `web.plate` semantic roles, `scripts/design/instructions/web_plate.json:184` and `scripts/design/instructions/web_plate.json:217` mirror them in the checked-in artifact, and `tests/test_design_generation_pipeline.py:76` locks hierarchy-to-instruction parity.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922268154 -> 9a1ebf8e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922268164 -> 9a1ebf8e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922272563 -> 9a1ebf8e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922276425 -> 9a1ebf8e

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md:27` now points the hard-rule range at tools `5-8`, which matches the renumbered precedence list.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922268167 -> 9a1ebf8e

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `scripts/design/layout_templates.py:389` through `scripts/design/layout_templates.py:395` now return a descriptive `ValueError` with the supported template list, and `tests/test_design_generation_pipeline.py:216` verifies the message contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922272567 -> 9a1ebf8e

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `docs/review/PR_1121_FIXED_MAPPING.md:54` now leaves the merge-readiness checklist unchecked until the final merge cycle, matching the repo governance contract for pre-merge artifacts.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3933958270 -> 9a1ebf8e

Disposition: NOT-A-BUG
Evidence: `scripts/design/contracts.py:13` constrains the supported screen ids to the canonical six-screen set, `scripts/design/execute_design.py:63` rejects runtime payloads outside that set, and `scripts/design/generate_figma_instructions.py:967` fails generation when a screen id is absent from the governed content model. Under that contract, lossy collisions such as `ios.home` versus `ios-home` cannot enter the runtime lane.
Reason: `_prefix()` currently derives ids only from governed screen identifiers, so adding hashed suffixes would churn stable generated ids without covering a reachable execution path in PR2.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922272565

Disposition: FIXED
Commit: f3ab3667
Evidence: `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md:31` now points the layout template reference at `scripts/design/layout_templates.py:383`, and `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md:40` points the deterministic adapter reference at `scripts/design/execution_adapters.py:20`, so both anchors land on live definitions instead of blank lines.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922605569 -> f3ab3667
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922605576 -> f3ab3667

## Merge Readiness
- [ ] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed
