# PR 2162 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/bab0ad074dc9.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/exp-e411a2f733cb.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 06e9e75cff860d1d16611594ebcf62b4807fdba9
Evidence: .github/workflows/ci.yml:674-681; tests/test_pgvector_compat.py:403-418
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3610768281 -> 06e9e75cff860d1d16611594ebcf62b4807fdba9

Disposition: FIXED
Commit: 06e9e75cff860d1d16611594ebcf62b4807fdba9
Evidence: .github/workflows/ci.yml:77; tests/test_pgvector_compat.py:390-409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3610768283 -> 06e9e75cff860d1d16611594ebcf62b4807fdba9

Disposition: FIXED
Commit: b8e064c4f9d55461ee6b85455ea36fdb344fe2c7
Evidence: tests/test_pgvector_compat.py:76-94,337-372; requirements-ci-lite.in:14; requirements-ci-lite.txt
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3610768284 -> b8e064c4f9d55461ee6b85455ea36fdb344fe2c7

Disposition: FIXED
Commit: 06e9e75cff860d1d16611594ebcf62b4807fdba9
Evidence: .github/workflows/ci.yml:674-681; tests/test_pgvector_compat.py:403-418
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3611356574 -> 06e9e75cff860d1d16611594ebcf62b4807fdba9

Disposition: FIXED
Commit: 06e9e75cff860d1d16611594ebcf62b4807fdba9
Evidence: .github/workflows/ci.yml:77,1147-1163; tests/test_pgvector_compat.py:390-409
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3611356578 -> 06e9e75cff860d1d16611594ebcf62b4807fdba9

Disposition: FIXED
Commit: a0c05df6b488cbf27f0addcf3adb25277e3b8237
Evidence: .github/workflows/ci.yml:77,1156-1163; tests/test_pgvector_compat.py:390-409; tests/test_pgvector_embedding_migration.py:13-33
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3611521041 -> a0c05df6b488cbf27f0addcf3adb25277e3b8237

Disposition: FIXED
Commit: b614da3cbcfcfff7659004f4135947ff06b35055
Evidence: tests/test_pgvector_compat.py:385-418 uniquely anchors the top-level job; .github/workflows/ci.yml:679-681 consumes only paths-filter boolean and GitHub job-result enums; actionlint and workflow guards pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#pullrequestreview-4730934386 -> b614da3cbcfcfff7659004f4135947ff06b35055

Disposition: NOT-A-BUG
Evidence: .github/workflows/ci.yml:77 keeps the review-critical selector explicit; tests/test_pgvector_compat.py:374-418 uses exact structural anchors and executable-input canaries.
Reason: A shared constant or broad YAML-parser refactor would widen this dependency compatibility PR without improving the exact fail-closed contract; the brittle ambiguous anchor was fixed narrowly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#pullrequestreview-4730922197

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"authority":"trusted_codex_review_source_unavailability","binding_kind":"seal_context_only","blocking":false,"fallback_required":false,"material_digest":"sha256:2e41261c679ef3b915894b1ad0eddd3c796391342451c75259ffd324b56fae7d","material_head_sha":"00b547776afa3873f5dd60f3bfc1b88d968d8453","quota_body_sha256":"sha256:e39b189a2ed6388c9d919876a2893ca0216a023301e11d788df190b4366991b9","quota_created_at":"2026-07-20T11:18:41Z","quota_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#issuecomment-5021643913","review_claim":"none","schema_version":"pulseplate.codex-review-source-unavailability/v1","source":"codex_review","source_degraded":true,"source_status":"usage_limit_reached","status":"tooling_unavailable"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:0047c2dce011f98bec20cd561f5332671a9008ec54ea89d01005291fc8a95d87","findings_sha256":"sha256:9d3eb7f4e24ca639cb24fcd8aaba5ce0aa633fc9b39fb8c0e6a2bf15c741bc6f","work_ledger_sha256":"sha256:9ec46006fa5fcc2813d1eb56462781bcf5094a8e8c37637ce482dfff128e3cd4"},"authority":"human_asserted_content_receipt","base_revision":"c325489612809e0c9dfc8bb300aca606a8bf7c49","coverage_completeness":"complete","findings_count":0,"head_revision":"00b547776afa3873f5dd60f3bfc1b88d968d8453","manifest_sha256":"sha256:26e5f5232fb833492cec1d36dbab631e5624ef0bcefa6d294625c67a91e0b724","producer":{"name":"codex-security-plugin","version":"0.1.11"},"scan_id":"4d0c0fbb-789a-40ff-a80e-302e90c6689d","snapshot_digest":"codex-security-snapshot/v1:sha256:b29cd87387ce08643fda3a8963a64a7ad4de6251663b88d3c5e2ad7b38032d93"},"material":{"base_ref_oid":"c325489612809e0c9dfc8bb300aca606a8bf7c49","digest":"sha256:2e41261c679ef3b915894b1ad0eddd3c796391342451c75259ffd324b56fae7d","material_head_sha":"00b547776afa3873f5dd60f3bfc1b88d968d8453","merge_base_sha":"c325489612809e0c9dfc8bb300aca606a8bf7c49","policy_version":"pulseplate.material-classification/v1"},"pr_number":2162,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
