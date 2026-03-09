# PR 1061 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3917772269
Disposition: NOT-A-BUG
Evidence: Review body is a Sourcery rate-limit notice with no code finding to address.
Reason: This review contains no actionable implementation feedback.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3917787941 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: tests/test_legacy_weekly_plan_alias_api.py:251

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907556833 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: tests/test_legacy_weekly_plan_alias_api.py:251

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3917799557 -> 3fbc03db
Disposition: FIXED
Commit: 3fbc03db
Evidence: legacy_app.py:3258

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907567013 -> 3fbc03db
Disposition: FIXED
Commit: 3fbc03db
Evidence: legacy_app.py:3258

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907575145
Disposition: NOT-A-BUG
Evidence: app/routers/vip.py:588; app/routers/vip.py:597
Reason: The helper intentionally keys `echo_payload` off the resolved builder so the default route preserves the pre-refactor contract: when module-level `make_weekly_menu` is available, the canonical VIP path echoes `request_obj.model_dump()` instead of the sparse fallback payload.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907575159 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: legacy_app.py:3239

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907575169 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: legacy_app.py:3265

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907575176 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: legacy_app.py:3295

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907575193 -> b59964d0
Disposition: FIXED
Commit: b59964d0
Evidence: tests/test_legacy_weekly_plan_alias_api.py:102

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3917808319
Disposition: NOT-A-BUG
Evidence: legacy_app.py:4590; legacy_app.py:4594; legacy_app.py:4653; app/routers/vip.py:518; app/routers/vip.py:588
Reason: This review summary aggregates four inline findings fixed above plus two deliberate compatibility decisions: the hidden legacy alias remains runtime-callable under existing `_get_api_key_dynamic` semantics, and the canonical VIP helper keeps the pre-refactor `echo` behavior. The public VIP surface remains gated at `/api/v1/vip/menu/weekly/plan`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907715232 -> dc959872
Disposition: FIXED
Commit: dc959872
Evidence: legacy_app.py:3246; legacy_app.py:3257; tests/test_legacy_weekly_plan_alias_api.py:270

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3917967588 -> dc959872
Disposition: FIXED
Commit: dc959872
Evidence: legacy_app.py:3246; legacy_app.py:4635; tests/test_legacy_weekly_plan_alias_api.py:167

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907802282 -> 76824910
Disposition: FIXED
Commit: 76824910
Evidence: docs/review/PR_1061_FIXED_MAPPING.md:16; docs/review/PR_1061_FIXED_MAPPING.md:21

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907802293 -> 76824910
Disposition: FIXED
Commit: 76824910
Evidence: legacy_app.py:3223; legacy_app.py:3271; legacy_app.py:3285; tests/test_legacy_weekly_plan_alias_api.py:334

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907802299 -> 76824910
Disposition: FIXED
Commit: 76824910
Evidence: legacy_app.py:3302; tests/test_legacy_weekly_plan_alias_api.py:254

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3918067947 -> 76824910
Disposition: FIXED
Commit: 76824910
Evidence: docs/review/PR_1061_FIXED_MAPPING.md:16; legacy_app.py:3223; legacy_app.py:3302; tests/test_legacy_weekly_plan_alias_api.py:334

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907863018
Disposition: NOT-A-BUG
Evidence: docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:34; scripts/ci/check_pr_body_phase2_gates.py:111; scripts/orchestration/review_mapping_artifact.py:101
Reason: The canonical Phase 2 artifact contract requires these two checkbox lines to remain checked in `docs/review/PR_<N>_FIXED_MAPPING.md`; unchecking them would fail the artifact validator instead of reflecting current governance state.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#discussion_r2907863024 -> 3f42a408
Disposition: FIXED
Commit: 3f42a408
Evidence: legacy_app.py:3229; legacy_app.py:3262; legacy_app.py:3272; tests/test_legacy_weekly_plan_alias_api.py:363

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1061#pullrequestreview-3918134801
Disposition: NOT-A-BUG
Evidence: docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:34; scripts/ci/check_pr_body_phase2_gates.py:111; legacy_app.py:3229; tests/test_legacy_weekly_plan_alias_api.py:363
Reason: This summary aggregates the two inline findings captured immediately above: the checklist comment is not a bug under the current artifact contract, and the non-finite day-value recovery issue was fixed in `3f42a408`.
