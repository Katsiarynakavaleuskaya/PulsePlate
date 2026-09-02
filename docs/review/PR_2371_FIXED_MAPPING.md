# PR 2371 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/3d9e69659b3b.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/browserslist-dep-sec-oracle-v2.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1490 and tests/test_frontend_dependency_guards.py:2752; selector compatibility is checked for every demand on its own lock surface; focused suite 173 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911578160 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2551; the permanent guard evaluates the current tracked surface universe without freezing historical carrier equality
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621759 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1484 and tests/test_frontend_dependency_guards.py:2658; SHA-512 SRI is base64-decoded and required to contain a 64-byte digest
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621767 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2557 and tests/test_frontend_dependency_guards.py:2589; exact expected and applicable advisory identities are asserted independently
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621776 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:2773 and tests/test_frontend_dependency_guards.py:2800; only exact boolean optional peer metadata permits absence and malformed or mandatory forms fail closed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911621782 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 79a2dc7b059bf4530a4ec910743571167da84fda
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:197; the replay reconstructs package.json and package-lock.json from the exact frozen base via git show before invoking the resolver
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3911627835 -> 79a2dc7b059bf4530a4ec910743571167da84fda

Disposition: FIXED
Commit: 47fea5211b835a8ed5c0cfad4dc207d130b3900b
Evidence: tests/test_frontend_dependency_guards.py:569, tests/test_frontend_dependency_guards.py:2776, and tests/test_frontend_dependency_guards.py:2793; Node ancestor lookup rejects an unrelated sibling and honors nearest-occurrence precedence; focused suite 175 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912113765 -> 47fea5211b835a8ed5c0cfad4dc207d130b3900b

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:469 and tests/test_frontend_dependency_guards.py:2799; malformed lock package records and non-object dependency containers fail closed; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338088 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: b6450b4c661512184334c9daf52ff57b3cf30115
Evidence: docs/review/PR_2371_FIXED_MAPPING.md; the mapping-only commit after the comment resealed material head a1ff72da36ba617d423879fc8f6e9d7158199022 with digest sha256:1d1d14eb8f179789368bb828bc49607665d9b3d95ea16172f037d5d9064b14c4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338102 -> b6450b4c661512184334c9daf52ff57b3cf30115

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1478 and tests/test_frontend_dependency_guards.py:2813; a root lock target demand is rejected even with a safe installed occurrence; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912338112 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1481 and tests/test_frontend_dependency_guards.py:2840; renamed npm aliases and registry-tarball demands are rejected instead of resolving through the canonical path; focused suite 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912451752 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542
Evidence: tests/test_frontend_dependency_guards.py:1475 and tests/test_frontend_dependency_guards.py:2815; both empty and dot root lock keys are rejected with safe installed occurrences; focused suite 180 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912644864 -> 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1274 and tests/test_frontend_dependency_guards.py:2836; malformed manifest dependency, override, bundled, and workspace containers fail closed; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912690951 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1297 and tests/test_frontend_dependency_guards.py:2852; tracked target-named workspace members are rejected as manifest carriers; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947938 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 1694db0a6d367f58380e6f623e363c5a73ca96e2
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:167 and docs/security/DEPENDABOT_ALERT_INVENTORY.md:39; both anchors now point to the actual boundary and all-occurrence guard lines
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947942 -> 1694db0a6d367f58380e6f623e363c5a73ca96e2

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:489 and tests/test_frontend_dependency_guards.py:3083; same-name optionalDependencies precedence is applied before selector validation; focused suite 187 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3912947949 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:35 and docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:41 rebind the synchronized base and reachable material head; the regenerated current mapping seal binds the same live material projection
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913104631 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:41 binds reachable material head f159534e0160bff57ec94985b51191d309f6bb32 after base synchronization; no pre-merge squash SHA is claimed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469111 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: f159534e0160bff57ec94985b51191d309f6bb32
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:216 defines the timestamped registry cutoff and immutable lock receipt, and requires fresh admission for later registry output
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469127 -> f159534e0160bff57ec94985b51191d309f6bb32

Disposition: FIXED
Commit: f159534e0160bff57ec94985b51191d309f6bb32
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:82 and tests/test_frontend_dependency_guards.py:2711 bind the recomputed 4a0b408d receipt digest to the exact retained advisory JSON
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#discussion_r3913469139 -> f159534e0160bff57ec94985b51191d309f6bb32

Disposition: FIXED
Commit: 937db0926f257684cc57ef39b1dcf78589643aeb
Evidence: tests/test_frontend_dependency_guards.py:1490 and tests/test_frontend_dependency_guards.py:2752; all Sourcery actionable selector-demand feedback is fixed and the focused suite reports 173 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5086600531 -> 937db0926f257684cc57ef39b1dcf78589643aeb

