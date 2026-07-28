# PR 2190 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/87332b3ebbe3.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pr2180-postmerge-test-ownership-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: c8b553bbde010c89025396cf21a7674fe1e15b00
Evidence: Commit c8b553bbde010c89025396cf21a7674fe1e15b00 regenerated the exact-material seal after .coderabbit.yaml changed; the final material cycle is resealed from e7b372dbb15abcc2a035835aa93af18f6ec713ed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#discussion_r3666023217 -> c8b553bbde010c89025396cf21a7674fe1e15b00

Disposition: FIXED
Commit: c8b553bbde010c89025396cf21a7674fe1e15b00
Evidence: Commit c8b553bbde010c89025396cf21a7674fe1e15b00 regenerated the exact-material seal after .coderabbit.yaml changed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#pullrequestreview-4797900048 -> c8b553bbde010c89025396cf21a7674fe1e15b00

Disposition: NOT-A-BUG
Evidence: scripts/orchestration/pr_review_evidence.py:119-127,1846-1868,2137-2166; scripts/orchestration/pr_review_context.py:534-542; tests/test_pr_review_material_seal.py:3336,3636; authenticated pr_review_closeout validate PASS on prior seal
Reason: The embedded report_payload is required, hash-bound canonical seal data; fixed_mapping_artifact unavailable is an expected non-blocking pre-seal source status because final-material self-review precedes mapping generation. Regenerating the same material to remove either field would violate the canonical schema and recreate the closeout loop.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#discussion_r3665775694

Disposition: NOT-A-BUG
Evidence: At c8b553bbde010c89025396cf21a7674fe1e15b00, docs/review/PR_2190_FIXED_MAPPING.md:20 is discussion_r3665775694, the withdrawn CodeRabbit payload finding; the actual reseal finding is discussion_r3666023217 and is separately mapped FIXED to c8b553bbde010c89025396cf21a7674fe1e15b00.
Reason: The review misidentifies the URL on line 20. Its governance concern is satisfied by the separate FIXED mapping for the actual Codex reseal thread.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#discussion_r3666123136

Disposition: NOT-A-BUG
Evidence: tests/test_app_who_targets_fallback.py:38,46-50,57,69-72; app/services/pro_nutrition_targets.py:287; 23 focused tests PASS; exact-head lint, test-pr, security, OpenAPI, coverage, and diff-coverage SUCCESS
Reason: The two explicit TDEE expectations cover distinct fallback branches; callbacks must accept builder(profile), and underscore-prefixed parameters already document intentional non-use, so helper extraction adds coupling while parameter removal breaks required callback arity.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#pullrequestreview-4797379530

Disposition: NOT-A-BUG
Evidence: scripts/orchestration/pr_review_evidence.py:119-127,1846-1868,2137-2166; scripts/orchestration/pr_review_context.py:534-542; tests/test_pr_review_material_seal.py:3336,3636; authenticated pr_review_closeout validate PASS on prior seal
Reason: The embedded report_payload is required, hash-bound canonical seal data; fixed_mapping_artifact unavailable is an expected non-blocking pre-seal source status because final-material self-review precedes mapping generation. Regenerating the same material to remove either field would violate the canonical schema and recreate the closeout loop.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#pullrequestreview-4797585048

Disposition: NOT-A-BUG
Evidence: At c8b553bbde010c89025396cf21a7674fe1e15b00, line 20 is the CodeRabbit payload URL; discussion_r3666023217 is separately mapped FIXED to c8b553bbde010c89025396cf21a7674fe1e15b00.
Reason: The actionable top-level review inherits the inline URL misidentification; the actual reseal finding has post-comment FIXED proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2190#pullrequestreview-4798028590

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:ff8e1cde7eadb8f5bea9f456c2a2c21e2423e98e91e96103b2309cfac11910ad","material_head_sha":"e7b372dbb15abcc2a035835aa93af18f6ec713ed","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"d2a5486409693e67fe677188dab7353428ddea8e","blocking":false,"head_revision":"e7b372dbb15abcc2a035835aa93af18f6ec713ed","material_digest":"sha256:ff8e1cde7eadb8f5bea9f456c2a2c21e2423e98e91e96103b2309cfac11910ad","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"d2a5486409693e67fe677188dab7353428ddea8e","digest":"sha256:ff8e1cde7eadb8f5bea9f456c2a2c21e2423e98e91e96103b2309cfac11910ad","material_head_sha":"e7b372dbb15abcc2a035835aa93af18f6ec713ed","merge_base_sha":"d2a5486409693e67fe677188dab7353428ddea8e","policy_version":"pulseplate.material-classification/v1"},"pr_number":2190,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":0,"material_digest":"sha256:ff8e1cde7eadb8f5bea9f456c2a2c21e2423e98e91e96103b2309cfac11910ad","material_head_sha":"e7b372dbb15abcc2a035835aa93af18f6ec713ed","report_payload":{"actionable_findings_count":0,"base_ref_oid":"d2a5486409693e67fe677188dab7353428ddea8e","calibration":{"case_labels":["clean-context"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/87332b3ebbe3.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"87332b3ebbe3"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[],"findings_count":0,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast"],"generated_at_utc":"2026-07-28T14:18:11Z","material_digest":"sha256:ff8e1cde7eadb8f5bea9f456c2a2c21e2423e98e91e96103b2309cfac11910ad","material_head_sha":"e7b372dbb15abcc2a035835aa93af18f6ec713ed","merge_base_sha":"d2a5486409693e67fe677188dab7353428ddea8e","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"d2a5486409693e67fe677188dab7353428ddea8e..e7b372dbb15abcc2a035835aa93af18f6ec713ed","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2190_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter has no deterministic findings from the supplied context."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".coderabbit.yaml","tests/test_app_key_coverage_clean.py","tests/test_app_who_targets_fallback.py"],"diff_summary":{"additions":7,"changed_lines":19,"deletions":12,"files":3},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:897cf9bdfbddcf6f00bbdc39d050d646f7ada4dd0177a62d80cf814931a25ca6","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
