# PR 2347 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/a17be0c6d330.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/prod-obs1-pgvector-final-d51f4d28-v2-post-probe-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: CD package identity checks use the owner-scoped public package endpoint with the explicitly bound release context
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809967 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a
Evidence: Provenance reuse normalization removes commit-varying source_sha while preserving material conflict detection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809978 -> 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a

Disposition: FIXED
Commit: 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a
Evidence: Deployment regression asserts the full inspected old PostgreSQL container identity is not stopped on pre-switch failure
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3875809990 -> 57f62dd0454db69f1fc4fd389ff7c0fd4f308c2a

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: PostgreSQL reuse job timeout is 90 minutes and deterministically covers its 60-minute wait plus scan and verification tail
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3878161130 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: Containerfile sets and verifies the installed pgvector LICENSE mtime against SOURCE_DATE_EPOCH
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880744505 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: PGvector contract test scopes platform digest evidence to contract and publisher job boundaries instead of the whole workflow
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3880744522 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: c091ff3db3e064c736b0166e04ec5325f4d7b9d1
Evidence: .github/workflows/cd.yml post-promotion exact-main fence plus canonical-tag supersession regression
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3886123118 -> c091ff3db3e064c736b0166e04ec5325f4d7b9d1

Disposition: FIXED
Commit: f411493f0781d9a2cc8f880c89c6885243efbf94
Evidence: Staging and self-hosted deploy paths perform a second definitive volume census immediately before the single PostgreSQL start
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887313894 -> f411493f0781d9a2cc8f880c89c6885243efbf94

Disposition: FIXED
Commit: 59bc354fb1050829a320fa0f96cccb099d7b691a
Evidence: Shallow fallback fetches execute only in an isolated temporary bare Git repository
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887551520 -> 59bc354fb1050829a320fa0f96cccb099d7b691a

Disposition: FIXED
Commit: 1f0ad5df0373ba035b98280deef08fa50162fe9c
Evidence: Compatibility admission uses only credential-free repository variables and rejects secrets.* or DEVPI_CI_* reintroduction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#discussion_r3887759530 -> 1f0ad5df0373ba035b98280deef08fa50162fe9c

Disposition: FIXED
Commit: 7e74dd6fd8215a31ab48b775e9a5c7be031d3dbf
Evidence: Production bundle and deploy contract bind the reviewed scripts/ops/postgres_backup.sh helper before self-hosted cutover
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5045531851 -> 7e74dd6fd8215a31ab48b775e9a5c7be031d3dbf

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: Consolidated CodeRabbit package, provenance, container-identity, and release-context review findings are covered by the reviewed workflow and tests
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5045605961 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2
Evidence: SPDX reuse omits current source-digest binding and read-only admission has bounded non-cancelling concurrency evidence
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5047946377 -> e1c79a6f74bcee69608d7f3d83ac4a1abf451ec2

Disposition: FIXED
Commit: d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19
Evidence: The sole actionable timeout finding is fixed and guarded by the closed reuse-state-machine contract test
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5048191394 -> d1f308ee8bfe5b2c4705ffdcd0b2ba9b4511dd19

Disposition: FIXED
Commit: 4646e7053a6b43355f37fe818d169ce91e939835
Evidence: Both actionable LICENSE reproducibility and publisher-scoped digest assertions are fixed with exact regression coverage
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5051266573 -> 4646e7053a6b43355f37fe818d169ce91e939835

Disposition: FIXED
Commit: 829a5be64416191597ec7123c0eee34a4222e2f0
Evidence: Production archive regex now requires scripts/ops/postgres_backup.sh and deploy/postgres-pgvector/image-manifest.json in canonical order
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347#pullrequestreview-5055358328 -> 829a5be64416191597ec7123c0eee34a4222e2f0

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:64bf9f247b2b29099dc7c57d5e0efa333f266f33e4a898d95b771527a3172289","material_head_sha":"d51f4d28c166945a15e6de5e0ddb591642c6d543","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"a157d445c98c3e4bea76bd95c2a8d333c99725c1","blocking":false,"head_revision":"d51f4d28c166945a15e6de5e0ddb591642c6d543","material_digest":"sha256:64bf9f247b2b29099dc7c57d5e0efa333f266f33e4a898d95b771527a3172289","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"a157d445c98c3e4bea76bd95c2a8d333c99725c1","digest":"sha256:64bf9f247b2b29099dc7c57d5e0efa333f266f33e4a898d95b771527a3172289","material_head_sha":"d51f4d28c166945a15e6de5e0ddb591642c6d543","merge_base_sha":"a157d445c98c3e4bea76bd95c2a8d333c99725c1","policy_version":"pulseplate.material-classification/v1"},"pr_number":2347,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:64bf9f247b2b29099dc7c57d5e0efa333f266f33e4a898d95b771527a3172289","material_head_sha":"d51f4d28c166945a15e6de5e0ddb591642c6d543","report_payload":{"actionable_findings_count":0,"base_ref_oid":"a157d445c98c3e4bea76bd95c2a8d333c99725c1","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/a17be0c6d330.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"a17be0c6d330"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 7846 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-08-30T19:58:20Z","material_digest":"sha256:64bf9f247b2b29099dc7c57d5e0efa333f266f33e4a898d95b771527a3172289","material_head_sha":"d51f4d28c166945a15e6de5e0ddb591642c6d543","merge_base_sha":"a157d445c98c3e4bea76bd95c2a8d333c99725c1","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"a157d445c98c3e4bea76bd95c2a8d333c99725c1..d51f4d28c166945a15e6de5e0ddb591642c6d543","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2347_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/build.yml",".github/workflows/cd.yml",".github/workflows/ci.yml",".github/workflows/trivy.yml",".secrets.baseline","deploy/AGENTS.md","deploy/docker-compose.production.selfhosted.yaml","deploy/docker-compose.staging.yaml","deploy/postgres-pgvector/Containerfile","deploy/postgres-pgvector/image-manifest.json","docs/deploy/OPERATIONAL_SIGNALS.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/deploy.sh","scripts/deploy_production.sh","tests/AGENTS.md","tests/test_caddy_deploy_provenance.py","tests/test_canonical_application_lifespan.py","tests/test_cd_workflow_production_deploy_gate.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_deploy_contract_scripts.py","tests/test_design_automation_next_lane_docs.py","tests/test_pgvector_compat.py","tests/test_runtime_toolchain_alignment.py"],"diff_summary":{"additions":7634,"changed_lines":7846,"deletions":212,"files":23},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:9e842b665d5d06f932a1e3bb1f7166c2a02256a9f91879725c8707646de02db9","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
