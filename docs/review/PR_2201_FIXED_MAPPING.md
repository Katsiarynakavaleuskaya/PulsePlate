# PR 2201 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/2294406629be.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/tc1-cdb076a28-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-test-hygiene-client-lifecycle
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3680751452

Disposition: FIXED
Commit: 1b115edbc029d3f0f67a33e23e95bdaf15ad5693
Evidence: tests/test_testclient_lifecycle_foundation.py::test_isolated_sqlite_fails_closed_when_async_state_is_active proves fail-closed before env or file mutation
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679760105 -> 1b115edbc029d3f0f67a33e23e95bdaf15ad5693

Disposition: FIXED
Commit: 1b115edbc029d3f0f67a33e23e95bdaf15ad5693
Evidence: tests/test_testclient_lifecycle_foundation.py::test_isolated_sqlite_teardown_refuses_replaced_path covers inode and symlink replacement
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679760109 -> 1b115edbc029d3f0f67a33e23e95bdaf15ad5693

Disposition: FIXED
Commit: 3131197caf66e89c2418a80d45bb06ee01ecc177
Evidence: Final material head 3131197caf66e89c2418a80d45bb06ee01ecc177 is frozen and the replacement v1 seal binds its exact digest
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679777003 -> 3131197caf66e89c2418a80d45bb06ee01ecc177

Disposition: FIXED
Commit: 632955d873221235af44a22870488cfd9f5df4bc
Evidence: tests/test_testclient_provider_contract.py tracks get_client as deprecated and forbids new provider callers
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679777009 -> 632955d873221235af44a22870488cfd9f5df4bc

Disposition: FIXED
Commit: 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6
Evidence: tests/test_conftest_coverage_97.py no longer mutates sys.modules and the canonical policy guard passes
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679777012 -> 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6

Disposition: FIXED
Commit: e50f793593496067a4d47a037f3089ee2878ea65
Evidence: tests/test_testclient_lifecycle_foundation.py::test_open_test_client_restores_dependency_override_mapping_identity
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679815423 -> e50f793593496067a4d47a037f3089ee2878ea65

Disposition: FIXED
Commit: 81096576c754019be2a6fe718b6df62744430503
Evidence: tests/test_rate_limit_test_client_guards.py proves legacy singleton cleanup restores poisoned state until TC2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679815426 -> 81096576c754019be2a6fe718b6df62744430503

Disposition: FIXED
Commit: e50f793593496067a4d47a037f3089ee2878ea65
Evidence: tests/test_testclient_lifecycle_foundation.py::test_isolated_sqlite_teardown_refuses_dangling_symlink
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679815428 -> e50f793593496067a4d47a037f3089ee2878ea65

Disposition: FIXED
Commit: 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6
Evidence: Collected reset_sys_modules coverage tests have typed fixture parameters and None return annotations
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679858999 -> 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6

Disposition: FIXED
Commit: 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6
Evidence: Coverage-only sys.modules writes were removed and tests/test_repo_policy_sys_modules.py passes
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679859003 -> 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6

Disposition: FIXED
Commit: 3131197caf66e89c2418a80d45bb06ee01ecc177
Evidence: Final material head 3131197caf66e89c2418a80d45bb06ee01ecc177 is frozen and the replacement v1 seal binds its exact digest
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679872783 -> 3131197caf66e89c2418a80d45bb06ee01ecc177

Disposition: FIXED
Commit: 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6
Evidence: tests/test_conftest_line58.py and tests/test_conftest_last_lines.py avoid persistent sys.modules mutation
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679872786 -> 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6

Disposition: FIXED
Commit: 632955d873221235af44a22870488cfd9f5df4bc
Evidence: tests/test_testclient_provider_contract.py rejects lexical shadowing with compiler scope evidence
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3679872787 -> 632955d873221235af44a22870488cfd9f5df4bc

Disposition: FIXED
Commit: b69fcabd7ac5ffa090082f750a777861528d3a36
Evidence: Provider guard reuses the canonical tests.test_repo_policy_sys_modules scanner including mutating method calls
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3680751457 -> b69fcabd7ac5ffa090082f750a777861528d3a36

Disposition: FIXED
Commit: 632955d873221235af44a22870488cfd9f5df4bc
Evidence: tests/test_testclient_provider_contract.py rejects with-as lexical rebinding
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3680775351 -> 632955d873221235af44a22870488cfd9f5df4bc

