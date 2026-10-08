# PR 2472 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/5863dc626e15.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/oracle_attachments/77dd91d073dbf3acdf71277fba6f15f7a66e4e0ec708e74e57491acdb31da5f1/result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 4b515f479d4b5816a4e8c8c0696044bf59be012e
Evidence: .github/workflows/cd.yml:1183; tests/test_caddy_deploy_provenance.py:1730; Separate main native job has its own budget, image-scan prerequisite and main-build success dependency.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4193395620 -> 4b515f479d4b5816a4e8c8c0696044bf59be012e

Disposition: FIXED
Commit: 4b515f479d4b5816a4e8c8c0696044bf59be012e
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:440; Corrected conflict75 wording; it is failed, not a PASS receipt.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4193453474 -> 4b515f479d4b5816a4e8c8c0696044bf59be012e

Disposition: FIXED
Commit: 4b515f479d4b5816a4e8c8c0696044bf59be012e
Evidence: scripts/ops/notify_premium_alias_checkpoint_failure.py:72; scripts/ops/notify_premium_alias_checkpoint_failure.py:90; Both builtin and asyncio timeout families preserve cleanup and failure; later253 request bound and native revalidation complement this fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4193453479 -> 4b515f479d4b5816a4e8c8c0696044bf59be012e

Disposition: FIXED
Commit: 253e99afce4c9fab26562767a3627b650ec122ce
Evidence: .github/workflows/ci.yml:758; tests/test_caddy_deploy_provenance.py:1947; One existing PR selector/native executor moved to required lint independently of the backend classifier, with same-runner raw evidence and explicit budgets.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4200864654 -> 253e99afce4c9fab26562767a3627b650ec122ce

Disposition: FIXED
Commit: 1b45371841bc0759fcea3fd7453b91f8432fa1d6
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:451; staged changed-doc guard0; Clarified15 absolute slots spaced60 seconds apart; runtime/event/timeout semantics unchanged. Actual post-comment fixing commit is published and reachable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4204231082 -> 1b45371841bc0759fcea3fd7453b91f8432fa1d6

Disposition: FIXED
Commit: 938e5c67a9c2d9ca616431494fedead8501ceba5
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:414; .github/workflows/ci.yml:758; .github/workflows/cd.yml:1183; .pre-commit-config.yaml:149; Aggregate covers production bootstrap documentation FIX938, routing FIX253 and budget/timeout FIX4b; unavailable-before remains NOT-A-BUG. Generic80-percent docstring metric is not a repository threshold; preserve required pydocstyle/hooks and unchanged coverage producers rather than an unrelated sweep.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#issuecomment-6012835991 -> 938e5c67a9c2d9ca616431494fedead8501ceba5

Disposition: FIXED
Commit: 4b515f479d4b5816a4e8c8c0696044bf59be012e
Evidence: .github/workflows/cd.yml:1183; discussion roots4193395606/4193395615/4193395620; Aggregate independently covers the budget FIX and profile-off/contention NOT-A-BUG cases; false bot Addressed prose is not adopted.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#pullrequestreview-5426063963 -> 4b515f479d4b5816a4e8c8c0696044bf59be012e

Disposition: FIXED
Commit: 4b515f479d4b5816a4e8c8c0696044bf59be012e
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:440; scripts/ops/notify_premium_alias_checkpoint_failure.py:72; .github/workflows/ci.yml:769; Aggregate covers conflict prose, both timeout families and unique PR merge-base selection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#pullrequestreview-5426136176 -> 4b515f479d4b5816a4e8c8c0696044bf59be012e

Disposition: FIXED
Commit: 253e99afce4c9fab26562767a3627b650ec122ce
Evidence: .github/workflows/ci.yml:758; .github/workflows/cd.yml:1204; tests/test_caddy_deploy_provenance.py:1658; Aggregate covers real outer PR routing FIX and independent fail-closed before-lineage NOT-A-BUG.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#pullrequestreview-5435047842 -> 253e99afce4c9fab26562767a3627b650ec122ce

Disposition: FIXED
Commit: 938e5c67a9c2d9ca616431494fedead8501ceba5
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:414; tests/test_deploy_contract_scripts.py:13707; Documented first adoption via reviewed production bundle and later five-file installed prerequisites; missing/symlink/hash admission remains strict before mutation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#pullrequestreview-5437400746 -> 938e5c67a9c2d9ca616431494fedead8501ceba5

