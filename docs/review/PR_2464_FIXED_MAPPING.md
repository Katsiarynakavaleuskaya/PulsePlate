# PR 2464 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/935f78a88e54.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/oracle_attachments/79a53e3a7fab84651f1ad49167488797ebe411fbd38a0a06c13ee23acd89205e/result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: scripts/orchestration/render_codex_start_prompt.py:620 selects Apple Container on Darwin and an explicit compatible-backend placeholder elsewhere; tests/test_render_codex_start_prompt.py:1916 covers both host recipes. Mac experiments remain explicit Apple Container.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149428996 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: scripts/orchestration/pr_oracle_attachment.py:1214 holds the shared restore-root cooperative lock across inventory/capacity admission and mkdir; tests/test_pr_oracle_attachment.py:1957 exercises two admissions at capacity31.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149429006 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: scripts/orchestration/pr_oracle_attachment.py:256 and qoder_dispatch_bridge.py:2954 handle the specific DispatchError without a broad RuntimeError catch; tests/test_pr_oracle_attachment.py:1895 and :2298, tests/test_qoder_dispatch_bridge.py:5619 cover structured CLI rejection and visible programming errors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149433587 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: scripts/orchestration/pr_oracle_attachment.py:977 publishes screened ref/hash dependency projections and preserves immutable binary/private companions, without a global privacy exemption; tests/test_pr_oracle_attachment.py:1926 and current ADC archive/download/36member/fresh historical restore prove the owning path. CLI json.dumps is JSON serialization; Flask jsonify is inapplicable.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149433598 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: scripts/orchestration/pr_oracle_attachment.py:215 plus scripts/AGENTS.md externally admit trusted T, distinct canonical M and clean absolute Python before -I/Tcwd startup; separate frozen guest controls and material remain bound. tests/test_pr_oracle_attachment.py:2000 and actual G34/G35/currentADC prove poison remains data. Fingerprints/flags do not authenticate hostile sameUID or human authority.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149463815 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: adc7ea73186ab3b0b228e9619db9b283e00c3d52
Evidence: .agents/skills/pulseplate-orchestration-dispatch/SKILL.md:108 defines the emitted TRUSTED_TOOL_ROOT and MATERIAL_ROOT names. Ancillary OH1/AS3 scanner assertions are unsupported on the cited path: existing experiment_runner_pr_creative_context.py:819 validates bounded native JSON before use; rules/context-loading.md:18 selects concrete admitted repo instructions without installed-skill enumeration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4159242136 -> adc7ea73186ab3b0b228e9619db9b283e00c3d52

Disposition: FIXED
Commit: d335e15a0637518d611f25ef4dadf2a0a678551e
Evidence: scripts/orchestration/pr_oracle_attachment.py:260 cross-binds both already captured nominal repository identities with existing casefold semantics before execution/retention. tests/test_pr_oracle_attachment.py:908 and :953 reject foreign origins and origin drift before reuse/delivery; nominal equality does not authenticate remote membership.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4159247903 -> d335e15a0637518d611f25ef4dadf2a0a678551e

Disposition: FIXED
Commit: d335e15a0637518d611f25ef4dadf2a0a678551e
Evidence: scripts/orchestration/experiment_runner_dispatch.py:1706 reconciles native NUL nonignored untracked inventory with all-and-only explicit admissions before snapshot. tests/test_experiment_runner_dispatch.py:150, :194, :231 and tests/test_pr_oracle_attachment.py:930, :953 cover omissions, literal names, drift and probe failure while preserving proofless manual defaults.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4159247921 -> d335e15a0637518d611f25ef4dadf2a0a678551e

Disposition: FIXED
Commit: 7eed819f2850a1334d26167d6deadea19b6e1a32
Evidence: pr_oracle_attachment.py:256 and qoder_dispatch_bridge.py:2954 sanitize only the specific DispatchError; pr_oracle_attachment.py:977 projects immutable binary/private dependencies as screened ref/hash records. Owning regressions1895/1926/2298 and actual36member archive restore validate both reviewed items.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#pullrequestreview-5372094903 -> 7eed819f2850a1334d26167d6deadea19b6e1a32

