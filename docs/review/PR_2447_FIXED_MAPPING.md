# PR 2447 — Review Governance

Review-Seal-Version: v1

## Lane Start Provenance
Packet: `artifacts/orchestration/task_packets/obs2a_pr2447_urllib3_v1.json`

## Experiment Runner Evidence
Artifact: `artifacts/orchestration/experiments/results/obs2a-pr2447-bug01-head2da-v3-result.json`

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7
Evidence: scripts/deploy.sh:1208 and scripts/deploy_production.sh:3018 conditionally pull and inspect Alertmanager; tests/test_deploy_contract_scripts.py:6135 and :9142 prove off/on runtime; native targeted Compose dry-run planned only app.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115638835 -> e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7

Disposition: FIXED
Commit: e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7
Evidence: scripts/deploy.sh:266 and :350-390 plus scripts/deploy_production.sh:783 and :867-907 enumerate all profiles/services and reject non-Alertmanager SMTP network, namespace and exact-key carriers; negative tests at tests/test_deploy_contract_scripts.py:3865 and :4885.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115638840 -> e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7

Disposition: FIXED
Commit: 924ad9995937d1ab970427c7e087c09c1d80daed
Evidence: scripts/deploy.sh:459 and scripts/deploy_production.sh:482 compare an aware UTC instant and reject at/after 2026-10-24T00:00:00Z; tests/test_deploy_contract_scripts.py:4982 covers before/at/after for both contours.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115672916 -> 924ad9995937d1ab970427c7e087c09c1d80daed

Disposition: FIXED
Commit: e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7
Evidence: scripts/deploy.sh:481-492 and scripts/deploy_production.sh:492-503 require selected SMTP key regular, mode-0444, nonempty metadata without reading contents; negative tests at tests/test_deploy_contract_scripts.py:3927 and :4792.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115672920 -> e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7

Disposition: FIXED
Commit: 924ad9995937d1ab970427c7e087c09c1d80daed
Evidence: scripts/deploy.sh:459 and scripts/deploy_production.sh:482 use the exact UTC expiry boundary; tests/test_deploy_contract_scripts.py:4982 proves before/at/after in both contours.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4116132348 -> 924ad9995937d1ab970427c7e087c09c1d80daed

Disposition: FIXED
Commit: 924ad9995937d1ab970427c7e087c09c1d80daed
Evidence: scripts/deploy_production.sh:526 binds the same Compose project, sole container ID and exact Docker state before product mutation; calls at :3060 and :3095 enforce expiry for running instances even with caller profile off. tests/test_deploy_contract_scripts.py:5077/:5135/:5211 cover absent/stopped/running, errors, malformed labels/state and unknown project. Native disposable Compose receipt confirms enumeration/inspect semantics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4116141922 -> 924ad9995937d1ab970427c7e087c09c1d80daed

Disposition: FIXED
Commit: 924ad9995937d1ab970427c7e087c09c1d80daed
Evidence: scripts/deploy_production.sh:68 captures caller profile presence/value before env loading and :290 rejects drift/restores/exports the caller value; scripts/deploy.sh:58 exports explicit empty for absent caller. tests/test_deploy_contract_scripts.py:5272/:5318 and native Compose receipt prove exported-empty precedence over env-file export syntax.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4116141925 -> 924ad9995937d1ab970427c7e087c09c1d80daed

Disposition: FIXED
Commit: 89dd4b5d5d379aac2a91069fac0cd68f50c2879b
Evidence: deploy/docker-compose.staging.yaml:180 and both production Compose contours assign explicit Alertmanager gateway priorities 1/2; scripts/deploy.sh:327 and scripts/deploy_production.sh:936 reject changed/missing/wrong-type values; tests/test_deploy_contract_scripts.py:4114 and :4164 cover native normal config and 14 negatives.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4138855911 -> 89dd4b5d5d379aac2a91069fac0cd68f50c2879b

Disposition: FIXED
Commit: 89dd4b5d5d379aac2a91069fac0cd68f50c2879b
Evidence: scripts/deploy_production.sh:549 inventories exact installed project/service Docker labels with full IDs, then verifies inspect identity/state; tests/test_deploy_contract_scripts.py:5581 proves directory/archive first bundles with old installed Compose lacking Alertmanager, and :5711 covers fail-closed census faults.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4138855917 -> 89dd4b5d5d379aac2a91069fac0cd68f50c2879b

