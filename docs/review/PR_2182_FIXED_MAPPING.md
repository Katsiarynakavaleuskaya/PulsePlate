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
{"authority":"human_asserted_content_receipt","code_review":{"authority":"trusted_codex_review_source_unavailability","binding_kind":"seal_context_only","blocking":false,"fallback_required":false,"material_digest":"sha256:4d950b90804089b8903833b3b6f9d9e6ec2e8a68a3d56ec7613a5af10d13550c","material_head_sha":"2dd9eaba95b00449c353795d3a80141de94594a7","quota_body_sha256":"sha256:619c9f9f66a93f7e7ea60049aa147d2cf183fb706a71e11a710216ed2ba19d92","quota_created_at":"2026-07-24T20:34:46Z","quota_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2182#issuecomment-5074146954","review_claim":"none","schema_version":"pulseplate.codex-review-source-unavailability/v1","source":"codex_review","source_degraded":true,"source_status":"usage_limit_reached","status":"tooling_unavailable"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:c81c2a1d99c927121de409d58f30421fbb324d73307aaee2eff148a46f2eeab4","findings_sha256":"sha256:014063f45403321ad5f92e8a8d5545ae0c439b7707e2c544c5097781aa66cadd","work_ledger_sha256":"sha256:3e1ca495cb241e14afefc6379567fc62cd4f29a61d84222ee180e2634084ef39"},"authority":"human_asserted_content_receipt","base_revision":"f09c96c4800476fedd5a3d313616a45f84d0eb59","coverage_completeness":"complete","findings_count":0,"head_revision":"2dd9eaba95b00449c353795d3a80141de94594a7","manifest_sha256":"sha256:41cf1757b22d331b61c55c4c2718754036cfcfd63b3f92aad43b2e2d4d557eae","producer":{"name":"codex-security-plugin","version":"0.1.13"},"scan_id":"80d63c75-e2ef-447e-b07f-1319526b3ca5","snapshot_digest":"codex-security-snapshot/v1:sha256:4d950b90804089b8903833b3b6f9d9e6ec2e8a68a3d56ec7613a5af10d13550c"},"material":{"base_ref_oid":"f09c96c4800476fedd5a3d313616a45f84d0eb59","digest":"sha256:4d950b90804089b8903833b3b6f9d9e6ec2e8a68a3d56ec7613a5af10d13550c","material_head_sha":"2dd9eaba95b00449c353795d3a80141de94594a7","merge_base_sha":"f09c96c4800476fedd5a3d313616a45f84d0eb59","policy_version":"pulseplate.material-classification/v1"},"pr_number":2182,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