Disposition: FIXED
Commit: adc7ea73186ab3b0b228e9619db9b283e00c3d52
Evidence: .agents/skills/pulseplate-orchestration-dispatch/SKILL.md:108 uses the emitted TRUSTED_TOOL_ROOT and MATERIAL_ROOT names while preserving external runtime/root admission, -I and Tcwd.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#pullrequestreview-5384036509 -> adc7ea73186ab3b0b228e9619db9b283e00c3d52

Disposition: NOT-A-BUG
Evidence: scripts/orchestration/role_dispatch_bridge.py:19 delegates the existing parser to qoder_dispatch_bridge.main; guard-adc-QA2-oracle-payload.json and actual QA2 current-result validation exit0 prove real dispatch delivery.
Reason: The neutral entrypoint is intentionally a thin shim. The real argument/evidence owner is qoder_dispatch_bridge; duplicating its parser would create a second owner.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#discussion_r4149366636

Disposition: NOT-A-BUG
Evidence: scripts/orchestration/role_dispatch_bridge.py:19 and :22 delegate to qoder_dispatch_bridge.main. Actual ADC dispatch and same QA2 consumption/revalidation exit0 demonstrate argument handling and evidence delivery.
Reason: The top-level review repeats the thin-entrypoint finding; parsing belongs to the existing qoder owner. Human exact-head merge approval remains separate from this ordinary technical disposition.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2464#pullrequestreview-5372021843

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:ad28c4316962ddb925f981607e4920989bb398b3e10f60e9d7ce670e9003d2ae","material_head_sha":"adc7ea73186ab3b0b228e9619db9b283e00c3d52","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985","blocking":false,"head_revision":"adc7ea73186ab3b0b228e9619db9b283e00c3d52","material_digest":"sha256:ad28c4316962ddb925f981607e4920989bb398b3e10f60e9d7ce670e9003d2ae","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985","digest":"sha256:ad28c4316962ddb925f981607e4920989bb398b3e10f60e9d7ce670e9003d2ae","material_head_sha":"adc7ea73186ab3b0b228e9619db9b283e00c3d52","merge_base_sha":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985","policy_version":"pulseplate.material-classification/v1"},"pr_number":2464,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:ad28c4316962ddb925f981607e4920989bb398b3e10f60e9d7ce670e9003d2ae","material_head_sha":"adc7ea73186ab3b0b228e9619db9b283e00c3d52","report_payload":{"actionable_findings_count":0,"base_ref_oid":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/935f78a88e54.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"935f78a88e54"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 6499 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-10-01T23:54:06Z","material_digest":"sha256:ad28c4316962ddb925f981607e4920989bb398b3e10f60e9d7ce670e9003d2ae","material_head_sha":"adc7ea73186ab3b0b228e9619db9b283e00c3d52","merge_base_sha":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"5338465ad08d4a0c8da6ffa9d65dce9d8dbea985..adc7ea73186ab3b0b228e9619db9b283e00c3d52","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2464_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".agents/skills/pulseplate-orchestration-dispatch/SKILL.md",".agents/skills/pulseplate-orchestration-dispatch/rules/context-loading.md",".github/workflows/ci.yml","docs/orchestration/GOVERNED_CREATIVE_CODE_EXECUTION_CONTRACT.md","docs/orchestration/contracts/EXPERIMENT_RUNNER_PR_CREATIVE_CONTEXT_CONTRACT.md","docs/orchestration/workflow.md","docs/roadmap/BACKLOG_LEDGER.md","scripts/AGENTS.md","scripts/orchestration/experiment_runner.py","scripts/orchestration/experiment_runner_dispatch.py","scripts/orchestration/experiment_runner_pr_creative_context.py","scripts/orchestration/pr_oracle_attachment.py","scripts/orchestration/qoder_dispatch_bridge.py","scripts/orchestration/render_codex_start_prompt.py","scripts/orchestration/task_bootstrap.py","tests/test_ci_workflow_pr_size_governance_contract.py","tests/test_experiment_runner_dispatch.py","tests/test_experiment_runner_pr_creative_context.py","tests/test_pr_oracle_attachment.py","tests/test_qoder_dispatch_bridge.py","tests/test_render_codex_start_prompt.py","tests/test_task_bootstrap.py"],"diff_summary":{"additions":6433,"changed_lines":6499,"deletions":66,"files":22},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":[".agents/skills/pulseplate-orchestration-dispatch/AGENTS.md","AGENTS.md","docs/orchestration/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:62e29a76a643f6be1400fd1b4adb0a92cc4a77376efa4eed3542412089c0cdac","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