Disposition: FIXED
Commit: 3131197caf66e89c2418a80d45bb06ee01ecc177
Evidence: Provider ownership requires one fixture-wide Yield identity under one managed context item and five invalid-shape oracles pass
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#discussion_r3681091466 -> 3131197caf66e89c2418a80d45bb06ee01ecc177

Disposition: FIXED
Commit: 1b115edbc029d3f0f67a33e23e95bdaf15ad5693
Evidence: Both Sourcery SQLite isolation actionables are covered by active-async-state and replaced-path lifecycle tests
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#pullrequestreview-4815022997 -> 1b115edbc029d3f0f67a33e23e95bdaf15ad5693

Disposition: FIXED
Commit: 894c2f0c429a38575f48aff7b35487b43e7be0ba
Evidence: CodeRabbit repo-root, structural response typing, and cleanup-primary-error findings are fixed with focused oracles
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#pullrequestreview-4815036856 -> 894c2f0c429a38575f48aff7b35487b43e7be0ba

Disposition: FIXED
Commit: 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6
Evidence: Both CodeRabbit sys.modules and typing actionables are fixed and policy guards pass
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#pullrequestreview-4815144809 -> 4b247f453eb33ac2dbc0dc435cad4612a48f8ec6

Disposition: FIXED
Commit: b69fcabd7ac5ffa090082f750a777861528d3a36
Evidence: Invalid-source guard diagnostics report exact leaking indexes and targets
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#pullrequestreview-4816704992 -> b69fcabd7ac5ffa090082f750a777861528d3a36

Disposition: NOT-A-BUG
Evidence: tests/conftest.py legacy singleton bridge and tests/test_rate_limit_test_client_guards.py prove distinct finite compatibility semantics while the inline with-as defect is separately FIXED
Reason: This top-level review is a mixed container and extracting a new public limiter API would widen temporary TC1 ownership before TC2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2201#pullrequestreview-4816328541

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:8d84e7da64664eafaa9bc2f7c2367b75e770f82c61905dcda23aeadabd51887e","material_head_sha":"3131197caf66e89c2418a80d45bb06ee01ecc177","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"3909b79ffd4b123f9753ef6af680f677fa84ef18","blocking":false,"head_revision":"3131197caf66e89c2418a80d45bb06ee01ecc177","material_digest":"sha256:8d84e7da64664eafaa9bc2f7c2367b75e770f82c61905dcda23aeadabd51887e","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"3909b79ffd4b123f9753ef6af680f677fa84ef18","digest":"sha256:8d84e7da64664eafaa9bc2f7c2367b75e770f82c61905dcda23aeadabd51887e","material_head_sha":"3131197caf66e89c2418a80d45bb06ee01ecc177","merge_base_sha":"3909b79ffd4b123f9753ef6af680f677fa84ef18","policy_version":"pulseplate.material-classification/v1"},"pr_number":2201,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:8d84e7da64664eafaa9bc2f7c2367b75e770f82c61905dcda23aeadabd51887e","material_head_sha":"3131197caf66e89c2418a80d45bb06ee01ecc177","report_payload":{"actionable_findings_count":0,"base_ref_oid":"3909b79ffd4b123f9753ef6af680f677fa84ef18","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/2294406629be.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"2294406629be"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 3069 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-07-30T12:19:46Z","material_digest":"sha256:8d84e7da64664eafaa9bc2f7c2367b75e770f82c61905dcda23aeadabd51887e","material_head_sha":"3131197caf66e89c2418a80d45bb06ee01ecc177","merge_base_sha":"3909b79ffd4b123f9753ef6af680f677fa84ef18","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"3909b79ffd4b123f9753ef6af680f677fa84ef18..3131197caf66e89c2418a80d45bb06ee01ecc177","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2201_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".secrets.baseline","conftest.py","docs/roadmap/BACKLOG_LEDGER.md","docs/tracking/ISSUE-TESTCLIENT-FACTORY-MIGRATION.md","tests/AGENTS.md","tests/_client.py","tests/conftest.py","tests/conftest_app.py","tests/test_conftest_coverage_97.py","tests/test_conftest_final_coverage.py","tests/test_conftest_last_lines.py","tests/test_conftest_line58.py","tests/test_conftest_specific_lines.py","tests/test_conftest_targeted_coverage.py","tests/test_final_coverage_97_boost.py","tests/test_rate_limit_test_client_guards.py","tests/test_testclient_lifecycle_foundation.py","tests/test_testclient_provider_contract.py"],"diff_summary":{"additions":2420,"changed_lines":3069,"deletions":649,"files":18},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:bf914204a8fb40147ec2c062b014efa1be9adb2710337e131ff2cf770aacaf97","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
