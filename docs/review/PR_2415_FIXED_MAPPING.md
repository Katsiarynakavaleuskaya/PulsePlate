# PR 2415 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/665203fc9ff5.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/ops03a-oracle-v2.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 65dd429168b9ce560cc5008e885d30aaccd3cdf6
Evidence: scripts/ops/staging_runtime_diagnostics.py:164-170,571-577; tests/test_staging_runtime_diagnostics.py:788-858; exact-image verify-full negative proof in owner-only native-exact-image-proof.md
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#discussion_r4093692871 -> 65dd429168b9ce560cc5008e885d30aaccd3cdf6

Disposition: FIXED
Commit: 65dd429168b9ce560cc5008e885d30aaccd3cdf6
Evidence: scripts/ops/staging_runtime_diagnostics.py:105-111; tests/test_staging_runtime_diagnostics.py:720-735,739-763,798-839; fake driver is passed directly and sys.modules is unchanged
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#discussion_r4093736120 -> 65dd429168b9ce560cc5008e885d30aaccd3cdf6

Disposition: FIXED
Commit: 65dd429168b9ce560cc5008e885d30aaccd3cdf6
Evidence: scripts/ops/staging_runtime_diagnostics.py:164-170,571-577; tests/test_staging_runtime_diagnostics.py:788-858; unreachable DB_TLS_FAILED removed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#pullrequestreview-5304534305 -> 65dd429168b9ce560cc5008e885d30aaccd3cdf6

Disposition: FIXED
Commit: 65dd429168b9ce560cc5008e885d30aaccd3cdf6
Evidence: scripts/ops/staging_runtime_diagnostics.py:105-111; tests/test_staging_runtime_diagnostics.py:720-735,739-763; no sys.modules mutation
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#pullrequestreview-5304586549 -> 65dd429168b9ce560cc5008e885d30aaccd3cdf6

Disposition: NOT-A-BUG
Evidence: scripts/ops/staging_runtime_diagnostics.py:164-170; tests/test_staging_runtime_diagnostics.py:798-839; docs/deploy/OPERATIONAL_SIGNALS.md:530-543; native-exact-image-proof.md:23-31; Psycopg official errors API
Reason: DB_AUTH_FAILED requires an observed class-28 SQLSTATE; absent SQLSTATE is conservatively DB_CONNECTION_FAILED and no exhaustive auth classification is promised
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#discussion_r4096994152

Disposition: NOT-A-BUG
Evidence: scripts/ops/staging_runtime_diagnostics.py:164-170; tests/test_staging_runtime_diagnostics.py:798-839; native wrong-password result observed sqlstate null
Reason: The code uses class 28 only when supplied by Psycopg and otherwise keeps the cause generic; removing that finite signal would discard correct evidence
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2415#pullrequestreview-5308437531

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:685ea9675cab81fcbf5d7295d96b8ebc166cd7d0cfdaa702506cfce081813817","material_head_sha":"57a0c644c7816cb73b70063ebebdd0e8147a6a36","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"b9f2818684fec734fabdaa7ab582d87809c46181","blocking":false,"head_revision":"57a0c644c7816cb73b70063ebebdd0e8147a6a36","material_digest":"sha256:685ea9675cab81fcbf5d7295d96b8ebc166cd7d0cfdaa702506cfce081813817","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"b9f2818684fec734fabdaa7ab582d87809c46181","digest":"sha256:685ea9675cab81fcbf5d7295d96b8ebc166cd7d0cfdaa702506cfce081813817","material_head_sha":"57a0c644c7816cb73b70063ebebdd0e8147a6a36","merge_base_sha":"b9f2818684fec734fabdaa7ab582d87809c46181","policy_version":"pulseplate.material-classification/v1"},"pr_number":2415,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:685ea9675cab81fcbf5d7295d96b8ebc166cd7d0cfdaa702506cfce081813817","material_head_sha":"57a0c644c7816cb73b70063ebebdd0e8147a6a36","report_payload":{"actionable_findings_count":0,"base_ref_oid":"b9f2818684fec734fabdaa7ab582d87809c46181","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/665203fc9ff5.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"665203fc9ff5"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1813 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-24T19:55:26Z","material_digest":"sha256:685ea9675cab81fcbf5d7295d96b8ebc166cd7d0cfdaa702506cfce081813817","material_head_sha":"57a0c644c7816cb73b70063ebebdd0e8147a6a36","merge_base_sha":"b9f2818684fec734fabdaa7ab582d87809c46181","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"b9f2818684fec734fabdaa7ab582d87809c46181..57a0c644c7816cb73b70063ebebdd0e8147a6a36","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2415_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".cursor/agents/dev-operator.md",".github/workflows/ci.yml","docs/deploy/OPERATIONAL_SIGNALS.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/ci/ci_risk_profile.py","scripts/ops/staging_runtime_diagnostics.py","tests/test_ci_risk_profile.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_staging_runtime_diagnostics.py"],"diff_summary":{"additions":1793,"changed_lines":1813,"deletions":20,"files":9},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":[".cursor/agents/AGENTS.md","AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:4083bac2012717547b968feb454385b3bd2f6e7d53244114b3925d72952529e7","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
