# PR 2308 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/496c1ff5443f.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/er-p6-preopen-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 2875e2b6962af2b33b0c424bd1d12c96a685b93f
Evidence: docs/roadmap/BACKLOG_LEDGER.md:11670-11682 now distinguishes merged PR #2299 capability delivery from active PR #2308 ER-P6 execution, preserves ER-P5 as a historical pre-generation governance stop, and keeps the one-off/no-further-substitute boundary; commit 2875e2b6962af2b33b0c424bd1d12c96a685b93f is a non-empty ledger-only fix made after the review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#discussion_r3826551025 -> 2875e2b6962af2b33b0c424bd1d12c96a685b93f

Disposition: FIXED
Commit: 2875e2b6962af2b33b0c424bd1d12c96a685b93f
Evidence: docs/roadmap/BACKLOG_LEDGER.md:11670-11682 now distinguishes merged PR #2299 capability delivery from active PR #2308 ER-P6 execution, preserves ER-P5 as a historical pre-generation governance stop, and keeps the one-off/no-further-substitute boundary; commit 2875e2b6962af2b33b0c424bd1d12c96a685b93f is a non-empty ledger-only fix made after the review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#pullrequestreview-4988897024 -> 2875e2b6962af2b33b0c424bd1d12c96a685b93f

Disposition: NOT-A-BUG
Evidence: core/rag/recursive_retrieval.py:350-366 stores an isolated snapshot and returns copies on hits; core/rag/recursive_retrieval.py:463-486 only reads the miss result and constructs new RAGChunk values; the exact ER-P6 mutation-isolation/public-parity probe and 420-test bundle passed on head 02572cade562ed81902a9adcb9caf68d55595f31.
Reason: The miss path returns the fresh retriever-owned context while the request-local cache owns a distinct snapshot, so the sole caller cannot mutate the stored cache value.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#discussion_r3826454250

Disposition: NOT-A-BUG
Evidence: core/rag/recursive_retrieval.py:355-366 stores the same isolated snap object that put() returns; core/rag/recursive_retrieval.py:389-404 returns copies on hits and the independent fresh retriever context on misses; the exact ER-P6 mutation-isolation/public-parity probe and 420-test bundle passed on head 02572cade562ed81902a9adcb9caf68d55595f31.
Reason: Returning hop_vector_cache.put(key, ctx) would expose the object stored inside the cache; the implemented miss return keeps the stored snapshot isolated and removes only the redundant second copy.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#discussion_r3826463159

Disposition: NOT-A-BUG
Evidence: core/rag/recursive_retrieval.py:350-366 stores an isolated snapshot and returns copies on hits; core/rag/recursive_retrieval.py:463-486 only reads the miss result and constructs new RAGChunk values; the exact ER-P6 mutation-isolation/public-parity probe and 420-test bundle passed on head 02572cade562ed81902a9adcb9caf68d55595f31.
Reason: The top-level review carries the same bounded cache-miss identity: the returned fresh context and stored request-local snapshot are different objects, and the sole caller is read-only.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#pullrequestreview-4988783933

Disposition: NOT-A-BUG
Evidence: core/rag/recursive_retrieval.py:355-366 stores the same isolated snap object that put() returns; core/rag/recursive_retrieval.py:389-404 returns copies on hits and the independent fresh retriever context on misses; the exact ER-P6 mutation-isolation/public-parity probe and 420-test bundle passed on head 02572cade562ed81902a9adcb9caf68d55595f31.
Reason: The top-level review carries the same bounded identity; its suggested put() return would expose the cached snapshot, while the implemented path preserves cache ownership and hit isolation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2308#pullrequestreview-4988792611

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:3a2f361942d4282c46b31bc08c2d65b938e5b4683a6c33e7e8f9e2087277ee9b","material_head_sha":"02572cade562ed81902a9adcb9caf68d55595f31","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"39c823179710aa7c1b5f32a06974fb6c9e3531cb","blocking":false,"head_revision":"02572cade562ed81902a9adcb9caf68d55595f31","material_digest":"sha256:3a2f361942d4282c46b31bc08c2d65b938e5b4683a6c33e7e8f9e2087277ee9b","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"39c823179710aa7c1b5f32a06974fb6c9e3531cb","digest":"sha256:3a2f361942d4282c46b31bc08c2d65b938e5b4683a6c33e7e8f9e2087277ee9b","material_head_sha":"02572cade562ed81902a9adcb9caf68d55595f31","merge_base_sha":"39c823179710aa7c1b5f32a06974fb6c9e3531cb","policy_version":"pulseplate.material-classification/v1"},"pr_number":2308,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":0,"material_digest":"sha256:3a2f361942d4282c46b31bc08c2d65b938e5b4683a6c33e7e8f9e2087277ee9b","material_head_sha":"02572cade562ed81902a9adcb9caf68d55595f31","report_payload":{"actionable_findings_count":0,"base_ref_oid":"39c823179710aa7c1b5f32a06974fb6c9e3531cb","calibration":{"case_labels":["clean-context","review-source-degraded"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/496c1ff5443f.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"496c1ff5443f"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[],"findings_count":0,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop"],"generated_at_utc":"2026-08-21T06:22:56Z","material_digest":"sha256:3a2f361942d4282c46b31bc08c2d65b938e5b4683a6c33e7e8f9e2087277ee9b","material_head_sha":"02572cade562ed81902a9adcb9caf68d55595f31","merge_base_sha":"39c823179710aa7c1b5f32a06974fb6c9e3531cb","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"39c823179710aa7c1b5f32a06974fb6c9e3531cb..02572cade562ed81902a9adcb9caf68d55595f31","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2308_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter has no deterministic findings from the supplied context."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["core/rag/recursive_retrieval.py","docs/roadmap/BACKLOG_LEDGER.md"],"diff_summary":{"additions":9,"changed_lines":18,"deletions":9,"files":2},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","core/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:1d39c05f78f13ad173ab60062d36c046962cb79f3464f9e88e9897c03cffd393","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