Disposition: FIXED
Commit: 79a2dc7b059bf4530a4ec910743571167da84fda
Evidence: docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md:197; CodeRabbit replay feedback is fixed by exact-base git-show reconstruction
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5086658854 -> 79a2dc7b059bf4530a4ec910743571167da84fda

Disposition: FIXED
Commit: 47fea5211b835a8ed5c0cfad4dc207d130b3900b
Evidence: tests/test_frontend_dependency_guards.py:569 and tests/test_frontend_dependency_guards.py:2776; the top-level Codex review actionable is fixed by reachable Node ancestor resolution
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087247194 -> 47fea5211b835a8ed5c0cfad4dc207d130b3900b

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:469, tests/test_frontend_dependency_guards.py:1478, and tests/test_frontend_dependency_guards.py:2799; all material actionables in this Codex review are fixed, while its stale-seal child is independently mapped to b6450b4c661512184334c9daf52ff57b3cf30115
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087511818 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 684409902cf3a05ff1badbac3b27fac6fd758c1e
Evidence: tests/test_frontend_dependency_guards.py:1481 and tests/test_frontend_dependency_guards.py:2840; the renamed-demand actionable in this Codex review is fixed and the focused suite reports 179 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087647678 -> 684409902cf3a05ff1badbac3b27fac6fd758c1e

Disposition: FIXED
Commit: 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542
Evidence: tests/test_frontend_dependency_guards.py:1475 and tests/test_frontend_dependency_guards.py:2815; the dot-root actionable in this CodeRabbit review is fixed and the focused suite reports 180 passed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087872989 -> 0bd2df4dbb8f004114b28e9fe14fbf0fa6232542

Disposition: FIXED
Commit: 792bcc8bd06719c1e5c71b2a15802f2b0468a912
Evidence: tests/test_frontend_dependency_guards.py:1274 and tests/test_frontend_dependency_guards.py:2836; the malformed-manifest actionable in this Codex review is fixed
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5087928515 -> 792bcc8bd06719c1e5c71b2a15802f2b0468a912

Disposition: FIXED
Commit: 1694db0a6d367f58380e6f623e363c5a73ca96e2
Evidence: all actionables in this Codex review are mapped to 792bcc8bd06719c1e5c71b2a15802f2b0468a912 and the final anchor correction 1694db0a6d367f58380e6f623e363c5a73ca96e2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088237740 -> 1694db0a6d367f58380e6f623e363c5a73ca96e2

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: the base-sync seal review is closed by reachable base/material rebinding in d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1 and the regenerated current mapping seal
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088421876 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

Disposition: FIXED
Commit: d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
Evidence: all owner-evidence actionables in this Codex review are fixed by f159534e0160bff57ec94985b51191d309f6bb32 and final owner rebinding d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2371#pullrequestreview-5088834566 -> d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:e4b7bc0f44887565ffb35ff0e0f0aac4549a4d9c222416576c1fe18ed5033a5e","material_head_sha":"d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"11fff8e9e6c22797cb42d0ac8612c51f4074c051","blocking":false,"head_revision":"d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","material_digest":"sha256:e4b7bc0f44887565ffb35ff0e0f0aac4549a4d9c222416576c1fe18ed5033a5e","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"11fff8e9e6c22797cb42d0ac8612c51f4074c051","digest":"sha256:e4b7bc0f44887565ffb35ff0e0f0aac4549a4d9c222416576c1fe18ed5033a5e","material_head_sha":"d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","merge_base_sha":"11fff8e9e6c22797cb42d0ac8612c51f4074c051","policy_version":"pulseplate.material-classification/v1"},"pr_number":2371,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:e4b7bc0f44887565ffb35ff0e0f0aac4549a4d9c222416576c1fe18ed5033a5e","material_head_sha":"d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","report_payload":{"actionable_findings_count":0,"base_ref_oid":"11fff8e9e6c22797cb42d0ac8612c51f4074c051","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/3d9e69659b3b.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"3d9e69659b3b"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 1384 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-09-02T11:52:47Z","material_digest":"sha256:e4b7bc0f44887565ffb35ff0e0f0aac4549a4d9c222416576c1fe18ed5033a5e","material_head_sha":"d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","merge_base_sha":"11fff8e9e6c22797cb42d0ac8612c51f4074c051","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"11fff8e9e6c22797cb42d0ac8612c51f4074c051..d2b34cfbd301ad3dc9c4a854732ee8d9ad9aa6e1","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2371_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":["docs/security/DEPENDABOT_ALERT_INVENTORY.md","docs/security/FRONTEND_BROWSERSLIST_REMEDIATION_CLASS.md","frontend/package-lock.json","tests/test_frontend_dependency_guards.py"],"diff_summary":{"additions":1328,"changed_lines":1384,"deletions":56,"files":4},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","frontend/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:b38b3737121641887ac8204b1ed0cd9a8f23ca8714c6d9ac890c223333d564f2","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
