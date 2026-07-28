# PR 2180 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/0bb0e13ca903.json`

## Experiment Runner Evidence
Not applicable: Experiment Runner did not materially contribute.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 70a779600461b9bdaf824e452f3cfd38e3785265
Evidence: app/services/pro_nutrition_bmr.py:178 and tests/test_premium_bmr_api.py:220
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#discussion_r3650016744 -> 70a779600461b9bdaf824e452f3cfd38e3785265

Disposition: FIXED
Commit: 70a779600461b9bdaf824e452f3cfd38e3785265
Evidence: tests/test_premium_bmr_api.py:622 and tests/test_premium_bmr_api.py:686
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#discussion_r3650016746 -> 70a779600461b9bdaf824e452f3cfd38e3785265

Disposition: FIXED
Commit: 70a779600461b9bdaf824e452f3cfd38e3785265
Evidence: tests/test_premium_bmr_api.py:805 and make validate-changed (213 passed)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#discussion_r3650016748 -> 70a779600461b9bdaf824e452f3cfd38e3785265

Disposition: FIXED
Commit: cdca94984afa60109697e01b801fa3b18b85a124
Evidence: app/services/pro_nutrition_bmr.py:25 and app/services/pro_nutrition_bmr.py:97; request invariants remain schema-owned and service hard-coded language/activity/sex sets were removed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#pullrequestreview-4774181217 -> cdca94984afa60109697e01b801fa3b18b85a124

Disposition: FIXED
Commit: 70a779600461b9bdaf824e452f3cfd38e3785265
Evidence: app/services/pro_nutrition_bmr.py:178; tests/test_premium_bmr_api.py:805; tests/test_premium_bmr_api.py:871; tests/test_route_family_bootstrap.py:279; make validate-changed (213 passed)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#pullrequestreview-4779097811 -> 70a779600461b9bdaf824e452f3cfd38e3785265

Disposition: FIXED
Commit: e6c72806c6d7263fd162e433aa1ad9931449e387
Evidence: docs/roadmap/BACKLOG_LEDGER.md:6818; docs Phase1 passed; make validate-changed passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2180#pullrequestreview-4793716930 -> e6c72806c6d7263fd162e433aa1ad9931449e387

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:e633f82b5a0c26468a1802fa635ecd5b24ae1cd4ce443b0336f0112755b7eb34","material_head_sha":"e6c72806c6d7263fd162e433aa1ad9931449e387","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"f337ab1e67750aa593cd64d43cb063aeb5f346de","blocking":false,"head_revision":"e6c72806c6d7263fd162e433aa1ad9931449e387","material_digest":"sha256:e633f82b5a0c26468a1802fa635ecd5b24ae1cd4ce443b0336f0112755b7eb34","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"f337ab1e67750aa593cd64d43cb063aeb5f346de","digest":"sha256:e633f82b5a0c26468a1802fa635ecd5b24ae1cd4ce443b0336f0112755b7eb34","material_head_sha":"e6c72806c6d7263fd162e433aa1ad9931449e387","merge_base_sha":"f337ab1e67750aa593cd64d43cb063aeb5f346de","policy_version":"pulseplate.material-classification/v1"},"pr_number":2180,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:e633f82b5a0c26468a1802fa635ecd5b24ae1cd4ce443b0336f0112755b7eb34","material_head_sha":"e6c72806c6d7263fd162e433aa1ad9931449e387","report_payload":{"actionable_findings_count":0,"base_ref_oid":"f337ab1e67750aa593cd64d43cb063aeb5f346de","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/0bb0e13ca903.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"0bb0e13ca903"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2834 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-07-28T04:50:34Z","material_digest":"sha256:e633f82b5a0c26468a1802fa635ecd5b24ae1cd4ce443b0336f0112755b7eb34","material_head_sha":"e6c72806c6d7263fd162e433aa1ad9931449e387","merge_base_sha":"f337ab1e67750aa593cd64d43cb063aeb5f346de","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"f337ab1e67750aa593cd64d43cb063aeb5f346de..e6c72806c6d7263fd162e433aa1ad9931449e387","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2180_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".secrets.baseline","app/AGENTS.md","app/http_error_details.py","app/routers/legacy_premium_nutrition.py","app/schemas/bmr.py","app/services/pro_nutrition_bmr.py","app/utils/feature_flags.py","app/utils/nutrition_wrappers.py","docs/architecture/LEGACY_COMPATIBILITY_SEAM.md","docs/contracts/PRODUCT_TIER_MAP.md","docs/roadmap/BACKLOG_LEDGER.md","legacy_app.py","tests/AGENTS.md","tests/edges/test_legacy_premium_nutrition_registration_bootstrap.py","tests/test_premium_bmr_api.py","tests/test_route_family_bootstrap.py"],"diff_summary":{"additions":1141,"changed_lines":2834,"deletions":1693,"files":16},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","app/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:464bc4825c862e4eb323bb887551db6a003e7c7e407a6e66d7023b3a69748bf5","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
