# PR 2397 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/120be58006dd.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/ops01-base2401-oracle-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266
Evidence: docs/deploy/OPS_CONTEXT_SOURCES.json:55; test_real_catalogue_production_image_only_selfhosted verifies exact self-hosted production image metadata.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4004824775 -> 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266

Disposition: FIXED
Commit: 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266
Evidence: docs/deploy/OPS_CONTEXT_SOURCES.json:152; docs/orchestration/AGENT_CONTEXT_MAP.md; staging HBA fingerprint, production exclusion and actual source-byte delivery tests passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4004824783 -> 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266

Disposition: FIXED
Commit: 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266
Evidence: scripts/ops/ops_context_report.py:11 and :229 retain concrete PR-2397 references and original expiry; nosec, absolute-binary guards and Bandit passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4004824786 -> 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266

Disposition: FIXED
Commit: 9b103e1448d2d59839f700e3c946524bed7d2ef6
Evidence: docs/deploy/OPS_CONTEXT_SOURCES.json:232; test_real_catalogue_caddy_policy_selection_and_fingerprint verifies both exact app source sets, isolated fingerprints and missing-policy errors; all16 source bytes delivered.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4053397381 -> 9b103e1448d2d59839f700e3c946524bed7d2ef6

Disposition: FIXED
Commit: 9b103e1448d2d59839f700e3c946524bed7d2ef6
Evidence: scripts/ops/ops_context_report.py:230 requires HEAD^{commit}; test_native_git_requires_commit_head accepts attached/detached commits and rejects blob/tree/unborn/missing/dangling HEAD.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4053397386 -> 9b103e1448d2d59839f700e3c946524bed7d2ef6

Disposition: FIXED
Commit: 9b103e1448d2d59839f700e3c946524bed7d2ef6
Evidence: scripts/ops/ops_context_report.py:225 resolves Git only through fixed /usr/bin:/bin; test_caller_path_cannot_supply_git and test_missing_system_git_never_falls_back pass; OS trust boundary documented.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4053415287 -> 9b103e1448d2d59839f700e3c946524bed7d2ef6

Disposition: FIXED
Commit: 925ec0b812154732575e72fac9bf59949f1d8fa9
Evidence: scripts/ci/ci_risk_profile.py:90 and :116 admit the two exact OPS inputs. Ten isolated/companion/near-miss cases in tests/test_ci_risk_profile.py pass; full selector/workflow/absolute-subprocess bundle409 and validate-changed493 passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4053818218 -> 925ec0b812154732575e72fac9bf59949f1d8fa9

Disposition: FIXED
Commit: b3f9e84ea25fc4d4404e9ddc1c7189dd3b7f211e
Evidence: scripts/ops/ops_context_report.py:157 requires both production configurations for app/database/prometheus over validated rows. tests/test_ops_context_report.py six isolated omission cases first prove valid baseline, then safe rejection through exact alternate-index CLI for target and unrelated selectors. Four bypasses reproduced before fix;384-case focused bundle and127-case native producer passed. Existing runbook clarifies finite class coverage; shipped catalogue/packages/staging/custom-path behavior preserved.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4054448493 -> b3f9e84ea25fc4d4404e9ddc1c7189dd3b7f211e

Disposition: FIXED
Commit: 0ee56bd7db3800c6e2c4240207511149246cd404
Evidence: scripts/ops/ops_context_report.py:163 adds all four explicit staging service relations to the unified required ten-triple matrix. Ten isolated omission cases and shared-only staging regression reject through exact CLI with positive controls; shared rows cannot substitute, unselected invalid relations still reject.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4057899541 -> 0ee56bd7db3800c6e2c4240207511149246cd404

Disposition: FIXED
Commit: 0ee56bd7db3800c6e2c4240207511149246cd404
Evidence: scripts/ops/ops_context_report.py:94 admits paths through one canonical seam before any acquisition, rejecting casefolded secrets ancestor components for index/member/observed including unselected member paths. Twelve synthetic reader-spy cases prove denied targets never read and no payload/digest emitted; safe near-name/custom paths remain permitted. Shared reader unchanged and finite-path/caller-sanitization limits explicit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4057899543 -> 0ee56bd7db3800c6e2c4240207511149246cd404

Disposition: FIXED
Commit: 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266
Evidence: All three linked inline findings fixed: production image classification, staging HBA catalogue/context and concrete PR-2397 nosec references; focused tests and security guards passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5197249521 -> 826ae76dbac8c9ddf5f98abc2eba9e54fc9ac266

Disposition: FIXED
Commit: 9b103e1448d2d59839f700e3c946524bed7d2ef6
Evidence: Both linked inline findings fixed: environment-specific Caddy policies and native Git commit-type recognition; native/canonical-source tests passed in378-case bundle.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5255962162 -> 9b103e1448d2d59839f700e3c946524bed7d2ef6

Disposition: FIXED
Commit: 9b103e1448d2d59839f700e3c946524bed7d2ef6
Evidence: The sole linked Git lookup finding is fixed by explicit system-only lookup and child PATH, no fallback, native fake-PATH marker proof and documented OS trust assumptions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5255980622 -> 9b103e1448d2d59839f700e3c946524bed7d2ef6