Disposition: FIXED
Commit: e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7
Evidence: The two applicable Sourcery findings are fixed by e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7 in both deploy scripts with off/on and all-profile negative tests; the separate httpd premise is disproven by the exact pinned-image native receipt and mapped NOT-A-BUG inline.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#pullrequestreview-5330606232 -> e718bdb3e4de5126d2e7ecdb05ce3af3db55adb7

Disposition: FIXED
Commit: 924ad9995937d1ab970427c7e087c09c1d80daed
Evidence: The actionable UTC expiry finding in this CodeRabbit top-level review is corrected by the aware boundary in both deploy scripts and the before/at/after contract test at tests/test_deploy_contract_scripts.py:4982; its inline root is mapped separately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#pullrequestreview-5331204345 -> 924ad9995937d1ab970427c7e087c09c1d80daed

Disposition: FIXED
Commit: 89dd4b5d5d379aac2a91069fac0cd68f50c2879b
Evidence: The two actionable P1 inline roots in this review are corrected by the gateway and first-bundle changes in the same commit and focused native/negative tests; the third inline carrier claim has separate native-backed NOT-A-BUG disposition.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#pullrequestreview-5359160047 -> 89dd4b5d5d379aac2a91069fac0cd68f50c2879b

Disposition: NOT-A-BUG
Evidence: Exact pinned linux/amd64 Alertmanager image native no-network read-only check returned httpd-present; local pr2447_httpd_native_receipt.txt records image identity and result; .github/workflows/cd.yml:985 uses that image.
Reason: The official pinned image contains executable /bin/httpd, so the synthetic exporter entrypoint exists.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115638837

Disposition: NOT-A-BUG
Evidence: docs/roadmap/BACKLOG_LEDGER.md:217 records the direct owner-approved one-PR2 17-path scope including the exact temporary CVE exception; PR 2447 carries trusted operator-approved and scope/privileged-approved labels and body Privileged scope approval.
Reason: The owner explicitly authorized the combined PR2 exception, superseding the repository default of a separate CVE PR for this exact lane; the waiver remains narrow and expiring.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4115672925

Disposition: NOT-A-BUG
Evidence: Accepted PR2 criteria C02/C08; docs/deploy/OPERATIONAL_SIGNALS.md:122 records the distinct repository/main/host/email states and requires the later monitoring-only transaction. Targeted deploy commands continue to address only app/Caddy/Prometheus.
Reason: PR2 prepares deploy admission; the accepted plan reserves first monitoring-only activation until after PR2 and PR3 merge plus separate human authorization. Selecting a profile makes admission stricter but does not authorize starting a service or prove email receipt.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4116141920

Disposition: NOT-A-BUG
Evidence: tests/test_deploy_contract_scripts.py:5430 runs native Docker Compose 5.3.1 all-profile config for ipc, pid, volumes_from, links and network_mode, then proves both readers reject normalized depends_on.alertmanager; scripts/deploy.sh:364 and scripts/deploy_production.sh:978 own the same guard.
Reason: On the admitted native Compose v5.3.1, each cited service-reference carrier becomes a normalized incoming depends_on edge already rejected before product mutation. This is bounded to the supported normalizer and tested carriers; no universal future-Compose claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#discussion_r4138855926

Disposition: NOT-A-BUG
Evidence: Authenticated unchanged guide body (updated_at 2026-09-27T14:07:42Z) retained in pr2447_sourcery_guide_current.json; opening English statement says the PR prepares but does not activate delivery. Concrete Sourcery review 5330606232 and inline roots are handled separately; OPERATIONAL_SIGNALS.md:122 preserves later human monitoring activation.
Reason: The Sourcery reviewer guide is informational and explicitly describes preparation without activation. It contains no independent defect request; its generic bot usage instructions do not create review or mutation authority. The separate concrete Sourcery review findings retain their own FIXED/NOT-A-BUG dispositions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5856567118

Disposition: NOT-A-BUG
Evidence: .coderabbit.yaml:13 and :32 request descriptive names, type hints and 97% test coverage; neither config nor tests/AGENTS.md:24 establishes an 80% docstring threshold. Focused tests and native receipts cover the concrete admission behavior. This disposition leaves all actual inline correctness/security findings subject to their separate fixes.
Reason: The standalone 80% docstring suggestion is an advisory default, not a repository coverage contract or a runtime defect. The changed Python functions are test helpers/cases with descriptive names and explicit deterministic assertions; production changes are shell/config. Adding generic prose solely to satisfy this bot metric would not improve the bounded behavior under review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5856579445

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5858805063 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5858805063

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5861562309 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5861562309

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5866346654 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5866346654

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5874776111 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5874776111

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5875589139 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5875589139

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5876624426 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5876624426

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5879564132 contains only a Codex code-review usage-limit notice; current AGENTS.md provider-neutral no-claim contract requires no provider retry and retains current-head CI, self-review and actionable-comment gates.
Reason: The comment reports provider unavailability and identifies no PR code or security defect; it grants no review, PASS, approval or no-findings claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5879564132

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5886715588 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5886715588

