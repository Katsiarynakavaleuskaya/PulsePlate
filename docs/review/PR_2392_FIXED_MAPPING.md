# PR 2392 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/3215c5698bd3.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/astra-agent-instructions-post-review.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 482f5b56430336f579f2bc9537d70fb5c2838be5
Evidence: .agents/skills/pulseplate-orchestration-dispatch/rules/role-mapping.md:30; tests/test_agent_docs_registry_guard.py:1116; repeated-owner ordinary/exact-context cases passed. Owner grants remain slug-scoped; only mixed-rights requests require rescoping.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997213910 -> 482f5b56430336f579f2bc9537d70fb5c2838be5

Disposition: FIXED
Commit: 482f5b56430336f579f2bc9537d70fb5c2838be5
Evidence: docs/orchestration/workflow.md:223; tests/test_agent_docs_registry_guard.py:1082; execute preflight precedes owner preparation, all preparatory writes are forbidden, and separate post-role owner handoff is required. Positive and reversed-order/omitted-ban/handoff controls passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997234734 -> 482f5b56430336f579f2bc9537d70fb5c2838be5

Disposition: FIXED
Commit: 482f5b56430336f579f2bc9537d70fb5c2838be5
Evidence: .agents/skills/pulseplate-orchestration-dispatch/SKILL.md:17; rules/packet-parsing.md:13; tests/test_agent_docs_registry_guard.py:1142; JSON-native bindings are required while existing CLI Markdown/manual inspection remains available.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997234736 -> 482f5b56430336f579f2bc9537d70fb5c2838be5

Disposition: FIXED
Commit: 7aca1df57c45f10930a22c31d63d32c657358f04
Evidence: .agents/skills/pulseplate-orchestration-dispatch/rules/role-mapping.md:67; docs/agents/model_policy.md:88; generic-only argument example and three unsupported-kwarg controls passed. An actual minimal native call using only task_name/message/fork_turns completed on this host; no universal-host or selected-model claim is made.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997417066 -> 7aca1df57c45f10930a22c31d63d32c657358f04

Disposition: FIXED
Commit: 7aca1df57c45f10930a22c31d63d32c657358f04
Evidence: docs/orchestration/workflow.md:237; docs/agents/model_policy.md:54; generated QA/Security examples and dropped-owner controls passed. The complete eligible set is preserved; one active eligible role/occurrence and exact files are selected per later serial handoff without narrowing metadata or claiming OS isolation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997417069 -> 7aca1df57c45f10930a22c31d63d32c657358f04

Disposition: FIXED
Commit: 7aca1df57c45f10930a22c31d63d32c657358f04
Evidence: .agents/skills/pulseplate-orchestration-dispatch/SKILL.md:87; generated Security selects order2 and generated QA selects2/3 with both owner flags intact; the old reusable literal5 and either dropped QA owner flag are rejected by finite controls.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997417072 -> 7aca1df57c45f10930a22c31d63d32c657358f04

Disposition: FIXED
Commit: 2f1223bbc8f4b9a7053775d85aa9f6621e750245
Evidence: docs/orchestration/workflow.md:220; general ownerless-route preparation preserves accepted goal, paths, phase and required roles and validates actual eligibility before writing. Existing-bootstrap capability was observed in retained ownerless-doc-route-observations.json/ownerless-rescope-observations.json; the private Documentation-to-Security example and permanent case tests were removed per owner steering.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997774962 -> 2f1223bbc8f4b9a7053775d85aa9f6621e750245

Disposition: FIXED
Commit: 2f1223bbc8f4b9a7053775d85aa9f6621e750245
Evidence: tests/test_agent_docs_registry_guard.py:1227; every generated-packet guide test explicitly supplies a fixture-controlled missing telemetry path. The affected generated QA/Security cases passed; runtime telemetry defaults remain unchanged.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997774965 -> 2f1223bbc8f4b9a7053775d85aa9f6621e750245

Disposition: FIXED
Commit: 2f1223bbc8f4b9a7053775d85aa9f6621e750245
Evidence: .cursor/agents/agent-coordinator.md:489; packet generation is metadata-only after analyze preflight and may precede execute preflight. Owner-capable preparatory dispatch follows execute preflight under no-write limits; tracked implementation follows all preparation and separate handoff. Relevant recipe controls passed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997786757 -> 2f1223bbc8f4b9a7053775d85aa9f6621e750245

