# PR 2249 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/c0b321a88857.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pilot-b3-exact-context-compaction-head172ca2-final.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 9eaa4e69ee008b594ac3d4a3548bf035ae5580f4
Evidence: tests/test_rag_context_compaction.py:26-33 proves a fresh list for empty input; focused helper suite passed 6 tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3745984356 -> 9eaa4e69ee008b594ac3d4a3548bf035ae5580f4

Disposition: FIXED
Commit: f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f
Evidence: core/rag/orchestration.py:458-469 preserves an upstream degraded reason; parameterized rollback coverage is in tests/test_rag_orchestration.py:1695-1755.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3745996967 -> f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f

Disposition: FIXED
Commit: f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f
Evidence: core/rag/orchestration.py:617-627 forwards observed chunks_compacted through late non-RAG recovery; the formatter-exception regression test passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3745996983 -> f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f

Disposition: FIXED
Commit: f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f
Evidence: tests/test_philosophy_validation_integration.py:403-408 asserts JSON Content-Type before resp.json; focused HTTP matrix passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3745996989 -> f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f

Disposition: FIXED
Commit: f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f
Evidence: First post-comment material descendant contains tests/test_rag_context_compaction.py:26-33 fresh-list proof and passed the full four-suite focused rerun.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3745997007 -> f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f

Disposition: FIXED
Commit: f2b57937ebf786950b216b4994f1712a79874050
Evidence: scripts/evals/run_rag_release_gates.py:896-910 forwards the request-time compaction flag; tests/test_rag_release_gates_runner.py:243-299 proves true, false, and absent states.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3746006788 -> f2b57937ebf786950b216b4994f1712a79874050

Disposition: FIXED
Commit: f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f
Evidence: core/rag/orchestration.py:458-469 assigns POST_RETRIEVAL only when no prior reason exists; the two-case regression matrix passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3746006790 -> f02fa458911a69f21effb1e4fbd5cb6f0e3bfa0f

Disposition: FIXED
Commit: fcb40041d1482377467463bbfd145deda858a848
Evidence: tests/test_rag_release_gates_runner.py:243-299 proves explicit true, explicit false, and absent/default-off forwarding on one loaded runner.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#discussion_r3746060773 -> fcb40041d1482377467463bbfd145deda858a848

Disposition: FIXED
Commit: 9eaa4e69ee008b594ac3d4a3548bf035ae5580f4
Evidence: The review's sole actionable child is fixed at tests/test_rag_context_compaction.py:26-33 and mapped separately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#pullrequestreview-4893105916 -> 9eaa4e69ee008b594ac3d4a3548bf035ae5580f4

Disposition: FIXED
Commit: fcb40041d1482377467463bbfd145deda858a848
Evidence: The review's sole actionable child is closed by tests/test_rag_release_gates_runner.py:289-299 and mapped separately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#pullrequestreview-4893179649 -> fcb40041d1482377467463bbfd145deda858a848

Disposition: NOT-A-BUG
Evidence: Every changed production callable in core/rag/context_compaction.py and the touched flag/eval seams has a docstring; repo pydocstyle is manual and all required narrow hooks pass.
Reason: The external 44 percent warning includes test-callable coverage and is not the repository docstring contract; adding decorative test docstrings would not improve the runtime invariant. Provider rate-limit text remains no-claim and non-blocking.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#issuecomment-5234907457

Disposition: NOT-A-BUG
Evidence: All four actionable inline children are separately mapped FIXED; rg shows _is_exact_compaction_result has one orchestration consumer and all helper behavior is covered.
Reason: The remaining public-export nitpick would widen a deliberately private defensive postcondition into a reusable API without another consumer or business invariant.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#pullrequestreview-4893119698

Disposition: NOT-A-BUG
Evidence: The generic top-level review adds no independent finding; its two inline findings are separately mapped FIXED to f2b57937 and f02fa458.
Reason: This aggregation review has no separate actionable beyond its mapped child threads.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2249#pullrequestreview-4893132707

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:7d4a38920f1dee883ec872340920669140921961c402adab76b8210eb74486ea","material_head_sha":"172ca23b2799f9faa723eca13f5699503f66a5f1","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4","blocking":false,"head_revision":"172ca23b2799f9faa723eca13f5699503f66a5f1","material_digest":"sha256:7d4a38920f1dee883ec872340920669140921961c402adab76b8210eb74486ea","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4","digest":"sha256:7d4a38920f1dee883ec872340920669140921961c402adab76b8210eb74486ea","material_head_sha":"172ca23b2799f9faa723eca13f5699503f66a5f1","merge_base_sha":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4","policy_version":"pulseplate.material-classification/v1"},"pr_number":2249,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:7d4a38920f1dee883ec872340920669140921961c402adab76b8210eb74486ea","material_head_sha":"172ca23b2799f9faa723eca13f5699503f66a5f1","report_payload":{"actionable_findings_count":0,"base_ref_oid":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/c0b321a88857.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"c0b321a88857"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 919 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-08-10T02:43:47Z","material_digest":"sha256:7d4a38920f1dee883ec872340920669140921961c402adab76b8210eb74486ea","material_head_sha":"172ca23b2799f9faa723eca13f5699503f66a5f1","merge_base_sha":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"6a8aabc4b8a3f27b1a3eb363276d6498dc33ada4..172ca23b2799f9faa723eca13f5699503f66a5f1","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2249_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".env.example","app/services/insight_runtime.py","app/utils/feature_flags.py","core/rag/context_compaction.py","core/rag/orchestration.py","docs/contracts/RAG_CONTRACT.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/evals/run_rag_release_gates.py","tests/test_app_insight_runtime.py","tests/test_philosophy_validation_integration.py","tests/test_rag_context_compaction.py","tests/test_rag_orchestration.py","tests/test_rag_release_gates_runner.py"],"diff_summary":{"additions":883,"changed_lines":919,"deletions":36,"files":13},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","app/AGENTS.md","core/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:21cb39f5e293b9af22ca858e0ca21748d9ac03389df58eeb4254639ad300467d","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
