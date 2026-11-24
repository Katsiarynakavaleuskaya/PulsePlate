# PR 2504 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/4bb4c27eb9b5.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/oracle_attachments/225d4c222325548c1939a5eedb4c1a58877ad3f3ec35f35799405eae4b9407f6/result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: docs/security/CVE-2026-84445-alertmanager.md:1044 documents the shared 2 GiB capture budget and 992 MiB example; tests/test_docker_workflow_build_path_contract.py:15514 tests equality and one-over cases.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4679557393 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: scripts/ci/fetch_docker_source_artifacts.py:4159 budgets both devices, capture allocation and the second ZIP copy; tests/test_docker_workflow_build_path_contract.py:15514 exercises same/separate volumes and post-capture rechecks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4679557404 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: tests/test_docker_workflow_build_path_contract.py:15444 checks native finalization separately from the primary exception, verifies the diagnostic footer bytes and distinguishes earlier retention failures.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4679557409 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: scripts/ci/fetch_docker_source_artifacts.py:2899 shortened the cited over-length docstring in 5069412b; the separately named test fixture has no over-length receipt-field literal; Sourcery marked the root addressed on W3 and the W3 all-files pre-commit log records Black success.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4679985894 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: 3adf47418ac5525a8e2747888440ddb3e9768005
Evidence: scripts/ci/fetch_docker_source_artifacts.py:7881 accepts the full 65558-byte stdlib read window; tests/test_docker_workflow_build_path_contract.py:7845 exercises a large valid commented ZIP under the recorded interpreter matrix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4681287446 -> 3adf47418ac5525a8e2747888440ddb3e9768005

Disposition: FIXED
Commit: b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382
Evidence: tests/test_docker_workflow_build_path_contract.py::test_alertmanager_H_artifact_transport_keeps_C_acceptance_independent now routes successful-stderr through GitHubRead.raw and checks subprocess stdout, stderr, hashes, the exact combined allowance and the destination bytes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157162 -> b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382

Disposition: FIXED
Commit: b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382
Evidence: tests/test_docker_workflow_build_path_contract.py::test_am_candidate_writer_matches_its_footer_and_directory_domain checks the complete decoded file and directory rows against the known fixture.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157171 -> b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: docs/security/CVE-2026-84445-alertmanager.md:1044 and scripts/ci/fetch_docker_source_artifacts.py:4159 address both budget findings; tests/test_docker_workflow_build_path_contract.py:7693 verifies bounded reads of large deflated members and :15444 verifies distinct finalizer/footer outcomes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#pullrequestreview-6038671554 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: 5069412b4c992277588e6688207e4dc76adab772
Evidence: scripts/ci/fetch_docker_source_artifacts.py:2899 shortened the sole located over-length docstring in the cited context; the separately named test fixture has no over-length receipt-field literal; W3 all-files pre-commit records Black success.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#pullrequestreview-6039200518 -> 5069412b4c992277588e6688207e4dc76adab772

Disposition: FIXED
Commit: b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382
Evidence: Both cited test gaps are corrected in tests/test_docker_workflow_build_path_contract.py. The four separate inline dispositions document combined capture bounds, classic ZIP end location and single report accounting.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#pullrequestreview-6044434296 -> b6dfc3f14a8ac67e7ccd9959a7dff467c1d49382

Disposition: NOT-A-BUG
Evidence: scripts/ci/prometheus_source_image.py:5337 bounds combined observed stdout and stderr before persistence. scripts/ci/fetch_docker_source_artifacts.py:4172 bounds that capture by evidence-room minus overhead; :4179 rejects mismatched size before creating the destination.
Reason: Even an unexpected successful stdout body consumes at most the reserved combined capture. The second file is created only after exact size and digest verification and a fresh capacity check.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157124

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:8204; tests/test_docker_workflow_build_path_contract.py::test_am_commented_receipt_accepts_full_stdlib_end_record_search; CPython 3.11.15/3.12.7/3.13.14 classic EOCD readback.
Reason: On the supported CPython versions the classic _EndRecData result has a comment at index 8 and an integer end-record file location at index 9 (the last field). Real classic ZIP reads with and without comments succeeded.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157133

