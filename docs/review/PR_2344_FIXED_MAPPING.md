# PR 2344 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/7b87d599d0e7.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pr-evidence-sidecar-v1-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8cf865d7a428e14fb0f965112a4a5075ba080474
Evidence: scripts/orchestration/pr_evidence_sidecar.py:87; tests/test_pr_evidence_sidecar.py:254; targeted pytest passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2344#discussion_r3871778636 -> 8cf865d7a428e14fb0f965112a4a5075ba080474

Disposition: FIXED
Commit: 3aa1c346bef8fcdd8f488aa9913eab7d3ad72206
Evidence: docs/orchestration/PR_EVIDENCE_SIDECAR_V1.md:41,119; scripts/orchestration/pr_evidence_sidecar.py:911; focused suite 111 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2344#discussion_r3873290517 -> 3aa1c346bef8fcdd8f488aa9913eab7d3ad72206

Disposition: FIXED
Commit: 8cf865d7a428e14fb0f965112a4a5075ba080474
Evidence: scripts/orchestration/pr_evidence_sidecar.py:87; tests/test_pr_evidence_sidecar.py:254; targeted pytest passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2344#pullrequestreview-5040863806 -> 8cf865d7a428e14fb0f965112a4a5075ba080474

Disposition: FIXED
Commit: 3aa1c346bef8fcdd8f488aa9913eab7d3ad72206
Evidence: docs/orchestration/PR_EVIDENCE_SIDECAR_V1.md:41,119; scripts/orchestration/pr_evidence_sidecar.py:911; focused suite 111 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2344#pullrequestreview-5042685214 -> 3aa1c346bef8fcdd8f488aa9913eab7d3ad72206

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:cc107a8f9406c42751c42d171ea71412139f5c0afae15d0cbf493b58c247f149","material_head_sha":"3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"57a80c130f4ae7317b9b905b02fa116551a88076","blocking":false,"head_revision":"3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","material_digest":"sha256:cc107a8f9406c42751c42d171ea71412139f5c0afae15d0cbf493b58c247f149","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"57a80c130f4ae7317b9b905b02fa116551a88076","digest":"sha256:cc107a8f9406c42751c42d171ea71412139f5c0afae15d0cbf493b58c247f149","material_head_sha":"3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","merge_base_sha":"57a80c130f4ae7317b9b905b02fa116551a88076","policy_version":"pulseplate.material-classification/v1"},"pr_number":2344,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:cc107a8f9406c42751c42d171ea71412139f5c0afae15d0cbf493b58c247f149","material_head_sha":"3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","report_payload":{"actionable_findings_count":0,"base_ref_oid":"57a80c130f4ae7317b9b905b02fa116551a88076","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/7b87d599d0e7.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"7b87d599d0e7"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2280 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-08-27T16:23:15Z","material_digest":"sha256:cc107a8f9406c42751c42d171ea71412139f5c0afae15d0cbf493b58c247f149","material_head_sha":"3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","merge_base_sha":"57a80c130f4ae7317b9b905b02fa116551a88076","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"57a80c130f4ae7317b9b905b02fa116551a88076..3aa1c346bef8fcdd8f488aa9913eab7d3ad72206","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2344_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["docs/orchestration/PR_EVIDENCE_SIDECAR_V1.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/AGENTS.md","scripts/orchestration/pr_evidence_sidecar.py","scripts/orchestration/render_codex_start_prompt.py","scripts/orchestration/start_pr_lane.sh","tests/test_pr_evidence_sidecar.py","tests/test_render_codex_start_prompt.py","tests/test_start_pr_lane.py"],"diff_summary":{"additions":2275,"changed_lines":2280,"deletions":5,"files":9},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","docs/orchestration/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:24b5dbc634d96cb4216471010e699be3d3aa7d3b0aa64a491b1838d2d9551312","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
