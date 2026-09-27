# PR 2443 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/ops03b-expanded-runtime.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/ops03b-final-material-oracle.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: f2f21816f8794aa89342008e0ea12326fa218489
Evidence: scripts/deploy_production.sh:799 and tests/test_deploy_contract_scripts.py:7142; frozen current admission is implemented in both deploy paths and full-path positives/negatives pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#discussion_r4112687790 -> f2f21816f8794aa89342008e0ea12326fa218489

Disposition: FIXED
Commit: f2f21816f8794aa89342008e0ea12326fa218489
Evidence: scripts/deploy.sh:515 and scripts/deploy_production.sh:859 require exactly one canonical Env entry; tests/test_deploy_contract_scripts.py:9213 rejects conflicting and duplicate values.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#discussion_r4112691039 -> f2f21816f8794aa89342008e0ea12326fa218489

Disposition: FIXED
Commit: d3e0b0d34e15105838eabffd505984a0b9a1618b
Evidence: tests/test_deploy_contract_scripts.py:7416 extracts complete shell functions, includes late RepoDigests predicate and detects a deliberate mutation; focused parity and validate-changed pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#discussion_r4115786432 -> d3e0b0d34e15105838eabffd505984a0b9a1618b

Disposition: FIXED
Commit: 46f53a73b29fa6c079df026fb194b4b080f988a9
Evidence: scripts/deploy.sh:682 and scripts/deploy_production.sh:2247 correct the summary frozen-ref portability finding. The 80 percent docstring item is advisory documentation style, not repository code coverage; contract runbooks and full-path tests describe behavior without repetitive test docstrings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#issuecomment-5849631825 -> 46f53a73b29fa6c079df026fb194b4b080f988a9

Disposition: FIXED
Commit: f2f21816f8794aa89342008e0ea12326fa218489
Evidence: scripts/deploy_production.sh:799 and tests/test_deploy_contract_scripts.py:7142 correct the production divergence reported by the review inline root.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#pullrequestreview-5327328463 -> f2f21816f8794aa89342008e0ea12326fa218489

Disposition: FIXED
Commit: f2f21816f8794aa89342008e0ea12326fa218489
Evidence: scripts/deploy.sh:515 and scripts/deploy_production.sh:859 reject duplicate required Env entries; full-path negative matrix passes before writer shutdown.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#pullrequestreview-5327331747 -> f2f21816f8794aa89342008e0ea12326fa218489

Disposition: FIXED
Commit: d3e0b0d34e15105838eabffd505984a0b9a1618b
Evidence: tests/test_deploy_contract_scripts.py:7416 checks complete parser bodies and late-predicate mutation; focused parity and full deploy-contract tests pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#pullrequestreview-5330769081 -> d3e0b0d34e15105838eabffd505984a0b9a1618b

Disposition: FIXED
Commit: 46f53a73b29fa6c079df026fb194b4b080f988a9
Evidence: scripts/deploy.sh:682 and scripts/deploy_production.sh:2247 inspect exact frozen ref while checking captured container.Image equality; tests/test_deploy_contract_scripts.py:7142,9055,9107 cover exact ref calls and refusal before effects; local narrow bundle and current-head CI substantive jobs pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#pullrequestreview-5331061703 -> 46f53a73b29fa6c079df026fb194b4b080f988a9

Disposition: NOT-A-BUG
Evidence: PR scope and scripts/deploy.sh:682 preserve closed identity binding; human exact-head squash approval and any later host deployment approval remain mandatory.
Reason: The assessment requests human review but identifies no additional code defect; procedural self-review and separate owner merge decision preserve that boundary.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2443#pullrequestreview-5327323749

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:36c31f374879dcf610fb074d30a7bbf824ba383727ef74f7a10ba6db835d1174","material_head_sha":"5505bb4c0b91d265f66dc472060281f1ed5c60d4","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"4e32408e930a2c1b71944c59ca46254eb8f4a055","blocking":false,"head_revision":"5505bb4c0b91d265f66dc472060281f1ed5c60d4","material_digest":"sha256:36c31f374879dcf610fb074d30a7bbf824ba383727ef74f7a10ba6db835d1174","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"4e32408e930a2c1b71944c59ca46254eb8f4a055","digest":"sha256:36c31f374879dcf610fb074d30a7bbf824ba383727ef74f7a10ba6db835d1174","material_head_sha":"5505bb4c0b91d265f66dc472060281f1ed5c60d4","merge_base_sha":"4e32408e930a2c1b71944c59ca46254eb8f4a055","policy_version":"pulseplate.material-classification/v1"},"pr_number":2443,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:36c31f374879dcf610fb074d30a7bbf824ba383727ef74f7a10ba6db835d1174","material_head_sha":"5505bb4c0b91d265f66dc472060281f1ed5c60d4","report_payload":{"actionable_findings_count":0,"base_ref_oid":"4e32408e930a2c1b71944c59ca46254eb8f4a055","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":""},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1006 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-27T19:53:22Z","material_digest":"sha256:36c31f374879dcf610fb074d30a7bbf824ba383727ef74f7a10ba6db835d1174","material_head_sha":"5505bb4c0b91d265f66dc472060281f1ed5c60d4","merge_base_sha":"4e32408e930a2c1b71944c59ca46254eb8f4a055","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"4e32408e930a2c1b71944c59ca46254eb8f4a055..5505bb4c0b91d265f66dc472060281f1ed5c60d4","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2443_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".secrets.baseline","docs/deploy/POSTGRES_SELF_HOSTED_DROPLET.md","docs/deploy/STAGING.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/deploy.sh","scripts/deploy_production.sh","tests/test_deploy_contract_scripts.py"],"diff_summary":{"additions":966,"changed_lines":1006,"deletions":40,"files":7},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:28830e4ac5e3ba9f26800cc9766a0f84fad2aa9543fcebf560b16307791bfd91","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