Disposition: FIXED
Commit: 482f5b56430336f579f2bc9537d70fb5c2838be5
Evidence: tests/test_agent_docs_registry_guard.py:883; all 16 new/modified top-level functions have concise docstrings; 144 registry cases and Black passed. The docstring-only follow-up preserves the module AST excluding docstrings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#issuecomment-5647988435 -> 482f5b56430336f579f2bc9537d70fb5c2838be5

Disposition: FIXED
Commit: 482f5b56430336f579f2bc9537d70fb5c2838be5
Evidence: .agents/skills/pulseplate-orchestration-dispatch/rules/role-mapping.md:30; repeated-owner regression tests passed. The one confirmed owner-granularity defect is corrected; the three remaining items have separately evidenced NOT-A-BUG dispositions in this same artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#pullrequestreview-5187635962 -> 482f5b56430336f579f2bc9537d70fb5c2838be5

Disposition: FIXED
Commit: 7aca1df57c45f10930a22c31d63d32c657358f04
Evidence: .cursor/agents/agent-coordinator.md:488; docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md:22 and :68; test_entry_recipes_require_canonical_admission passed for all three named entry recipes. Each now links preflight, no-write preparation and later scoped handoff.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#pullrequestreview-5187847156 -> 7aca1df57c45f10930a22c31d63d32c657358f04

Disposition: FIXED
Commit: 2f1223bbc8f4b9a7053775d85aa9f6621e750245
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2216 and :2233; the active item now references the repository-wide narrow local default and hosted heavy parity, with full local verification requiring an explicit single-invocation exception. Existing hook follow-up remains open and is not claimed fixed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#pullrequestreview-5188237775 -> 2f1223bbc8f4b9a7053775d85aa9f6621e750245

Disposition: FIXED
Commit: 2f1223bbc8f4b9a7053775d85aa9f6621e750245
Evidence: .cursor/agents/agent-coordinator.md:489; the one actionable bootstrap/admission clarification is corrected and covered by the passing named recipe test; its inline root is separately mapped in this artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#pullrequestreview-5188249321 -> 2f1223bbc8f4b9a7053775d85aa9f6621e750245

Disposition: NOT-A-BUG
Evidence: .agents/skills/pulseplate-orchestration-dispatch/SKILL.md:51; rules/role-mapping.md:11-15; test_native_guide_examples_match_bindings_and_override_boundary passed
Reason: The cited general Qoder selection instruction was deleted in the reviewed diff. The active Codex procedure explicitly uses native_agent_type from its packet binding.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997213909

Disposition: NOT-A-BUG
Evidence: .agents/skills/pulseplate-orchestration-dispatch/rules/role-mapping.md:11-25; Inherited Logic argument example; native binding and retired-coder negative control passed
Reason: The quoted blanket explorer/Research rule appears as removed text in the reviewed diff. The current procedure preserves the canonical native binding independently of readonly authority.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997213911

Disposition: NOT-A-BUG
Evidence: tests/AGENTS.md:149; tests/conftest.py:226-241 and 293-344; tests/test_analyzer_store.py:20-28; tests/test_db_model_registry.py:226-239
Reason: The named analyzer fixture uses core.db.Base after session-autouse fixtures call load_canonical_orm_metadata. The instruction expressly permits shared fixtures; direct fixture-local repetition of the loader is unnecessary.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997213913

Disposition: NOT-A-BUG
Evidence: docs/agents/model_policy.md:72; the active desktop native spawn schema exposes agent_type/model/reasoning_effort; retained native Sol task completed; finite binding/example tests passed
Reason: The unavailable-fields claim does not apply to the observed host. Examples now explicitly depend on the active callable schema; unsupported optional overrides inherit supported defaults, while a required unavailable choice is never silently substituted.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997234730

Disposition: NOT-A-BUG
Evidence: docs/orchestration/workflow.md:222-232 permits only a suitable existing route for actual scope and explicitly reports a capability gap if none exists; AGENT_ROUTING_GRAPH.md:110 reserves dominant-domain selection to coordinator; task_bootstrap.py:2148-2150 exposes --task-class and :1633-1645 resolves that class through the existing graph. Retained ownerless-rescope-observations.json includes Security with requested_agents=[] and emitted security-auditor ownership; the ordinary docs route is honestly recorded ownerless.
Reason: The new step does not promise a primary/owner override or automatic write admission for every docs task. It uses existing scope-based routing only when suitable, preserves constraints, forbids manufactured flags and explicitly stops implementation when the route capability is absent. No graph edit, invented user-requested role or misclassified task is prescribed. The broader requested coordinator-owner input would create new executable authority outside this approved instruction correction; its absence is already represented by the explicit capability-gap branch, not hidden as successful admission.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#discussion_r3997958391

