# PR 2167 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/2ec8d8552cbf.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/exp-2167-v011-freeze-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8675810f969b9dc69acf98de2158503b243c4e97
Evidence: scripts/orchestration/pr_review_evidence.py:138-139,914-961; tests/test_pr_review_material_seal.py:2014-2052
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2167#discussion_r3617225703 -> 8675810f969b9dc69acf98de2158503b243c4e97

Disposition: FIXED
Commit: cb4eadcb4e06e2e9c7befd9cddc9704c969cf3c4
Evidence: scripts/orchestration/pr_review_evidence.py:639,717; tests/test_pr_review_material_seal.py:1960-2004
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2167#discussion_r3617402788 -> cb4eadcb4e06e2e9c7befd9cddc9704c969cf3c4

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"authority":"trusted_codex_review_source_unavailability","binding_kind":"seal_context_only","blocking":false,"fallback_required":false,"material_digest":"sha256:0a07d3a79b51b12d2ed82e79a39cfcecb858a7c0170f45d5c34b697dcb3e463b","material_head_sha":"cb4eadcb4e06e2e9c7befd9cddc9704c969cf3c4","quota_body_sha256":"sha256:e39b189a2ed6388c9d919876a2893ca0216a023301e11d788df190b4366991b9","quota_created_at":"2026-07-20T21:29:43Z","quota_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2167#issuecomment-5027472129","review_claim":"none","schema_version":"pulseplate.codex-review-source-unavailability/v1","source":"codex_review","source_degraded":true,"source_status":"usage_limit_reached","status":"tooling_unavailable"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:82d8b4711d93020596ac1afd9188f01d04f13448e93354e593672006cc352617","findings_sha256":"sha256:c9d7ebb453ba811fafde7804319c2b6ce543b64c020370674b2d23c7eecf054c","work_ledger_sha256":"sha256:681be5c185cd6edb51ba18a4ae727b7d0b5b489984ed7066cfe3d93fad85a645"},"authority":"human_asserted_content_receipt","base_revision":"c325489612809e0c9dfc8bb300aca606a8bf7c49","coverage_completeness":"complete","findings_count":0,"head_revision":"cb4eadcb4e06e2e9c7befd9cddc9704c969cf3c4","manifest_sha256":"sha256:4dd994c53e2163bd4188984084fad4d6d1980e90d7855ca39c4acb461b86c5c0","producer":{"name":"codex-security-plugin","version":"0.1.11"},"scan_id":"26ac8fbb-5fb9-4b62-86c6-f3a50e1101cd","snapshot_digest":"codex-security-snapshot/v1:sha256:0a07d3a79b51b12d2ed82e79a39cfcecb858a7c0170f45d5c34b697dcb3e463b"},"material":{"base_ref_oid":"c325489612809e0c9dfc8bb300aca606a8bf7c49","digest":"sha256:0a07d3a79b51b12d2ed82e79a39cfcecb858a7c0170f45d5c34b697dcb3e463b","material_head_sha":"cb4eadcb4e06e2e9c7befd9cddc9704c969cf3c4","merge_base_sha":"c325489612809e0c9dfc8bb300aca606a8bf7c49","policy_version":"pulseplate.material-classification/v1"},"pr_number":2167,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
