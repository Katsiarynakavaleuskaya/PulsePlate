# PR 2405 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/76026d412473.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/ops02-db-lifecycle-oracle-v18.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: tests/test_db_engine_reuse_diff_coverage.py::test_init_db_explicit_sqlite_url_creates_its_missing_parent
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081532965 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: tests/test_app_db_fallback_97.py::test_raw_getter_cannot_resurrect_primary_after_fallback_publication
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081604263 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: tests/test_db_missing_lines_coverage.py direct adapter tests assert exact selected factory bind
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081604273 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: docs/roadmap/BACKLOG_LEDGER.md OPS-02 Target PR #2405
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081604279 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: tests/test_core_db_missing_coverage.py _RaceLock monkeypatch restores AsyncSessionLocal
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081604305 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: tests/test_db_engine_reuse_diff_coverage.py::test_query_only_sqlite_replacement_preserves_selected_database_file
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081611190 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: e50b8f20d66aed4920e0a9aa9bd8248889d26106
Evidence: tests/test_core_db_comprehensive.py::test_async_acquisition_returns_current_pair_after_concurrent_retirement and sync Event regressions
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4081981013 -> e50b8f20d66aed4920e0a9aa9bd8248889d26106

Disposition: FIXED
Commit: ab40718c2912f36de317ff8e9c70b4500916dd47
Evidence: tests/test_db_engine_reuse_diff_coverage.py::test_sqlite_to_pysqlite_same_file_replacement_preserves_database
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4083683057 -> ab40718c2912f36de317ff8e9c70b4500916dd47

Disposition: FIXED
Commit: 5b09c9b0c7d7148245fcd645a37ab2c6c410299e
Evidence: tests/test_db_engine_reuse_diff_coverage.py::test_uri_retirement_never_deletes_unsuffixed_decoy_file and selected URI regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4084151967 -> 5b09c9b0c7d7148245fcd645a37ab2c6c410299e

Disposition: FIXED
Commit: 56f296bd124b142c2035b8445f2373b9401ed80c
Evidence: core/db.py:1046, core/db.py:1137, tests/test_db_engine_reuse_diff_coverage.py:544; deterministic in-flight candidate race passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087415578 -> 56f296bd124b142c2035b8445f2373b9401ed80c

Disposition: FIXED
Commit: 56f296bd124b142c2035b8445f2373b9401ed80c
Evidence: core/db.py:1092, tests/test_db_engine_reuse_diff_coverage.py:802; ambient race and selected schema primary-error cases passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087415583 -> 56f296bd124b142c2035b8445f2373b9401ed80c

Disposition: FIXED
Commit: 56f296bd124b142c2035b8445f2373b9401ed80c
Evidence: core/db.py:1124, tests/test_db_engine_reuse_diff_coverage.py:607; confirmed non-SQLite replacement cleanup passed without server connection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087415588 -> 56f296bd124b142c2035b8445f2373b9401ed80c

Disposition: FIXED
Commit: f9fba67f95128408b8297a90c2d7fe781ab11c8f
Evidence: core/db_fallback.py:209-218 rechecks current engine and factory after retirement; tests/test_app_db_fallback_97.py:110 deterministic concurrent replacement passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087701318 -> f9fba67f95128408b8297a90c2d7fe781ab11c8f

Disposition: FIXED
Commit: 98bba2268d73475e985d07aae65210a0942f8237
Evidence: core/db_fallback.py:300 reconciles degraded markers to selected URL; core/db.py publication paths call it; tests/test_app_db_fallback_97.py:110,175 prove primary and second-fallback races, and tests/test_health_db.py passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087970471 -> 98bba2268d73475e985d07aae65210a0942f8237

Disposition: FIXED
Commit: 98bba2268d73475e985d07aae65210a0942f8237
Evidence: docs/deploy/OPERATIONAL_SIGNALS.md:506-529 now cites exact core/db.py, core/db_fallback.py and focused test file:line evidence for each lifecycle claim
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4087970480 -> 98bba2268d73475e985d07aae65210a0942f8237

Disposition: FIXED
Commit: 436153a9af4d56ce80b6a44e0e17c8d67cf89240
Evidence: core/db.py:873 validates the current async pair and constructs the session within both locks; tests/test_core_db_comprehensive.py:16 covers both async consumers with deterministic retirement before construction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4088162354 -> 436153a9af4d56ce80b6a44e0e17c8d67cf89240

