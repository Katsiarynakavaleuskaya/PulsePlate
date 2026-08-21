# PR 2309 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/bc68e18d227d.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/mirror-cut-oracle-post-main-sync.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 788ec1a877630e357754abd284cba8a57f0bbf40
Evidence: tests/test_repo_policy_guards.py replaces lexical source counting with AST recognition; the focused repo-policy guard, validate-changed, and exact-head gates pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#discussion_r3827501181 -> 788ec1a877630e357754abd284cba8a57f0bbf40

Disposition: FIXED
Commit: 5cb927d92e590a31e2cd0aa2c7f7d5cd164b031d
Evidence: tests/test_repo_policy_guards.py:764-895 implements the digest-bound manifest, closed scope-aware AST recognizer, exact owner/wrapper/call cardinality, eight fresh feature states, and five live route-manifest drift negatives.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#discussion_r3827789469 -> 5cb927d92e590a31e2cd0aa2c7f7d5cd164b031d

Disposition: FIXED
Commit: 788ec1a877630e357754abd284cba8a57f0bbf40
Evidence: The review lexical-count defect is fixed by the post-review AST commit and discussion_r3827501181 proof. The separate repeated-bootstrap suggestion is dispositioned NOT-A-BUG at discussion_r3827501173 with registrar-owned idempotency evidence.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#pullrequestreview-4989939837 -> 788ec1a877630e357754abd284cba8a57f0bbf40

Disposition: FIXED
Commit: 5cb927d92e590a31e2cd0aa2c7f7d5cd164b031d
Evidence: The sole actionable scope/cardinality finding is fixed by the post-review closed recognizer and live manifest commit; discussion_r3827789469 carries the detailed executable proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#pullrequestreview-4990271058 -> 5cb927d92e590a31e2cd0aa2c7f7d5cd164b031d

Disposition: FIXED
Commit: 067cf93a35957cf489d0760c984bf06300df8fdf
Evidence: tests/test_repo_policy_guards.py:812-895 now parameterizes all eight feature states, emits deterministic source/live route rows on mismatch, and documents the reviewed regeneration procedure; targeted, full guard, validate-changed, all-files pre-commit, and pre-push gates pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#pullrequestreview-4991200620 -> 067cf93a35957cf489d0760c984bf06300df8fdf

Disposition: NOT-A-BUG
Evidence: app/routers/bmi_registration.py:150-220 owns per-app idempotency; tests/test_bmi_registration_router_coverage.py:77 calls the registrar twice and proves one live family; tests/test_application_instance_ownership.py:256 proves repeated canonical bootstrap leaves the composed app unchanged.
Reason: ensure_canonical_app_bootstrap intentionally invokes the idempotent registrar once per bootstrap attempt. Requiring the outer wrapper to suppress the second call would create a false wrapper-cache contract and weaken registrar ownership.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#discussion_r3827501173

Disposition: NOT-A-BUG
Evidence: app/routers/bmi_registration.py:150-220 and tests/test_bmi_registration_router_coverage.py:77 prove registrar-owned idempotency; exact-head CodeRabbit status is SUCCESS. Repository CI does not enforce the advisory bot docstring percentage.
Reason: The summary repeats the false outer-wrapper cache contract and an advisory docstring metric. Neither is an unfixed current-surface defect or required repository gate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#issuecomment-5365587232

Disposition: NOT-A-BUG
Evidence: tests/test_application_instance_ownership.py:19-188, tests/test_missing_coverage.py, and tests/test_repo_policy_guards.py are deliberately independent runtime/import/static-policy oracles; the bounded AST collector is local to one closed guard mechanism.
Reason: Centralizing the retired-name tuple or extracting a speculative shared recognizer would couple independent tests, add mutable test authority, and provide no production correction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2309#pullrequestreview-4989925165

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:f6a2b72bb18c31d293d3fb1454ce284920c1c111d8caecd7c12e933d4fcf4b13","material_head_sha":"067cf93a35957cf489d0760c984bf06300df8fdf","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"e2be23492a5266116109f4908f5ee33bd05711e0","blocking":false,"head_revision":"067cf93a35957cf489d0760c984bf06300df8fdf","material_digest":"sha256:f6a2b72bb18c31d293d3fb1454ce284920c1c111d8caecd7c12e933d4fcf4b13","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"e2be23492a5266116109f4908f5ee33bd05711e0","digest":"sha256:f6a2b72bb18c31d293d3fb1454ce284920c1c111d8caecd7c12e933d4fcf4b13","material_head_sha":"067cf93a35957cf489d0760c984bf06300df8fdf","merge_base_sha":"e2be23492a5266116109f4908f5ee33bd05711e0","policy_version":"pulseplate.material-classification/v1"},"pr_number":2309,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:f6a2b72bb18c31d293d3fb1454ce284920c1c111d8caecd7c12e933d4fcf4b13","material_head_sha":"067cf93a35957cf489d0760c984bf06300df8fdf","report_payload":{"actionable_findings_count":0,"base_ref_oid":"e2be23492a5266116109f4908f5ee33bd05711e0","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/bc68e18d227d.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"bc68e18d227d"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1285 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-08-21T08:37:27Z","material_digest":"sha256:f6a2b72bb18c31d293d3fb1454ce284920c1c111d8caecd7c12e933d4fcf4b13","material_head_sha":"067cf93a35957cf489d0760c984bf06300df8fdf","merge_base_sha":"e2be23492a5266116109f4908f5ee33bd05711e0","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"e2be23492a5266116109f4908f5ee33bd05711e0..067cf93a35957cf489d0760c984bf06300df8fdf","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2309_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["app/AGENTS.md","app/__init__.py","app/main.py","docs/architecture/LEGACY_COMPATIBILITY_SEAM.md","docs/architecture/backend_routing_map.md","legacy_app.py","tests/edges/test_legacy_premium_nutrition_registration_bootstrap.py","tests/test_application_instance_ownership.py","tests/test_coverage_boost_simple_97.py","tests/test_final_coverage_97_boost.py","tests/test_main_paywall_bootstrap.py","tests/test_missing_coverage.py","tests/test_repo_policy_guards.py","tests/test_route_family_bootstrap.py"],"diff_summary":{"additions":854,"changed_lines":1285,"deletions":431,"files":14},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","app/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:580d8d5a21ea3b6f2be93d65b65fbdbd3f13a8b940db24a9163f6a7ed246dbc8","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
