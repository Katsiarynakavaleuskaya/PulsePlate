# PR 2315 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/dd43fea29205.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/creative-single-role-synthesis-routing-context-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: a411959fae412be9654b8c905565981a4ad3bae8
Evidence: scripts/orchestration/qoder_dispatch_bridge.py:validate_task_pilot_context-call
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835509292 -> a411959fae412be9654b8c905565981a4ad3bae8

Disposition: FIXED
Commit: a411959fae412be9654b8c905565981a4ad3bae8
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_near_misses_fail_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835514416 -> a411959fae412be9654b8c905565981a4ad3bae8

Disposition: FIXED
Commit: 1b655a622004117c20f0b9663eeecc7f64714f89
Evidence: tests/test_render_codex_start_prompt.py::test_packet_role_order_rejects_malformed_legacy_creative_context
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835563076 -> 1b655a622004117c20f0b9663eeecc7f64714f89

Disposition: FIXED
Commit: 1b655a622004117c20f0b9663eeecc7f64714f89
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_near_misses_fail_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835563079 -> 1b655a622004117c20f0b9663eeecc7f64714f89

Disposition: FIXED
Commit: f5ac0fafc431d10d3adab5a004c48fbf42ffa84d
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_near_misses_fail_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835571489 -> f5ac0fafc431d10d3adab5a004c48fbf42ffa84d

Disposition: FIXED
Commit: f5ac0fafc431d10d3adab5a004c48fbf42ffa84d
Evidence: tests/test_creative_pilot_workspace.py::test_synthesis_task_packet_with_security_review_requirement_fails_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835571490 -> f5ac0fafc431d10d3adab5a004c48fbf42ffa84d

Disposition: FIXED
Commit: d3d9e4f0a370b31639025eb5081d553aba0cf9d5
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_accepts_rebound_context_identity
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835651344 -> d3d9e4f0a370b31639025eb5081d553aba0cf9d5

Disposition: FIXED
Commit: d3d9e4f0a370b31639025eb5081d553aba0cf9d5
Evidence: tests/test_qoder_dispatch_bridge.py::test_legacy_creative_context_preserves_existing_role_order
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835651347 -> d3d9e4f0a370b31639025eb5081d553aba0cf9d5

Disposition: FIXED
Commit: 9c3cdafd5d22932178b320d280924e74c46f5050
Evidence: tests/test_creative_pilot_workspace.py::test_synthesis_task_packet_with_judgment_requirement_fails_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835718901 -> 9c3cdafd5d22932178b320d280924e74c46f5050

Disposition: FIXED
Commit: 8c39f813a76747af66d63473fb85381242b0a28a
Evidence: tests/test_qoder_dispatch_bridge.py::test_synthesis_security_requirement_cannot_be_hidden_by_flag
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835793790 -> 8c39f813a76747af66d63473fb85381242b0a28a

Disposition: FIXED
Commit: 8c39f813a76747af66d63473fb85381242b0a28a
Evidence: tests/test_qoder_dispatch_bridge.py::test_synthesis_judgment_requirement_cannot_be_hidden_by_projection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835860541 -> 8c39f813a76747af66d63473fb85381242b0a28a

Disposition: FIXED
Commit: 3f45724cfab3d61bfd04a0edf3702e38ecc0b5e0
Evidence: tests/test_qoder_dispatch_bridge.py::test_synthesis_candidate_paths_must_use_canonical_spelling
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836044151 -> 3f45724cfab3d61bfd04a0edf3702e38ecc0b5e0

Disposition: FIXED
Commit: 6a77e6be353ee59d9e55f2ff683e364ab041deb8
Evidence: tests/test_context_pack.py::test_root_absorption_happens_only_after_all_members_validate
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836128198 -> 6a77e6be353ee59d9e55f2ff683e364ab041deb8

Disposition: FIXED
Commit: cb8d9ea75040d8948c1b3feebba8d48c30bc8848
Evidence: tests/test_creative_pilot_workspace.py::test_synthesis_dispatch_requires_workspace_source_field
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836476071 -> cb8d9ea75040d8948c1b3feebba8d48c30bc8848

Disposition: FIXED
Commit: 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_rederives_domain_before_identity
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836655401 -> 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4

Disposition: FIXED
Commit: 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4
Evidence: tests/test_creative_pilot_workspace.py::test_synthesis_dispatch_binds_candidate_paths_to_workspace_targets
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836655404 -> 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4

Disposition: FIXED
Commit: 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4
Evidence: tests/test_context_pack.py::test_candidate_path_preserves_ordinary_internal_spaces
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3836655407 -> 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4

Disposition: FIXED
Commit: 95e372da2d126a65b32f8285acafeadbb86984c7
Evidence: tests/test_qoder_dispatch_bridge.py:complete-CodeRabbit-regression-matrix
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#issuecomment-5378994109 -> 95e372da2d126a65b32f8285acafeadbb86984c7

Disposition: FIXED
Commit: a411959fae412be9654b8c905565981a4ad3bae8
Evidence: scripts/orchestration/qoder_dispatch_bridge.py:validated-context-call
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999488095 -> a411959fae412be9654b8c905565981a4ad3bae8

Disposition: FIXED
Commit: a411959fae412be9654b8c905565981a4ad3bae8
Evidence: tests/test_qoder_dispatch_bridge.py:legacy-schema-cases
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999492952 -> a411959fae412be9654b8c905565981a4ad3bae8

Disposition: FIXED
Commit: 1b655a622004117c20f0b9663eeecc7f64714f89
Evidence: tests/test_qoder_dispatch_bridge.py:legacy-structure-and-exact-error-cases
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999560900 -> 1b655a622004117c20f0b9663eeecc7f64714f89

