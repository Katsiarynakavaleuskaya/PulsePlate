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

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-screen-content-template-convergence`
Reason: The aggregate Sourcery review also proposed converging `ScreenContentModel.layout_sections` and `ScreenContentModel.static_component_tree` with the reusable template registry. That cleanup is intentionally deferred out of PR2 so the runtime-template seam can merge without widening scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3933908427

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `scripts/design/generate_figma_instructions.py:513` and `scripts/design/generate_figma_instructions.py:540` now publish the canonical `web.plate` semantic roles, `scripts/design/instructions/web_plate.json:184` and `scripts/design/instructions/web_plate.json:217` mirror them in the checked-in artifact, and `tests/test_design_generation_pipeline.py:76` locks hierarchy-to-instruction parity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3933912553 -> 9a1ebf8e
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
Evidence: `docs/design/CODE_FIRST_UI_PROMPT_COOKBOOK.md:11`, `scripts/design/execute_design.py:207`, `scripts/design/layout_templates.py:389`, and `scripts/design/instructions/web_plate.json:184` close the actionable items collected in the aggregate CodeRabbit review, while the `_prefix()` concern remains explicitly dispositioned below as `NOT-A-BUG`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3933916914 -> 9a1ebf8e

Disposition: FIXED
Commit: 9a1ebf8e
Evidence: `docs/review/PR_1121_FIXED_MAPPING.md:54` now leaves the merge-readiness checklist unchecked until the final merge cycle, matching the repo governance contract for pre-merge artifacts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3933958270 -> 9a1ebf8e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922272556 -> 9a1ebf8e

Disposition: NOT-A-BUG
Evidence: `scripts/design/contracts.py:13` constrains the supported screen ids to the canonical six-screen set, `scripts/design/execute_design.py:63` rejects runtime payloads outside that set, and `scripts/design/generate_figma_instructions.py:967` fails generation when a screen id is absent from the governed content model. Under that contract, lossy collisions such as `ios.home` versus `ios-home` cannot enter the runtime lane.
Reason: `_prefix()` currently derives ids only from governed screen identifiers, so adding hashed suffixes would churn stable generated ids without covering a reachable execution path in PR2.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922272565

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-screen-content-template-convergence`
Reason: The later aggregate CodeRabbit nitpick review mixed one already-governed `_prefix()` concern, one documentation-numbering preference, and the same content-model/template convergence cleanup that is intentionally postponed to a dedicated follow-up PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3934269703

Disposition: FIXED
Commit: f3ab3667
Evidence: `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md:31` now points the layout template reference at `scripts/design/layout_templates.py:383`, and `docs/design/CODE_NATIVE_DESIGN_RUNTIME.md:40` points the deterministic adapter reference at `scripts/design/execution_adapters.py:20`, so both anchors land on live definitions instead of blank lines.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3934301606 -> f3ab3667
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922605569 -> f3ab3667
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2922605576 -> f3ab3667

Disposition: FIXED
Commit: 530b6d75
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:455`, `docs/roadmap/BACKLOG_LEDGER.md:462`, and `docs/roadmap/BACKLOG_LEDGER.md:479` now explicitly fold deferred `pulseplate_canvas_v1` work into the existing `ledger-p1-screen-content-template-convergence` item, so the postponed runtime artifact scope is recorded with owner, reason, links, and DoD.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#pullrequestreview-3934763535 -> 530b6d75
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1121#discussion_r2923028556 -> 530b6d75

## Merge Readiness
- [x] Local gates passed on current head
- [x] All required checks green
- [x] No unresolved review threads remain
- [x] CodeRabbit PASS / no-actionables
- [x] Sourcery PASS / no-actionables
- [x] Cubic PASS / no-actionables
- [x] Wait-window after latest bot/review activity observed