Disposition: NOT-A-BUG
Evidence: docs/security/CVE-2026-84445-alertmanager.md:1046 and scripts/ci/prometheus_source_image.py:5337; tests/test_prometheus_source_image.py::test_public_package_inventory_real_capture_combined_stream_bound_and_cleanup.
Reason: The published budget applies to combined stdout and stderr. A diagnostic fits only with remaining capacity; at the exact combined boundary an additional byte must be rejected.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157146

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:8005 and :8101; candidate-observation.json is in the selected file set and an already-loaded file is skipped in the later read loop.
Reason: The pre-allocation check compares the budget without modifying retained_bytes. The selected-file accounting adds the report size once.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4684157154

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:4653, :4685, :7927 and :8101. On W4 a paired ordinary fixture retained 8,327 P bytes and 230 H bytes. The sum of 8,557 passed; 8,556 rejected H with AM_receipt_retention_budget.
Reason: The P and H observations each enter the selected member set and are charged once. The pre-allocation comparison does not increment the counter. The exact retained P total is passed into the subsequent H load.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4685552123

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:4158, :4183, :4633 and :4667; .github/workflows/ci.yml:733 and .github/workflows/cd.yml:1520. The space-changed and evidence-space-changed test cases verify fail-closed behavior.
Reason: The 512 MiB admission reserve bounds this reader's own writes from the observed capacity. Its two authenticated downloads run serially in a private job directory, with another capacity check before the destination write. A later external filesystem write can still cause I/O failure and no successful verification. Global allocation across unrelated writers is outside this reader's contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#discussion_r4685552140

Disposition: NOT-A-BUG
Evidence: scripts/ci/fetch_docker_source_artifacts.py:4653, :4685, :8101 and :4183. The paired exact-boundary control accepted 8,557 bytes and refused 8,556. Shared/separate filesystem and post-capture capacity-loss tests cover the operational reserve.
Reason: Both observations have ordinary in-scope explanations: retained observation bytes are charged once across sequential P/H reads, and disk reserve admission checks cover this job's bounded writes on the selected volumes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2504#pullrequestreview-6046144245

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:1db0c3485301f70c0832a51dc0f46361d32bbbc5eef4b9f52ecfa4074f8f0d9a","material_head_sha":"1ed28d7092c0d8225597d1030154d187eb38fe40","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"b67d9f5e0a85b99fa77d31464daa169fc0520923","blocking":false,"head_revision":"1ed28d7092c0d8225597d1030154d187eb38fe40","material_digest":"sha256:1db0c3485301f70c0832a51dc0f46361d32bbbc5eef4b9f52ecfa4074f8f0d9a","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"b67d9f5e0a85b99fa77d31464daa169fc0520923","digest":"sha256:1db0c3485301f70c0832a51dc0f46361d32bbbc5eef4b9f52ecfa4074f8f0d9a","material_head_sha":"1ed28d7092c0d8225597d1030154d187eb38fe40","merge_base_sha":"b67d9f5e0a85b99fa77d31464daa169fc0520923","policy_version":"pulseplate.material-classification/v1"},"pr_number":2504,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:1db0c3485301f70c0832a51dc0f46361d32bbbc5eef4b9f52ecfa4074f8f0d9a","material_head_sha":"1ed28d7092c0d8225597d1030154d187eb38fe40","report_payload":{"actionable_findings_count":0,"base_ref_oid":"b67d9f5e0a85b99fa77d31464daa169fc0520923","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/4bb4c27eb9b5.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"4bb4c27eb9b5"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1753 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-11-24T20:46:54Z","material_digest":"sha256:1db0c3485301f70c0832a51dc0f46361d32bbbc5eef4b9f52ecfa4074f8f0d9a","material_head_sha":"1ed28d7092c0d8225597d1030154d187eb38fe40","merge_base_sha":"b67d9f5e0a85b99fa77d31464daa169fc0520923","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"b67d9f5e0a85b99fa77d31464daa169fc0520923..1ed28d7092c0d8225597d1030154d187eb38fe40","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2504_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/cd.yml",".github/workflows/ci.yml",".github/workflows/frontend-ci.yml",".secrets.baseline","docs/roadmap/BACKLOG_LEDGER.md","docs/security/CVE-2026-84445-alertmanager.md","scripts/AGENTS.md","scripts/ci/fetch_docker_source_artifacts.py","scripts/deploy.sh","scripts/deploy_production.sh","tests/test_caddy_deploy_provenance.py","tests/test_docker_workflow_build_path_contract.py"],"diff_summary":{"additions":1444,"changed_lines":1753,"deletions":309,"files":12},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:049776d9e48ffe3cf3cf7e274851952bac89cdde93b99256ddcd0e764cb13697","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
