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
Commit: de6038d6ce7fb93147dac544dc2cb42c90b0cf8e
Evidence: tests/test_trivy_ignore_policy_expiry.py:119-130,453-467; focused Trivy policy tests and pre-commit pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3616180730 -> de6038d6ce7fb93147dac544dc2cb42c90b0cf8e

Disposition: FIXED
Commit: b614da3cbcfcfff7659004f4135947ff06b35055
Evidence: tests/test_pgvector_compat.py:385-418 uniquely anchors the top-level job; .github/workflows/ci.yml:679-681 consumes only paths-filter boolean and GitHub job-result enums; actionlint and workflow guards pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#pullrequestreview-4730934386 -> b614da3cbcfcfff7659004f4135947ff06b35055

Disposition: FIXED
Commit: bec83538accb4ff48bbb451afe7084b4399c14ea
Evidence: .github/workflows/ci.yml:679-689; tests/test_trivy_ignore_policy_expiry.py:119-130,453-467; actionlint, focused tests, make validate-changed, and pre-commit pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#pullrequestreview-4737269432 -> bec83538accb4ff48bbb451afe7084b4399c14ea

Disposition: NOT-A-BUG
Evidence: The live PR head descends from bec83538accb4ff48bbb451afe7084b4399c14ea, and scripts/orchestration/pr_review_closeout.py:734-756 plus scripts/ci/check_pr_merge_readiness.py:615-633 recompute and accept the sealed live material digest.
Reason: The reviewed 720f0f71dff25becf9eac2e69b19362f6b7dd85b ref is an unavailable synthetic squash, not the live PR head; the canonical seal remains valid for the unchanged material digest.
Fingerprint: sha256:8e6435d916bc32e4089cefdf99be6bd17b6f7ba2f5f9cad4aa705c3d343b2e26
Cause: unavailable_review_ref_ancestry
Material-Digest: sha256:ff45a81a9fb4c25de5214f089f9ac6b8ee46fcac0e49644e6d60a2df69d038d4
Verified-Fix: bec83538accb4ff48bbb451afe7084b4399c14ea
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3617296300

Disposition: NOT-A-BUG
Evidence: scripts/orchestration/pr_review_closeout.py:734-756 and scripts/ci/check_pr_merge_readiness.py:615-633 recompute and reject stale live-material seals; docs/review/PR_2162_FIXED_MAPPING.md contains the regenerated Review Material Seal.
Reason: The comment references the superseded squashed head f2c25ed; the repaired live PR graph now retains the material commits, while canonical closeout and merge-readiness validation fail closed on any current stale seal. This closeout regenerates the seal for the live material digest.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#discussion_r3616962234

Disposition: NOT-A-BUG
Evidence: .github/workflows/ci.yml:77 keeps the review-critical selector explicit; tests/test_pgvector_compat.py:374-418 uses exact structural anchors and executable-input canaries.
Reason: A shared constant or broad YAML-parser refactor would widen this dependency compatibility PR without improving the exact fail-closed contract; the brittle ambiguous anchor was fixed narrowly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#pullrequestreview-4730922197

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"authority":"trusted_codex_review_source_unavailability","binding_kind":"seal_context_only","blocking":false,"fallback_required":false,"material_digest":"sha256:ff45a81a9fb4c25de5214f089f9ac6b8ee46fcac0e49644e6d60a2df69d038d4","material_head_sha":"bec83538accb4ff48bbb451afe7084b4399c14ea","quota_body_sha256":"sha256:e39b189a2ed6388c9d919876a2893ca0216a023301e11d788df190b4366991b9","quota_created_at":"2026-07-20T11:18:41Z","quota_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2162#issuecomment-5021643913","review_claim":"none","schema_version":"pulseplate.codex-review-source-unavailability/v1","source":"codex_review","source_degraded":true,"source_status":"usage_limit_reached","status":"tooling_unavailable"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:e15d188b548036dc4252b8f8b1e1d65b42b9b9e59b433a5219928083b6c79cfd","findings_sha256":"sha256:e42fa0f4bd94e5376a12e37960f46c11f7f75a4478ec306fd632b83ebb5a36e9","work_ledger_sha256":"sha256:5b31d37c402673d6775edb893fa04fb0587a113673e701a2dae78c8f51fa85e6"},"authority":"human_asserted_content_receipt","base_revision":"c325489612809e0c9dfc8bb300aca606a8bf7c49","coverage_completeness":"complete","findings_count":0,"head_revision":"bec83538accb4ff48bbb451afe7084b4399c14ea","manifest_sha256":"sha256:0643e3dacb43ef988c948ae5834a153d0ef0b6f2dcb6ba56995649fdcdfbbb1c","producer":{"name":"codex-security-plugin","version":"0.1.11"},"scan_id":"c3c5cd25-602a-4105-90a4-6ac356ead74b","snapshot_digest":"codex-security-snapshot/v1:sha256:1a3db1aef0dc1fdd583d4fbd075e8c2a33c9c09e56fec88786e4c8307a370e6f"},"material":{"base_ref_oid":"c325489612809e0c9dfc8bb300aca606a8bf7c49","digest":"sha256:ff45a81a9fb4c25de5214f089f9ac6b8ee46fcac0e49644e6d60a2df69d038d4","material_head_sha":"bec83538accb4ff48bbb451afe7084b4399c14ea","merge_base_sha":"c325489612809e0c9dfc8bb300aca606a8bf7c49","policy_version":"pulseplate.material-classification/v1"},"pr_number":2162,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
