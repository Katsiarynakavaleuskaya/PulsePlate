# PR 2209 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/insight-schema-adapter-post-open-2411a6a3b.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/insight-schema-adapter-exp-42a0d5f0988b-main-a4e144-dispatch-clean.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 374daa79aaf5d29691f329bda55566319894847f
Evidence: tests/test_insight_ownership.py:22-223 replaces the self-matching regex with a finite AST ownership visitor; tests/test_insight_ownership.py:324-335 scans the complete tests tree.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#discussion_r3686695919 -> 374daa79aaf5d29691f329bda55566319894847f

Disposition: FIXED
Commit: 4791ebefb520240d9800a38658f4d446aae1e24c
Evidence: app/services/insight_compat.py:66-78 returns the service result through a typed InsightResponse local without cast.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#discussion_r3686730384 -> 4791ebefb520240d9800a38658f4d446aae1e24c

Disposition: FIXED
Commit: 4791ebefb520240d9800a38658f4d446aae1e24c
Evidence: docs/contracts/RAG_CONTRACT.md:37-53 includes the required non-empty provider field in the canonical InsightResponse example.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#discussion_r3686730409 -> 4791ebefb520240d9800a38658f4d446aae1e24c

Disposition: FIXED
Commit: 374daa79aaf5d29691f329bda55566319894847f
Evidence: tests/test_insight_ownership.py:22-39 centralizes the finite adapter-owned symbols and compatibility allowlist; app/AGENTS.md:376-389 documents the canonical private compatibility seams.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#pullrequestreview-4823767016 -> 374daa79aaf5d29691f329bda55566319894847f

Disposition: FIXED
Commit: 4791ebefb520240d9800a38658f4d446aae1e24c
Evidence: app/services/insight_compat.py:66-78 and docs/contracts/RAG_CONTRACT.md:37-53 implement both actionable review items; focused tests and exact-head CI are required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#pullrequestreview-4823807306 -> 4791ebefb520240d9800a38658f4d446aae1e24c

Disposition: FIXED
Commit: 537eee595002e2e362c2185ff5161b5180abde88
Evidence: tests/test_insight_ownership.py:153-171 models one-Name Assign and AnnAssign; tests/test_insight_ownership.py:238-253 fail-closes tuple/list carriers; tests/AGENTS.md:73-82 records the finite grammar.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#pullrequestreview-4823962686 -> 537eee595002e2e362c2185ff5161b5180abde88

Disposition: NOT-A-BUG
Evidence: Exact-head CI run 30603339411 passes lint 91070629571, test-pr 91070629593, OpenAPI 91070629548, security 91070629775, coverage-pr 91073827448, and diff-coverage 91073827460 at the required 97 percent; only job 91071129542 fails because the canonical mapping is intentionally absent before closeout.
Reason: The current CodeRabbit update was rate-limited and posted no new inline finding. Its docstring/test buttons are optional heuristics, while the compatibility functions are documented and every trusted repository technical gate passes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#issuecomment-5136930625

Disposition: NOT-A-BUG
Evidence: Current exact-head CI diff-coverage job 91073827460 passes the repository threshold at 97 percent for material head 2411a6a3b39499848078eae3762868549fc1b96f.
Reason: The Codecov comment was generated before later coverage and scope-simplification commits and is stale for the frozen exact head; the trusted repository diff-coverage gate is current and passing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2209#issuecomment-5137869457

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:80e73d9d37e57e7d917515e482cd0c4a9309114c321604a1ea40b797d4e0dbec","material_head_sha":"2411a6a3b39499848078eae3762868549fc1b96f","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"a4e144421e1d811850ac81a1efa7948fd5d85500","blocking":false,"head_revision":"2411a6a3b39499848078eae3762868549fc1b96f","material_digest":"sha256:80e73d9d37e57e7d917515e482cd0c4a9309114c321604a1ea40b797d4e0dbec","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"a4e144421e1d811850ac81a1efa7948fd5d85500","digest":"sha256:80e73d9d37e57e7d917515e482cd0c4a9309114c321604a1ea40b797d4e0dbec","material_head_sha":"2411a6a3b39499848078eae3762868549fc1b96f","merge_base_sha":"a4e144421e1d811850ac81a1efa7948fd5d85500","policy_version":"pulseplate.material-classification/v1"},"pr_number":2209,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:80e73d9d37e57e7d917515e482cd0c4a9309114c321604a1ea40b797d4e0dbec","material_head_sha":"2411a6a3b39499848078eae3762868549fc1b96f","report_payload":{"actionable_findings_count":0,"base_ref_oid":"a4e144421e1d811850ac81a1efa7948fd5d85500","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/insight-schema-adapter-post-open-2411a6a3b.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"595b2f86366b"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1176 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-07-31T04:13:10Z","material_digest":"sha256:80e73d9d37e57e7d917515e482cd0c4a9309114c321604a1ea40b797d4e0dbec","material_head_sha":"2411a6a3b39499848078eae3762868549fc1b96f","merge_base_sha":"a4e144421e1d811850ac81a1efa7948fd5d85500","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"a4e144421e1d811850ac81a1efa7948fd5d85500..2411a6a3b39499848078eae3762868549fc1b96f","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2209_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["app/AGENTS.md","app/schemas/insight.py","app/services/insight_application_service.py","app/services/insight_compat.py","docs/architecture/LEGACY_COMPATIBILITY_SEAM.md","docs/contracts/RAG_CONTRACT.md","legacy_app.py","tests/AGENTS.md","tests/test_api.py","tests/test_app_extended_coverage.py","tests/test_insight_error_hygiene.py","tests/test_insight_ownership.py","tests/test_insight_rag_response_fields.py","tests/test_insight_vip_guard_api.py","tests/test_insight_vip_monthly_quota_api.py","tests/test_legacy_app_diff_coverage.py","tests/test_legacy_insight_router.py","tests/test_rag_vector_feature_flag_guard.py","tests/test_targeted_coverage_boost.py"],"diff_summary":{"additions":784,"changed_lines":1176,"deletions":392,"files":19},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","app/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:0ed33696310d363558f71a38647ea3b81991a69a10c13e7fe14af319826d6e05","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
