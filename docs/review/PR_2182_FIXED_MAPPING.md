# PR 2182 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/badc789f6cd2.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/bmr-test-ownership-80f74b8bf.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 80f74b8bf12f94389434c4669d6e93d04345b8ed
Evidence: tests/test_premium_bmr_api.py:801 and :820 pin the exact activity label plus Katch formula and note payload; canonical 44 tests passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#discussion_r3648218075 -> 80f74b8bf12f94389434c4669d6e93d04345b8ed

Disposition: FIXED
Commit: 80f74b8bf12f94389434c4669d6e93d04345b8ed
Evidence: tests/test_premium_bmr_api.py:854 uses an autouse monkeypatch fixture and context-managed client so API_KEY and FEATURE_PREMIUM_NUTRITION are restored.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#discussion_r3648218102 -> 80f74b8bf12f94389434c4669d6e93d04345b8ed

Disposition: FIXED
Commit: 80f74b8bf12f94389434c4669d6e93d04345b8ed
Evidence: Dead TestLegacyBMRImportFallback coverage was removed because GET / never exercised the patched BMR symbols; scoped 220 tests passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#discussion_r3648218109 -> 80f74b8bf12f94389434c4669d6e93d04345b8ed

Disposition: FIXED
Commit: 80f74b8bf12f94389434c4669d6e93d04345b8ed
Evidence: tests/test_premium_bmr_api.py:1164, :1215, :1258, and :1306 assert exact wrapper-precedence BMR and TDEE values; outer tests retain descriptive docstrings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#discussion_r3648218112 -> 80f74b8bf12f94389434c4669d6e93d04345b8ed

Disposition: FIXED
Commit: 80f74b8bf12f94389434c4669d6e93d04345b8ed
Evidence: All four actionable child findings fixed in tests/test_premium_bmr_api.py; canonical 44, targeted 90, and scoped 220 tests passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#pullrequestreview-4776819212 -> 80f74b8bf12f94389434c4669d6e93d04345b8ed

Disposition: NOT-A-BUG
Evidence: .pre-commit-config.yaml:135-142 defines manual pydocstyle with no 80-percent coverage threshold; exact-head CI lint and local pre-commit passed, and the four affected outer test docstrings were fixed.
Reason: The 80-percent metric is an external CodeRabbit advisory, not a repository-required gate; broad unrelated test-docstring churn would violate this behavior-neutral prerequisite scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#issuecomment-5074147472

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"authority":"trusted_codex_review_source_unavailability","binding_kind":"seal_context_only","blocking":false,"fallback_required":false,"material_digest":"sha256:74aa2ec46cb1378d82ef5be9fbac7df4d9cd9d3a1ef6c980e620d26908e8b3ae","material_head_sha":"80f74b8bf12f94389434c4669d6e93d04345b8ed","quota_body_sha256":"sha256:619c9f9f66a93f7e7ea60049aa147d2cf183fb706a71e11a710216ed2ba19d92","quota_created_at":"2026-07-24T20:34:46Z","quota_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#issuecomment-5074146954","review_claim":"none","schema_version":"pulseplate.codex-review-source-unavailability/v1","source":"codex_review","source_degraded":true,"source_status":"usage_limit_reached","status":"tooling_unavailable"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:4c452e881b380de6a299706341912507db6bd7431e36b906ff34f4cbdc016e93","findings_sha256":"sha256:e061851c555498349b85dcccafe9b20e621d3b2ab86083dfc3ede9aca73f0542","work_ledger_sha256":"sha256:d6ae924afa09b54d02affae21967ff8341e34619be8abf9d5bd8ff93161cae2f"},"authority":"human_asserted_content_receipt","base_revision":"2b5943ab355f2b8a5ecdbb075c3e1361c54b317f","coverage_completeness":"complete","findings_count":0,"head_revision":"80f74b8bf12f94389434c4669d6e93d04345b8ed","manifest_sha256":"sha256:e660164cf242ea9ddcb8e44d607d95165af1a34e0e17ed55a864456810772e18","producer":{"name":"codex-security-plugin","version":"0.1.12"},"scan_id":"966a492c-2987-4193-80f6-2018206755ad","snapshot_digest":"codex-security-snapshot/v1:sha256:74aa2ec46cb1378d82ef5be9fbac7df4d9cd9d3a1ef6c980e620d26908e8b3ae"},"material":{"base_ref_oid":"2b5943ab355f2b8a5ecdbb075c3e1361c54b317f","digest":"sha256:74aa2ec46cb1378d82ef5be9fbac7df4d9cd9d3a1ef6c980e620d26908e8b3ae","material_head_sha":"80f74b8bf12f94389434c4669d6e93d04345b8ed","merge_base_sha":"2b5943ab355f2b8a5ecdbb075c3e1361c54b317f","policy_version":"pulseplate.material-classification/v1"},"pr_number":2182,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