Disposition: FIXED
Commit: 1b45371841bc0759fcea3fd7453b91f8432fa1d6
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:451; root4204231082; Independent aggregate carrier for the sole cadence wording finding; actual published fixing commit1b follows the comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#pullrequestreview-5439027557 -> 1b45371841bc0759fcea3fd7453b91f8432fa1d6

Disposition: NOT-A-BUG
Evidence: tests/test_notify_premium_alias_checkpoint_failure.py:1394; failure unit COMPOSE_PROFILES=
Reason: Profile-off keeps delivery default-off and does not prevent explicit exec into the existing running selected Alertmanager; stopped/absent service is rejected.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4193395606

Disposition: NOT-A-BUG
Evidence: deploy/systemd/pulseplate-premium-alias-checkpoint.service.example:8; deploy/systemd/pulseplate-premium-alias-checkpoint.service.example:19
Reason: Accepted contention fails with status75/OnFailure and no PASS receipt; SuccessExitStatus75 would weaken the accepted contract and was not introduced.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4193395615

Disposition: NOT-A-BUG
Evidence: .github/workflows/cd.yml:1204; tests/test_caddy_deploy_provenance.py:1658
Reason: Before-to-head admission intentionally fails closed on unavailable/malformed lineage; a fallback true would conceal an admission error.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2472#discussion_r4200864649

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:ea5c09c73dc33097f04ff7e4fa63bb9634cbc605a2e4f897b6f25e1343bf6319","material_head_sha":"a374440a18d96ebc0dde1ec00cdecc3490803540","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"7744af5cf3919b768a868497ae6d41e46952c484","blocking":false,"head_revision":"a374440a18d96ebc0dde1ec00cdecc3490803540","material_digest":"sha256:ea5c09c73dc33097f04ff7e4fa63bb9634cbc605a2e4f897b6f25e1343bf6319","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"7744af5cf3919b768a868497ae6d41e46952c484","digest":"sha256:ea5c09c73dc33097f04ff7e4fa63bb9634cbc605a2e4f897b6f25e1343bf6319","material_head_sha":"a374440a18d96ebc0dde1ec00cdecc3490803540","merge_base_sha":"7744af5cf3919b768a868497ae6d41e46952c484","policy_version":"pulseplate.material-classification/v1"},"pr_number":2472,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:ea5c09c73dc33097f04ff7e4fa63bb9634cbc605a2e4f897b6f25e1343bf6319","material_head_sha":"a374440a18d96ebc0dde1ec00cdecc3490803540","report_payload":{"actionable_findings_count":0,"base_ref_oid":"7744af5cf3919b768a868497ae6d41e46952c484","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/5863dc626e15.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"5863dc626e15"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 4490 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-10-07T21:33:20Z","material_digest":"sha256:ea5c09c73dc33097f04ff7e4fa63bb9634cbc605a2e4f897b6f25e1343bf6319","material_head_sha":"a374440a18d96ebc0dde1ec00cdecc3490803540","merge_base_sha":"7744af5cf3919b768a868497ae6d41e46952c484","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"7744af5cf3919b768a868497ae6d41e46952c484..a374440a18d96ebc0dde1ec00cdecc3490803540","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2472_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/cd.yml",".github/workflows/ci.yml",".secrets.baseline","deploy/systemd/pulseplate-premium-alias-checkpoint-failure.service.example","deploy/systemd/pulseplate-premium-alias-checkpoint.service.example","deploy/systemd/pulseplate-premium-alias-checkpoint.timer.example","docs/deploy/OPERATIONAL_SIGNALS.md","docs/roadmap/BACKLOG_LEDGER.md","docs/security/CVE-2026-84445-alertmanager.md","scripts/AGENTS.md","scripts/deploy.sh","scripts/deploy_production.sh","scripts/ops/notify_premium_alias_checkpoint_failure.py","scripts/verify_premium_alias_telemetry.py","tests/test_caddy_deploy_provenance.py","tests/test_cd_attestation_workflow_contract.py","tests/test_cd_workflow_production_deploy_gate.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_deploy_contract_scripts.py","tests/test_notify_premium_alias_checkpoint_failure.py","tests/test_premium_alias_telemetry_verifier.py","tests/test_release_control_plane_ci_gate.py","tests/test_runtime_toolchain_alignment.py"],"diff_summary":{"additions":4318,"changed_lines":4490,"deletions":172,"files":23},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:060819dd556c1249923d81adb390c9a24101444bb172773f2db21e9ecbd960fa","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