Disposition: NOT-A-BUG
Evidence: Authenticated Codex Connector issue comment 5902163072 states only a code-review usage limit and credit setting; current repo provider-neutral no-claim policy requires no retry and retains current-head CI, mapping, security and review gates.
Reason: The notice identifies no defect in PR code, config, tests or security; it is provider availability information and grants no review, approval, PASS or no-findings claim.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5902163072

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5902404319 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5902404319

Disposition: NOT-A-BUG
Evidence: Authenticated issue comment 5922365126 contains only a code-review usage-limit notice; current AGENTS.md preserves current-head CI, trusted security checks, self-review, mapping, dispositions and the review wait window.
Reason: This provider-availability notice identifies no PR material defect and grants no review, approval, PASS or no-findings claim. Provider-neutral closeout requires no retry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5922365126

Disposition: NOT-A-BUG
Evidence: Authenticated current-head issue comment 5929091438 contains only the code-review usage-limit notice; AGENTS.md retains current-head CI, trusted security checks, self-review, dispositions and wait-window gates.
Reason: Provider availability information identifies no independent code or security defect and grants no review, PASS, approval or no-findings claim. No provider retry is required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2447#issuecomment-5929091438

## Review Material Seal
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_BEGIN -->
<!-- pragma: allowlist nextline secret -->
{"authority":"human_asserted_content_receipt","code_review":{"blocking":false,"material_digest":"sha256:0d55300c0f58e2c95f831a2066e0727ffe13382fc5b5dc7b9ba321a8c6d9a009","material_head_sha":"cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","output_required":false,"review_claim":"none"},"codex_security":{"base_revision":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e","blocking":false,"head_revision":"cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","material_digest":"sha256:0d55300c0f58e2c95f831a2066e0727ffe13382fc5b5dc7b9ba321a8c6d9a009","no_findings_claim":false,"output_required":false,"scan_claim":"none"},"material":{"base_ref_oid":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e","digest":"sha256:0d55300c0f58e2c95f831a2066e0727ffe13382fc5b5dc7b9ba321a8c6d9a009","material_head_sha":"cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","merge_base_sha":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e","policy_version":"pulseplate.material-classification/v1"},"pr_number":2447,"repository":"Katsiarynakavaleuskaya/PulsePlate","schema_version":"pulseplate.pr-review-seal/v1","self_review":{"actionable_findings_count":0,"authority":"repo_native_pulseplate_pr_review_advisory","blocking":false,"findings_count":1,"material_digest":"sha256:0d55300c0f58e2c95f831a2066e0727ffe13382fc5b5dc7b9ba321a8c6d9a009","material_head_sha":"cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","report_payload":{"actionable_findings_count":0,"base_ref_oid":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e","calibration":{"case_labels":["large-diff-risk"],"false_positive_controls":["clean context must produce zero findings","benign fixed-mapping presence must not become a governance finding","warnings and governance uncertainty remain actionable findings, not diagnostic notes","review-source degradation is status/warning only unless an explicit blocking source finding exists","large diff risk is review-planning evidence, not a merge-readiness claim"],"posting_eligible":false,"posting_gate":"GitHub posting remains out of scope until a dedicated calibrated posting PR.","rubric_version":"pr4-2026-04-28"},"coordinator_packet":{"path":"artifacts/orchestration/task_packets/obs2a_pr2447_urllib3_v1.json","role_order":["agent-coordinator","architecture-specialist","security-auditor","qa-engineer-agent","bug-hunter","data-scientist-agent"],"task_packet_id":"1be4468bbc99"},"decision_log":["This report is advisory and side-effect free.","This report does not post GitHub comments, resolve review threads, merge PRs, or claim merge readiness.","External CodeRabbit, Sourcery, and Cubic statuses remain separate PR governance signals."],"deferred_followups":[],"findings":[{"category":"tests","diagnostic_code":"large_diff_review_risk","disposition_candidate":"NOT-A-BUG","evidence":"Diff contains 4863 changed lines, above review-risk threshold 800.","file":"docs/roadmap/BACKLOG_LEDGER.md","gate_to_run":"make validate-changed","line":null,"role_agent":"bug-hunter","severity":"note","suggested_fix":"Confirm PR split rationale and targeted deterministic gates before opening review."}],"findings_count":1,"gate_plan":["python3 scripts/orchestration/check_preflight.py","python3 scripts/orchestration/check_agent_consistency.py","python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q","make test-fast","make validate-changed"],"generated_at_utc":"2026-10-01T11:55:52Z","material_digest":"sha256:0d55300c0f58e2c95f831a2066e0727ffe13382fc5b5dc7b9ba321a8c6d9a009","material_head_sha":"cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","merge_base_sha":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e","mode":"dry-run-report","review_source_status":[{"blocking":false,"evidence":"gh api repos/<repo>/pulls/<pr>","fallback_required":false,"reason":"","source":"github_pr_metadata","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"6e09f4ea8cc33e8389d99075b6f6a0d10f1b725e..cafbac47cf0084d4bc65471f2ce8cb15d0a2a73f","fallback_required":false,"reason":"","source":"git_diff","source_degraded":false,"status":"available"},{"blocking":false,"evidence":"docs/review/PR_2447_FIXED_MAPPING.md","fallback_required":false,"reason":"","source":"fixed_mapping_artifact","source_degraded":false,"status":"available"}],"role_review":[{"role_agent":"agent-coordinator","summary":"agent-coordinator has no deterministic findings from the supplied context."},{"role_agent":"architecture-specialist","summary":"architecture-specialist has no deterministic findings from the supplied context."},{"role_agent":"security-auditor","summary":"security-auditor has no deterministic findings from the supplied context."},{"role_agent":"qa-engineer-agent","summary":"qa-engineer-agent has no deterministic findings from the supplied context."},{"role_agent":"bug-hunter","summary":"bug-hunter flagged 1 advisory finding(s) for human review."},{"role_agent":"data-scientist-agent","summary":"data-scientist-agent has no scoring calibration changes in this dry-run report."}],"schema_version":"2.0.0","scope_reviewed":{"changed_files":[".github/workflows/cd.yml",".secrets.baseline","AGENTS.md","RUNBOOK_AGENT.md","deploy/AGENTS.md","deploy/alertmanager/alertmanager.yml","deploy/alertmanager/trivy-ignore.yaml","deploy/docker-compose.production.selfhosted.yaml","deploy/docker-compose.production.yaml","deploy/docker-compose.staging.yaml","deploy/prometheus/prometheus.yml","docs/deploy/OPERATIONAL_SIGNALS.md","docs/deploy/STAGING.md","docs/roadmap/BACKLOG_LEDGER.md","docs/security/CVE-2026-84445-alertmanager.md","docs/security/CVE-2026-84782-openssl.md","docs/security/PR_2447_URLLIB3_REMEDIATION.md","requirements-ci-lite.txt","requirements-dev.txt","requirements-docker-runtime.txt","requirements-lock.txt","requirements-rag-vector-cpu.txt","requirements-rag-vector.txt","requirements.in","requirements.txt","scripts/ci/check_trivy_ignore_policy_native.py","scripts/deploy.sh","scripts/deploy_production.sh","scripts/ops/staging_runtime_diagnostics.py","tests/fixtures/dependency_security_schema.json","tests/test_caddy_deploy_provenance.py","tests/test_dependency_security_guard.py","tests/test_deploy_contract_scripts.py","tests/test_staging_runtime_diagnostics.py","tests/test_trivy_ignore_policy_expiry.py","trivy/ignore-policy.rego"],"diff_summary":{"additions":4636,"changed_lines":4863,"deletions":227,"files":36},"fixed_mapping_errors":[],"omitted_surfaces":["GitHub posting","PR thread resolution","merge readiness claims"],"pr_metadata_available":true,"scoped_agents_md":["AGENTS.md","deploy/AGENTS.md","scripts/AGENTS.md","tests/AGENTS.md"]},"warnings":[]},"report_sha256":"sha256:b76bcc0216c7925845ec63c687b95a554b16e21705c1b400a973d7a88e8eae11","review_claim":"none","review_tool":"pulseplate-pr-review","schema_version":"pulseplate.self-review-advisory/v1","status":"advisory_report_attached"}}
<!-- PULSEPLATE_PR_REVIEW_SEAL_V1_END -->