Disposition: FIXED
Commit: 925ec0b812154732575e72fac9bf59949f1d8fa9
Evidence: The linked input-only routing omission is corrected by two exact memberships and ten regression cases; no broad prefix, classifier algorithm, docs-only semantics or threshold changes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5256461697 -> 925ec0b812154732575e72fac9bf59949f1d8fa9

Disposition: FIXED
Commit: b3f9e84ea25fc4d4404e9ddc1c7189dd3b7f211e
Evidence: scripts/ops/ops_context_report.py:157 requires both production configurations for app/database/prometheus over validated rows. tests/test_ops_context_report.py six isolated omission cases first prove valid baseline, then safe rejection through exact alternate-index CLI for target and unrelated selectors. Four bypasses reproduced before fix;384-case focused bundle and127-case native producer passed. Existing runbook clarifies finite class coverage; shipped catalogue/packages/staging/custom-path behavior preserved.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5257348785 -> b3f9e84ea25fc4d4404e9ddc1c7189dd3b7f211e

Disposition: FIXED
Commit: 0ee56bd7db3800c6e2c4240207511149246cd404
Evidence: Both linked staging-completeness and designated-secret-store acquisition findings are corrected by the unified ten-relation predicate and one report-owned path-admission seam. Tests-first17 failures reproduced;404 focused cases,147 native producer cases and519 validate-changed passed. No universal secret-content recognition or live authority claimed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5261553881 -> 0ee56bd7db3800c6e2c4240207511149246cd404

Disposition: NOT-A-BUG
Evidence: docs/deploy/OPS_CONTEXT_SOURCES.json:214 already includes both production and staging Prometheus Compose references; test_real_catalogue_prometheus_compose_owners passes for both environments.
Reason: The requested references already existed at the reviewed original head; current exact-source tests and actual index rows contradict the omission claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#discussion_r4004783287

Disposition: NOT-A-BUG
Evidence: .pre-commit-config.yaml:149 keeps pydocstyle manual-only; .coderabbit.yaml:19 and :35 require 97 percent test coverage, not an 80 percent docstring threshold. Full-body assessment and classifier observation are recorded in acceptance-routing-current.md; new contract tests retain descriptive names and docstrings.
Reason: The current CodeRabbit footer is an advisory docstring metric, not a configured repository gate or an independent functional/security defect. The complete comment states no actionable comments, and the actual current readiness classifier returns non-actionable. This disposition does not claim that the warning is absent or that any provider passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#issuecomment-5663358424

Disposition: NOT-A-BUG
Evidence: docs/deploy/OPS_CONTEXT_SOURCES.json:214 already includes both production and staging Prometheus Compose references; test_real_catalogue_prometheus_compose_owners passes for both environments.
Reason: The requested references already existed at the reviewed original head; current exact-source tests and actual index rows contradict the omission claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2397#pullrequestreview-5197190338

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:92055624a38d5cf556359267d6d0636930d49396300d545ccc26f27ff9239aad","material_head_sha":"e902235f47b80201262af01ab51724f7dac5a0e8","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"bcaf6d03c1746886e522f2ac24485338b4ec6e92","blocking":false,"head_revision":"e902235f47b80201262af01ab51724f7dac5a0e8","material_digest":"sha256:92055624a38d5cf556359267d6d0636930d49396300d545ccc26f27ff9239aad","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"bcaf6d03c1746886e522f2ac24485338b4ec6e92","digest":"sha256:92055624a38d5cf556359267d6d0636930d49396300d545ccc26f27ff9239aad","material_head_sha":"e902235f47b80201262af01ab51724f7dac5a0e8","merge_base_sha":"bcaf6d03c1746886e522f2ac24485338b4ec6e92","policy_version":"pulseplate.material-classification/v1"},"pr_number":2397,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:92055624a38d5cf556359267d6d0636930d49396300d545ccc26f27ff9239aad","material_head_sha":"e902235f47b80201262af01ab51724f7dac5a0e8","report_payload":{"actionable_findings_count":0,"base_ref_oid":"bcaf6d03c1746886e522f2ac24485338b4ec6e92","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/120be58006dd.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"120be58006dd"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 2383 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-23T06:47:29Z","material_digest":"sha256:92055624a38d5cf556359267d6d0636930d49396300d545ccc26f27ff9239aad","material_head_sha":"e902235f47b80201262af01ab51724f7dac5a0e8","merge_base_sha":"bcaf6d03c1746886e522f2ac24485338b4ec6e92","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"bcaf6d03c1746886e522f2ac24485338b4ec6e92..e902235f47b80201262af01ab51724f7dac5a0e8","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2397_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".cursor/agents/dev-operator.md",".github/workflows/ci.yml","docs/deploy/OPERATIONAL_SIGNALS.md","docs/deploy/OPS_CONTEXT_SOURCES.json","docs/orchestration/AGENT_CONTEXT_MAP.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/ci/ci_risk_profile.py","scripts/ops/ops_context_report.py","tests/AGENTS.md","tests/test_ci_risk_profile.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_ops_context_report.py"],"diff_summary":{"additions":2382,"changed_lines":2383,"deletions":1,"files":12},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":[".cursor/agents/AGENTS.md","AGENTS.md","docs/orchestration/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:37681722de7dab8cf716ae9d36fea6cfb79a61d1200d7e2b273238fc4a21d9da","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
