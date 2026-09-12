# PR 2390 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/efed19b7c4b0.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/pr-2390-publication-governance-v5-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 7d98caa85fd3ee7299ddcc6654e369038229245c
Evidence: .github/workflows/cd.yml exports buildkit_version from the closed manifest; deploy/postgres-pgvector/image-manifest.json binds buildkit_version 0.32.2.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3993182804 -> 7d98caa85fd3ee7299ddcc6654e369038229245c

Disposition: FIXED
Commit: 7d98caa85fd3ee7299ddcc6654e369038229245c
Evidence: tests/test_deploy_contract_scripts.py plants unowned.apk after acquisition creates builder-apks/x86_64 and asserts APK repository file set drifted.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3993182810 -> 7d98caa85fd3ee7299ddcc6654e369038229245c

Disposition: FIXED
Commit: 12952f9984632c400c2ad32d825af29e75b57ce7
Evidence: .pre-commit-config.yaml:17 adds --enforce-all to the exact signed-index hook; tests/test_deploy_contract_scripts.py:8511 and native-file-size-hook-regression.json prove modified oversize index rejection, admitted index acceptance and unchanged 500 KB unrelated-file limit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3995923138 -> 12952f9984632c400c2ad32d825af29e75b57ce7

Disposition: FIXED
Commit: 12952f9984632c400c2ad32d825af29e75b57ce7
Evidence: tests/test_docker_workflow_build_path_contract.py:725 extracts the PCRE2 guard and requires the complete negated comparator plus exit 1; final-review-regressions.log records the focused passing regression.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3995923146 -> 12952f9984632c400c2ad32d825af29e75b57ce7

Disposition: FIXED
Commit: 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e
Evidence: docs/security/MAIN_RECOVERY_1_CONTAINER_PUBLICATION.md now points to the exact assertions at tests/test_deploy_contract_scripts.py:8511, Dockerfile:323 and tests/test_docker_workflow_build_path_contract.py:731; Docs Phase 1 and diff checks pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3996067186 -> 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e

Disposition: FIXED
Commit: 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e
Evidence: Eight test docstrings were added in 12952f9984632c400c2ad32d825af29e75b57ce7; the newly introduced read_regular helper in .github/workflows/cd.yml:1120 is documented in this commit. final-docstring-commit-census-binding.json binds the complete local qualified census (18/18 changed Python functions including heredocs) to this commit. The proprietary CodeRabbit denominator 29 and its displayed percentage are not independently reproduced or claimed cleared.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#issuecomment-5640240984 -> 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e

Disposition: FIXED
Commit: 7d98caa85fd3ee7299ddcc6654e369038229245c
Evidence: Both CodeRabbit inline findings from this review are fixed in 7d98caa85fd3ee7299ddcc6654e369038229245c: BuildKit version bind and extra-file APK fixture.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#pullrequestreview-5183199737 -> 7d98caa85fd3ee7299ddcc6654e369038229245c

Disposition: FIXED
Commit: 12952f9984632c400c2ad32d825af29e75b57ce7
Evidence: .pre-commit-config.yaml:17 enforces modified signed-index size; tests/test_docker_workflow_build_path_contract.py:725 asserts the full PCRE2 rejection guard; .github/workflows/cd.yml:929 consumes manifest-bound BUILDX_VERSION for acquisition/runtime verification and both provenance URL consumers. Executed setup regression rejects mismatch, missing and malformed versions; 24 focused regressions and actionlint pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#pullrequestreview-5186130312 -> 12952f9984632c400c2ad32d825af29e75b57ce7

Disposition: FIXED
Commit: 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e
Evidence: The recovery document assertion anchors were corrected for discussion_r3996067186. The other root discussion_r3996067183 is separately NOT-A-BUG with pinned v1.5.0 upstream hook/write-path evidence: serialization rationale is correct and remains unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#pullrequestreview-5186283030 -> 787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e

Disposition: NOT-A-BUG
Evidence: deploy/postgres-pgvector/Containerfile:32
Reason: Alpine apk verify checks the signed index and package files, not only already-installed packages. This line is the fail-closed check before offline apk add.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3993131283

Disposition: NOT-A-BUG
Evidence: .pre-commit-config.yaml:35; https://github.com/Yelp/detect-secrets/blob/v1.5.0/detect_secrets/pre_commit_hook.py#L47-L64 and https://github.com/Yelp/detect-secrets/blob/v1.5.0/detect_secrets/core/baseline.py record the pinned update and whole-file save path.
Reason: The pinned detect-secrets-hook can update baseline metadata, save the whole baseline and return 3. Parallel file batches can overwrite each other; require_serial serializes this one invocation. The documentation already excludes independent processes/worktrees and does not claim the cause of every historical baseline change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#discussion_r3996067183

Disposition: NOT-A-BUG
Evidence: deploy/postgres-pgvector/Containerfile:32
Reason: The Sourcery review repeats the apk verify index-gate claim already answered as NOT-A-BUG; local dual builds reproduced platform digest sha256:06c914735c70f82424a2a9b1e57790590a21d0fbfe250504ff79a1cca2559380.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2390#pullrequestreview-5183145906

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:11df903d5c5f345a11971312301656ddeb6d43ac667cda0db6a8abc4cae70650","material_head_sha":"787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323","blocking":false,"head_revision":"787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","material_digest":"sha256:11df903d5c5f345a11971312301656ddeb6d43ac667cda0db6a8abc4cae70650","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323","digest":"sha256:11df903d5c5f345a11971312301656ddeb6d43ac667cda0db6a8abc4cae70650","material_head_sha":"787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","merge_base_sha":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323","policy_version":"pulseplate.material-classification/v1"},"pr_number":2390,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:11df903d5c5f345a11971312301656ddeb6d43ac667cda0db6a8abc4cae70650","material_head_sha":"787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","report_payload":{"actionable_findings_count":0,"base_ref_oid":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/efed19b7c4b0.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"efed19b7c4b0"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1055 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-12T12:52:57Z","material_digest":"sha256:11df903d5c5f345a11971312301656ddeb6d43ac667cda0db6a8abc4cae70650","material_head_sha":"787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","merge_base_sha":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"c845a7e5e6a8af4c0678608c8d3996dafe1ae323..787fc1bf01d1b6a3f4df4ca9e5507c6a4fa9d63e","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2390_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/cd.yml",".pre-commit-config.yaml",".secrets.baseline","Dockerfile","deploy/AGENTS.md","deploy/docker-compose.production.selfhosted.yaml","deploy/docker-compose.staging.yaml","deploy/postgres-pgvector/Containerfile","deploy/postgres-pgvector/builder-apk-index.tar.gz","deploy/postgres-pgvector/builder-apk-inputs.tsv","deploy/postgres-pgvector/image-manifest.json","docs/roadmap/BACKLOG_LEDGER.md","docs/security/MAIN_RECOVERY_1_CONTAINER_PUBLICATION.md","scripts/deploy.sh","scripts/deploy_production.sh","tests/test_deploy_contract_scripts.py","tests/test_docker_workflow_build_path_contract.py","tests/test_pgvector_compat.py"],"diff_summary":{"additions":960,"changed_lines":1055,"deletions":95,"files":18},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:1c420267c926e23a10b2dbca8f1512044af7b44e61d5afdf3094bccda8fa8cf8","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