Disposition: NOT-A-BUG
Evidence: docs/orchestration/workflow.md:158-163 and :244-261 explicitly distinguish permitted actions from OS isolation; task_bootstrap.py:2124-2141 defaults to disposable task packets; qoder_dispatch_bridge.py:2919-2928 defaults to stdout; SKILL.md:84 uses artifacts input and stdout. Both executable output implementations are unchanged in this PR.
Reason: The observation that an explicitly supplied arbitrary --output can write a tracked file is correct, but the requested shared filesystem enforcement is not a defect in the changed instruction contract. No shown recipe selects a tracked output. The staged action restriction does not claim that these general-purpose CLIs enforce it or make an unauthorized argument authorized; the workflow explicitly disclaims sandbox enforcement. The approved task preserves existing executable authority and does not introduce an output-boundary mechanism. This disposition makes no claim that arbitrary output paths are technically prevented.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2392#pullrequestreview-5188503477

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:32e3515c99f5d1521636efbbdcf8304a5344aefc1d6a9ff23ee2b25202ba96e6","material_head_sha":"2f1223bbc8f4b9a7053775d85aa9f6621e750245","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"b0eecb29160129be961a7038cd08084293759fc3","blocking":false,"head_revision":"2f1223bbc8f4b9a7053775d85aa9f6621e750245","material_digest":"sha256:32e3515c99f5d1521636efbbdcf8304a5344aefc1d6a9ff23ee2b25202ba96e6","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"b0eecb29160129be961a7038cd08084293759fc3","digest":"sha256:32e3515c99f5d1521636efbbdcf8304a5344aefc1d6a9ff23ee2b25202ba96e6","material_head_sha":"2f1223bbc8f4b9a7053775d85aa9f6621e750245","merge_base_sha":"b0eecb29160129be961a7038cd08084293759fc3","policy_version":"pulseplate.material-classification/v1"},"pr_number":2392,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:32e3515c99f5d1521636efbbdcf8304a5344aefc1d6a9ff23ee2b25202ba96e6","material_head_sha":"2f1223bbc8f4b9a7053775d85aa9f6621e750245","report_payload":{"actionable_findings_count":0,"base_ref_oid":"b0eecb29160129be961a7038cd08084293759fc3","calibration":{"case_labels":["review-source-degraded","large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/3215c5698bd3.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"3215c5698bd3"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1812 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","Add and fill docs/review/PR_<N>_FIXED_MAPPING.md before merge-ready loop","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-12T23:14:30Z","material_digest":"sha256:32e3515c99f5d1521636efbbdcf8304a5344aefc1d6a9ff23ee2b25202ba96e6","material_head_sha":"2f1223bbc8f4b9a7053775d85aa9f6621e750245","merge_base_sha":"b0eecb29160129be961a7038cd08084293759fc3","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"b0eecb29160129be961a7038cd08084293759fc3..2f1223bbc8f4b9a7053775d85aa9f6621e750245","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2392_FIXED_MAPPING.md","fallback_required":true,"reason":"Fixed-mapping artifact unavailable","source":"fixed_mapping_artifact","source_degraded":true,"status":"unavailable"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".agents/skills/pulseplate-orchestration-dispatch/AGENTS.md",".agents/skills/pulseplate-orchestration-dispatch/SKILL.md",".agents/skills/pulseplate-orchestration-dispatch/rules/context-loading.md",".agents/skills/pulseplate-orchestration-dispatch/rules/packet-parsing.md",".agents/skills/pulseplate-orchestration-dispatch/rules/role-mapping.md",".cursor/agents/AGENTS.md",".cursor/agents/agent-coordinator.md",".cursor/agents/architecture-specialist.md",".cursor/agents/bug-hunter.md",".cursor/agents/dev-operator.md","AGENTS.md","docs/agents/model_policy.md","docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md","docs/orchestration/workflow.md","docs/roadmap/BACKLOG_LEDGER.md","docs/templates/codex.config.example.toml","tests/AGENTS.md","tests/test_agent_docs_registry_guard.py"],"diff_summary":{"additions":1326,"changed_lines":1812,"deletions":486,"files":18},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":[".agents/skills/pulseplate-orchestration-dispatch/AGENTS.md",".cursor/agents/AGENTS.md","AGENTS.md","docs/orchestration/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:02b3f3a6afaa14135670ae63864a2f12a6a0adecdfba96982609aa4dd73e3e33","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