Disposition: FIXED
Commit: f5ac0fafc431d10d3adab5a004c48fbf42ffa84d
Evidence: tests/test_qoder_dispatch_bridge.py:numeric-authority-and-review-flag-cases
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999576045 -> f5ac0fafc431d10d3adab5a004c48fbf42ffa84d

Disposition: FIXED
Commit: d3d9e4f0a370b31639025eb5081d553aba0cf9d5
Evidence: tests/test_qoder_dispatch_bridge.py:packet-identity-and-legacy-null-cases
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999787991 -> d3d9e4f0a370b31639025eb5081d553aba0cf9d5

Disposition: FIXED
Commit: 9c3cdafd5d22932178b320d280924e74c46f5050
Evidence: tests/test_qoder_dispatch_bridge.py:inactive-judgment-matrix
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999855730 -> 9c3cdafd5d22932178b320d280924e74c46f5050

Disposition: FIXED
Commit: 8c39f813a76747af66d63473fb85381242b0a28a
Evidence: tests/test_qoder_dispatch_bridge.py:derived-security-classifier-case
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999926066 -> 8c39f813a76747af66d63473fb85381242b0a28a

Disposition: FIXED
Commit: 8c39f813a76747af66d63473fb85381242b0a28a
Evidence: tests/test_qoder_dispatch_bridge.py:derived-judgment-classifier-case
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999984776 -> 8c39f813a76747af66d63473fb85381242b0a28a

Disposition: FIXED
Commit: 95e372da2d126a65b32f8285acafeadbb86984c7
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_judgment_structure_fails_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-5000044311 -> 95e372da2d126a65b32f8285acafeadbb86984c7

Disposition: FIXED
Commit: 3f45724cfab3d61bfd04a0edf3702e38ecc0b5e0
Evidence: tests/test_qoder_dispatch_bridge.py::test_synthesis_candidate_paths_must_use_canonical_spelling
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-5000188072 -> 3f45724cfab3d61bfd04a0edf3702e38ecc0b5e0

Disposition: FIXED
Commit: 6a77e6be353ee59d9e55f2ff683e364ab041deb8
Evidence: tests/test_task_bootstrap.py::test_task_bootstrap_root_scope_preserves_candidate_path
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-5000262446 -> 6a77e6be353ee59d9e55f2ff683e364ab041deb8

Disposition: FIXED
Commit: cb8d9ea75040d8948c1b3feebba8d48c30bc8848
Evidence: tests/test_creative_pilot_workspace.py:workspace-source-provenance-matrix
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-5000571789 -> cb8d9ea75040d8948c1b3feebba8d48c30bc8848

Disposition: FIXED
Commit: 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4
Evidence: tests/test_qoder_dispatch_bridge.py:routing-workspace-context-and-space-path-closures
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-5000733190 -> 9e0b07bcbcaf95f0f3e464d3cc9d2b4d7584e8d4

Disposition: NOT-A-BUG
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_near_misses_fail_closed
Reason: dispatch_role_order is rejected by canonical invariant-review validation before the synthesis recognizer can accept it
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#discussion_r3835507707

Disposition: NOT-A-BUG
Evidence: tests/test_qoder_dispatch_bridge.py::test_single_coordinator_synthesis_near_misses_fail_closed
Reason: the sole Sourcery issue is the dispatch_role_order false positive rejected by the canonical invariant-review validator
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2315#pullrequestreview-4999486643

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:cb47e7f03d6dd9dcb8a28823c6cd03d026a30898ed92da45398be9d87bcda7d3","material_head_sha":"6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b","blocking":false,"head_revision":"6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","material_digest":"sha256:cb47e7f03d6dd9dcb8a28823c6cd03d026a30898ed92da45398be9d87bcda7d3","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b","digest":"sha256:cb47e7f03d6dd9dcb8a28823c6cd03d026a30898ed92da45398be9d87bcda7d3","material_head_sha":"6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","merge_base_sha":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b","policy_version":"pulseplate.material-classification/v1"},"pr_number":2315,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:cb47e7f03d6dd9dcb8a28823c6cd03d026a30898ed92da45398be9d87bcda7d3","material_head_sha":"6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","report_payload":{"actionable_findings_count":0,"base_ref_oid":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/dd43fea29205.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"dd43fea29205"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2796 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-08-22T20:12:04Z","material_digest":"sha256:cb47e7f03d6dd9dcb8a28823c6cd03d026a30898ed92da45398be9d87bcda7d3","material_head_sha":"6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","merge_base_sha":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"52bf381e13dce55bdf5d6a9a5bb816d117365c4b..6ff52d6e0f8856a726c076e51fa34c27e1b2e5f8","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2315_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["docs/orchestration/KIMI_NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md","docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/orchestration/bootstrap_sync_policy.py","scripts/orchestration/context_pack.py","scripts/orchestration/creative_pilot_workspace_contract.py","scripts/orchestration/embedding_retrieval_admission_telemetry.py","scripts/orchestration/qoder_dispatch_bridge.py","scripts/orchestration/task_bootstrap.py","tests/test_bootstrap_sync_policy.py","tests/test_context_pack.py","tests/test_creative_pilot_workspace.py","tests/test_qoder_dispatch_bridge.py","tests/test_render_codex_start_prompt.py","tests/test_task_bootstrap.py"],"diff_summary":{"additions":2559,"changed_lines":2796,"deletions":237,"files":15},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","docs/orchestration/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:13f0f3f697bc1dc5a91dd2d0a2dea25f080d6e91c8514d8234203c10ec153e21","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
