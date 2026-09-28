# PR 2451 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/3a0da712f24d.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/noos-1b-final-keyed-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_private_path_rejects_symlinked_ancestor
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116006390 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_case_source_score_rejects_out_of_range_and_nonfinite
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116006396 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_collector_observes_real_final_field_and_fallback
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116020059 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_field_mismatch_has_unknown_origin
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116020065 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_partial_collection_receipt_preserves_completed_case
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116020069 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_wrapped_budget_failures_keep_exact_receipt_reason
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116020071 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_degraded_controlled_retrieval_cannot_be_scored
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029529 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_reported_cost_over_reservation_stops_following_send
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029534 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_cost_is_known_only_for_one_accounted_attempt
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029542 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_reader_and_reference_receipt_prerequisites_fail_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029548 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_identity_attempt_and_cost_admission_is_fail_closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029555 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_validated_case_and_annotation_do_not_alias_raw_input
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029563 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_report_fingerprint_changes_with_equal_metrics_but_changed_rationale
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029570 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_partial_collection_receipt_preserves_completed_case
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116029577 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_hmac_packets_reject_wrong_key_and_unkeyed_historical_ids
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203014 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_manifest_defensive_copy_prevents_post_admission_mutation
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203017 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_collector_rejects_nonignored_output_before_provider_construction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203020 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_manifest_rejects_whitespace_context_and_late_unsafe_context
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203022 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_reported_cost_over_reservation_stops_following_send
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203024 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_corpus_cannot_mix_run_identity
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203027 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_origin_requires_raw_canonical_final_field
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203029 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_nonprovider_cases_cannot_contribute_cost_accounting
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203035 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_live_environment_needs_synthetic_private_pro_quota
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203039 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_unmatched_candidate_abstention_keeps_omission_and_abstention
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116203044 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_manifest_rejects_whitespace_context_and_late_unsafe_context
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116446606 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_whole_manifest_preflight_uses_encoded_sdk_body_without_send
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116446609 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_hidden_inputs_require_owner_private_file_or_directory
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116446611 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_sources_must_match_captured_public_projection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4116446614 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 90984d613d912fc1d1bc2601cd15fb3bd562c53e
Evidence: tests/test_fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_live_environment_restores_baseline_engine_after_temporary_quota_db
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4117088538 -> 90984d613d912fc1d1bc2601cd15fb3bd562c53e

Disposition: FIXED
Commit: 90984d613d912fc1d1bc2601cd15fb3bd562c53e
Evidence: tests/test_fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_sdk_and_tenacity_retries_share_physical_attempt_counter
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4117088540 -> 90984d613d912fc1d1bc2601cd15fb3bd562c53e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_private_path_rejects_symlinked_ancestor; tests/test_fitchef_claim_assurance_eval.py::test_case_source_score_rejects_out_of_range_and_nonfinite
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#pullrequestreview-5331040845 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: b1795bcfe3c6d10080cf2e8c3763c3fc477a281e
Evidence: scripts/evals/collect_fitchef_answers.py; tests/test_fitchef_claim_assurance_eval.py::test_provider_field_mismatch_has_unknown_origin; test_partial_collection_receipt_preserves_completed_case
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#pullrequestreview-5331064174 -> b1795bcfe3c6d10080cf2e8c3763c3fc477a281e

Disposition: FIXED
Commit: 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8
Evidence: scripts/evals/collect_fitchef_answers.py; scripts/evals/fitchef_claim_assurance_eval.py; tests/test_fitchef_claim_assurance_eval.py::test_manifest_defensive_copy_prevents_post_admission_mutation; earlier stale MockTransport note is already corrected by 77d441ab18953ea6f2ef18b9e9ca709fd100ed87
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#pullrequestreview-5331373902 -> 6c3f889ab1909e2cba9a1668ba3b2294231cc2b8

Disposition: FIXED
Commit: 90984d613d912fc1d1bc2601cd15fb3bd562c53e
Evidence: tests/test_fitchef_claim_assurance_eval.py::test_live_environment_restores_baseline_engine_after_temporary_quota_db; test_sdk_and_tenacity_retries_share_physical_attempt_counter; unmatched abstention has separate NOT-A-BUG proof
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#pullrequestreview-5332233438 -> 90984d613d912fc1d1bc2601cd15fb3bd562c53e

Disposition: NOT-A-BUG
Evidence: tests/test_fitchef_claim_assurance_eval.py::test_unmatched_candidate_abstention_keeps_omission_and_abstention; scripts/evals/fitchef_claim_assurance_eval.py::_metrics
Reason: An unmatched candidate abstention and the omitted reference claim are distinct observations. Coverage uses matched/reference claims directly; no additive partition over those three counters is promised. Dropping unmatched abstentions would hide an explicit candidate abstention.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2451#discussion_r4117088526

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:7bc921b455a92dc00b026d0f56fc1aaf6dcb4c23376a324e0f6e9716f09d5f95","material_head_sha":"b04da225e657152cb7b986e4872766f73864f096","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"314995c81283a99d268e5e7e504c0353ac437720","blocking":false,"head_revision":"b04da225e657152cb7b986e4872766f73864f096","material_digest":"sha256:7bc921b455a92dc00b026d0f56fc1aaf6dcb4c23376a324e0f6e9716f09d5f95","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"314995c81283a99d268e5e7e504c0353ac437720","digest":"sha256:7bc921b455a92dc00b026d0f56fc1aaf6dcb4c23376a324e0f6e9716f09d5f95","material_head_sha":"b04da225e657152cb7b986e4872766f73864f096","merge_base_sha":"314995c81283a99d268e5e7e504c0353ac437720","policy_version":"pulseplate.material-classification/v1"},"pr_number":2451,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:7bc921b455a92dc00b026d0f56fc1aaf6dcb4c23376a324e0f6e9716f09d5f95","material_head_sha":"b04da225e657152cb7b986e4872766f73864f096","report_payload":{"actionable_findings_count":0,"base_ref_oid":"314995c81283a99d268e5e7e504c0353ac437720","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"3a0da712f24d"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 4933 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-28T20:04:11Z","material_digest":"sha256:7bc921b455a92dc00b026d0f56fc1aaf6dcb4c23376a324e0f6e9716f09d5f95","material_head_sha":"b04da225e657152cb7b986e4872766f73864f096","merge_base_sha":"314995c81283a99d268e5e7e504c0353ac437720","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"314995c81283a99d268e5e7e504c0353ac437720..b04da225e657152cb7b986e4872766f73864f096","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2451_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/ci.yml","docs/evals/FITCHEF_CLAIM_EVIDENCE_EVAL_V1.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/AGENTS.md","scripts/evals/collect_fitchef_answers.py","scripts/evals/fitchef_claim_assurance_eval.py","tests/fixtures/evidence/fitchef_claim_assurance/development_controls.jsonl","tests/guards/test_security_devtooling_regression_guards.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_fitchef_claim_assurance_eval.py"],"diff_summary":{"additions":4921,"changed_lines":4933,"deletions":12,"files":10},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:981e8be248c1d1ef6d7810c94913d2781f5615bd1e617408c30aeca2b517c1fb","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
