# PR 2191 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/7d018e371f42.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/python-31314-aux-workflows-sourcery-fix-oracle.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 467b337d177a5b5adce00460baab442170251aae
Evidence: tests/test_runtime_toolchain_alignment.py:180 compares exact Counter multisets; 31 focused tests passed on the fix head
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#discussion_r3668857477 -> 467b337d177a5b5adce00460baab442170251aae

Disposition: FIXED
Commit: 467b337d177a5b5adce00460baab442170251aae
Evidence: The review-level order-coupling actionable is fixed at tests/test_runtime_toolchain_alignment.py:180; its constant suggestion is separately dispositioned on discussion_r3668857484
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#pullrequestreview-4801431852 -> 467b337d177a5b5adce00460baab442170251aae

Disposition: NOT-A-BUG
Evidence: tests/test_runtime_toolchain_alignment.py:181 is the independent literal 3.13.14 oracle; tests/runtime_toolchain_versions.py:3 remains canonical until PR-1b
Reason: A temporary AUXILIARY_PYTHON constant would add indirection and a second temporary version source instead of detecting workflow-oracle drift
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#discussion_r3668857484

Disposition: NOT-A-BUG
Evidence: Cursor states that Bugbot is disabled and performed no review
Reason: This is an account upsell/status notice with no repository finding or requested code change
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#issuecomment-5109145088

Disposition: NOT-A-BUG
Evidence: The Sourcery guide describes the three-file diff and offers tool usage tips; the later actionable review is mapped separately
Reason: This guide contains no independent defect request
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#issuecomment-5109146610

Disposition: NOT-A-BUG
Evidence: The current CodeRabbit summary explicitly reports no actionable comments and lists five passed pre-merge review checks
Reason: Walkthrough, suggested label, and optional finishing-touch controls are informational, not code defects
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2191#issuecomment-5109150100

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:2f269b85909d38d40e06c92d3920ec762241f5393d7fe991eb9002fd1f19872e","material_head_sha":"467b337d177a5b5adce00460baab442170251aae","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"27780b40516b0f649e377cf0ba91dcbd281fa74d","blocking":false,"head_revision":"467b337d177a5b5adce00460baab442170251aae","material_digest":"sha256:2f269b85909d38d40e06c92d3920ec762241f5393d7fe991eb9002fd1f19872e","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"27780b40516b0f649e377cf0ba91dcbd281fa74d","digest":"sha256:2f269b85909d38d40e06c92d3920ec762241f5393d7fe991eb9002fd1f19872e","material_head_sha":"467b337d177a5b5adce00460baab442170251aae","merge_base_sha":"27780b40516b0f649e377cf0ba91dcbd281fa74d","policy_version":"pulseplate.material-classification/v1"},"pr_number":2191,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":0,"material_digest":"sha256:2f269b85909d38d40e06c92d3920ec762241f5393d7fe991eb9002fd1f19872e","material_head_sha":"467b337d177a5b5adce00460baab442170251aae","report_payload":{"actionable_findings_count":0,"base_ref_oid":"27780b40516b0f649e377cf0ba91dcbd281fa74d","calibration":{"case_labels":["clean-context","review-source-degraded"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":""},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[],"findings_count":0,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast"],"generated_at_utc":"2026-07-28T20:23:23Z","material_digest":"sha256:2f269b85909d38d40e06c92d3920ec762241f5393d7fe991eb9002fd1f19872e","material_head_sha":"467b337d177a5b5adce00460baab442170251aae","merge_base_sha":"27780b40516b0f649e377cf0ba91dcbd281fa74d","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"27780b40516b0f649e377cf0ba91dcbd281fa74d..467b337d177a5b5adce00460baab442170251aae","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2191_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter has no deterministic findings from the supplied context."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/nightly-tests.yml",".github/workflows/rag-release-gates.yml","tests/test_runtime_toolchain_alignment.py"],"diff_summary":{"additions":24,"changed_lines":28,"deletions":4,"files":3},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:e272fd2d1ed1be6be7e3947e3b780ae651c7a63e5043bf4c0e9ae7139550068c","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