Disposition: FIXED
Commit: 436153a9af4d56ce80b6a44e0e17c8d67cf89240
Evidence: core/db_fallback.py:240 captures expected prior engine/selector before preparation and rejects stale publication; tests/test_app_db_fallback_97.py:55 proves a newer explicit generation wins
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4088162359 -> 436153a9af4d56ce80b6a44e0e17c8d67cf89240

Disposition: FIXED
Commit: 436153a9af4d56ce80b6a44e0e17c8d67cf89240
Evidence: core/db.py:335 shares in-flight SQLite candidate protection with fallback; core/db_fallback.py:240 holds it through publication decision; tests/test_app_db_fallback_97.py:55 proves retirement cannot unlink the candidate file
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#discussion_r4088162364 -> 436153a9af4d56ce80b6a44e0e17c8d67cf89240

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: Sourcery reviewer guide companion issue r4081532965 fixed by explicit SQLite parent regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5793349486 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: Companion Sourcery inline r4081532965 fixed by explicit SQLite parent regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5289891178 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: Companion CodeRabbit inline roots r4081604263/r4081604273/r4081604279/r4081604305 fixed in DB and test material
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5289985408 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: f0b7dcedd11ac1d0951b7195659376279a4f642b
Evidence: Companion Codex inline r4081611190 fixed by same-file SQLite cleanup regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5289994316 -> f0b7dcedd11ac1d0951b7195659376279a4f642b

Disposition: FIXED
Commit: e50b8f20d66aed4920e0a9aa9bd8248889d26106
Evidence: Companion Codex inline r4081981013 fixed by final lock-held generation checks
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5290435346 -> e50b8f20d66aed4920e0a9aa9bd8248889d26106

Disposition: FIXED
Commit: ab40718c2912f36de317ff8e9c70b4500916dd47
Evidence: Companion Codex inline r4083683057 fixed by driver-qualified same-file SQLite regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5292473782 -> ab40718c2912f36de317ff8e9c70b4500916dd47

Disposition: FIXED
Commit: 5b09c9b0c7d7148245fcd645a37ab2c6c410299e
Evidence: Companion CodeRabbit inline r4084151967 fixed by real URI decoy and strict cleanup identity tests
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5293016361 -> 5b09c9b0c7d7148245fcd645a37ab2c6c410299e

Disposition: FIXED
Commit: 56f296bd124b142c2035b8445f2373b9401ed80c
Evidence: Review summary points to three core/db.py findings r4087415578, r4087415583 and r4087415588; all fixed by core/db.py:1046-1137 and deterministic tests at tests/test_db_engine_reuse_diff_coverage.py:544,607,802.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5296911459 -> 56f296bd124b142c2035b8445f2373b9401ed80c

Disposition: FIXED
Commit: f9fba67f95128408b8297a90c2d7fe781ab11c8f
Evidence: Review summary points to fallback generation finding r4087701318; core/db_fallback.py:209-218 and tests/test_app_db_fallback_97.py:110 fix and prove it
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5297251796 -> f9fba67f95128408b8297a90c2d7fe781ab11c8f

Disposition: FIXED
Commit: 98bba2268d73475e985d07aae65210a0942f8237
Evidence: Review summary points to roots r4087970471 and r4087970480, fixed in core/db_fallback.py:300, tests/test_app_db_fallback_97.py:175 and docs/deploy/OPERATIONAL_SIGNALS.md:506
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5297567115 -> 98bba2268d73475e985d07aae65210a0942f8237

Disposition: FIXED
Commit: 436153a9af4d56ce80b6a44e0e17c8d67cf89240
Evidence: Review summary points to roots r4088162354, r4088162359 and r4088162364; code and deterministic tests at core/db.py:335,873, core/db_fallback.py:240, tests/test_core_db_comprehensive.py:16 and tests/test_app_db_fallback_97.py:55 fix them
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#pullrequestreview-5297782806 -> 436153a9af4d56ce80b6a44e0e17c8d67cf89240

Disposition: NOT-A-BUG
Evidence: Codex review activity summary names the latest head and contains no independent code finding; companion inline roots have their own FIXED dispositions.
Reason: The issue comment is status metadata, with no separate requested code change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5793349656

