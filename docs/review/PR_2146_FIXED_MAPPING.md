# PR 2146 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/05116ce4384e.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pyarrow25-offline-data-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 17beb0e59ba6564f00fb7416f4426815cf6dd2ba
Evidence: tests/test_python_supply_chain_controls.py:955 asserts the 25.0.0 floor, lines 958-961 enforce the <26.0.0 ceiling, and focused supply-chain pytest passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2146#discussion_r3608655570 -> 17beb0e59ba6564f00fb7416f4426815cf6dd2ba

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"review_commit_ref":"17beb0e59ba6564f00fb7416f4426815cf6dd2ba","review_commit_ref_kind":"repository_commit","review_reference":"https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2146#issuecomment-5012446561","reviewed_material_digest":"sha256:dbd27d0dd58f2ed5e9b56e3f46189c139480963cb46a984adcd881af620d4a8e","status":"completed"},"codex_security":{"artifacts":{"coverage_sha256":"sha256:08438dae801c51ea63036dd3f1b317e387a706d0c3b664a0fe2afeea01ab9bf5","findings_sha256":"sha256:6d7cfc2a93762e5889bb940e12cf40df1058d85c3533aa9da409da9428b6b4c7","work_ledger_sha256":"sha256:a62f3ae913eae94e29e6c4c2876aea709167fb37cb9cc15d5e30b7f68ee95568"},"authority":"human_asserted_content_receipt","base_revision":"bf31be9b3d015414c0b11917ff940146b2c1f81a","coverage_completeness":"complete","findings_count":0,"head_revision":"17beb0e59ba6564f00fb7416f4426815cf6dd2ba","manifest_sha256":"sha256:1073c65a3061dd114d84099a0431facc2af4da515f0e01d3667cc6f03373444c","producer":{"name":"codex-security-plugin","version":"0.1.11"},"scan_id":"657538e9-efb7-4342-8799-60cb64a40e70","snapshot_digest":"codex-security-snapshot/v1:sha256:d5220767b096f97f4250ce7b3f53e8245f7cdd2447a9013fc5ebf1d313ab8690"},"material":{"base_ref_oid":"bf31be9b3d015414c0b11917ff940146b2c1f81a","digest":"sha256:dbd27d0dd58f2ed5e9b56e3f46189c139480963cb46a984adcd881af620d4a8e","material_head_sha":"17beb0e59ba6564f00fb7416f4426815cf6dd2ba","merge_base_sha":"bf31be9b3d015414c0b11917ff940146b2c1f81a","policy_version":"pulseplate.material-classification/v1"},"pr_number":2146,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1"}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