Disposition: NOT-A-BUG
Evidence: CodeRabbit auto-pause and change-stack summary contains no independent defect; actionable companion review and inline roots are mapped separately.
Reason: The issue comment reports review status and duplicates mapped review roots.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5793350578

Disposition: NOT-A-BUG
Evidence: Codecov comment was created 2026-09-23T11:23:41Z for historical PR material; current-head CI run 35939313949 diff-coverage job 107452901388 reports Total 338, Missing 10, Coverage 97% on head d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3
Reason: Historical patch-coverage comment no longer describes the current material; the canonical current-head diff-coverage >=97 gate passed without weakening selection or threshold
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5793939789

Disposition: NOT-A-BUG
Evidence: GitHub issue comment body contains only a Codex review usage-limit notice and no code finding; no provider review or PASS is claimed
Reason: Informational provider quota notice; current-head CI, self-review, security, mapping and review-thread gates remain independently required
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5804659717

Disposition: NOT-A-BUG
Evidence: GitHub issue comment body contains only a Codex review usage-limit notice and no code finding; no provider review or PASS is claimed
Reason: Informational provider quota notice; current-head CI, self-review, security, mapping and review-thread gates remain independently required
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5804810448

Disposition: NOT-A-BUG
Evidence: GitHub issue comment body contains only a Codex review usage-limit notice and no code finding; no provider review or PASS is claimed
Reason: Informational provider quota notice; current-head CI, self-review, security, mapping and review-thread gates remain independently required
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5805021221

Disposition: NOT-A-BUG
Evidence: GitHub issue comment is only a Codex code-review usage-limit notice and contains no code finding; provider output remains unavailable and no PASS is claimed
Reason: Informational provider quota notice, not a current code defect; current-head CI, repo-native self-review, security, mapping and thread gates remain independently required
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2405#issuecomment-5805320408

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:18678fcd4e2d9f625301f3626451dbc85c16017738b2efe8ea9fdd01ccfd872e","material_head_sha":"d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"cc74f17b124b72a84c2e51e0b1310238f1538906","blocking":false,"head_revision":"d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","material_digest":"sha256:18678fcd4e2d9f625301f3626451dbc85c16017738b2efe8ea9fdd01ccfd872e","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"cc74f17b124b72a84c2e51e0b1310238f1538906","digest":"sha256:18678fcd4e2d9f625301f3626451dbc85c16017738b2efe8ea9fdd01ccfd872e","material_head_sha":"d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","merge_base_sha":"cc74f17b124b72a84c2e51e0b1310238f1538906","policy_version":"pulseplate.material-classification/v1"},"pr_number":2405,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:18678fcd4e2d9f625301f3626451dbc85c16017738b2efe8ea9fdd01ccfd872e","material_head_sha":"d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","report_payload":{"actionable_findings_count":0,"base_ref_oid":"cc74f17b124b72a84c2e51e0b1310238f1538906","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":""},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 3727 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-24T05:17:27Z","material_digest":"sha256:18678fcd4e2d9f625301f3626451dbc85c16017738b2efe8ea9fdd01ccfd872e","material_head_sha":"d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","merge_base_sha":"cc74f17b124b72a84c2e51e0b1310238f1538906","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"cc74f17b124b72a84c2e51e0b1310238f1538906..d8650d4f8aaa8cb6e945bd4c26830e53c0b7cab3","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2405_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/ci.yml",".secrets.baseline","app/models/rag_feedback.py","core/AGENTS.md","core/db.py","core/db_fallback.py","docs/deploy/OPERATIONAL_SIGNALS.md","docs/roadmap/BACKLOG_LEDGER.md","tests/test_app_db_fallback_97.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_core_db_async_optional.py","tests/test_core_db_comprehensive.py","tests/test_core_db_missing_coverage.py","tests/test_db_engine_reuse_diff_coverage.py","tests/test_db_missing_lines_coverage.py","tests/test_pgvector_compat.py","tests/test_remaining_modules.py","tests/test_shoplist_day_db_wiring.py","tests/test_total_coverage_boost_core_hotspots.py"],"diff_summary":{"additions":3157,"changed_lines":3727,"deletions":570,"files":19},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","app/AGENTS.md","core/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:3e4d04c62b57c226d7906a5e4885ea5bc623e0af9e552375343baeb4f5092f17","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
