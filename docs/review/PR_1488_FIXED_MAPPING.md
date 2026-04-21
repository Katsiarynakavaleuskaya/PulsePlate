# PR #1488 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4148229640
Disposition: FIXED
Commit: see mapping entries below
Evidence: review covered by `#discussion_r3117952073` and the split-contract test hardening in [tests/test_cd_workflow_production_deploy_gate.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_cd_workflow_production_deploy_gate.py:64).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117952073
Disposition: FIXED
Commit: 02b06b8d5
Evidence: [scripts/deploy_production.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/scripts/deploy_production.sh:294), [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:29)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4148251408
Disposition: FIXED
Commit: see mapping entries below
Evidence: review covered by `#discussion_r3117970414` and `#discussion_r3117970442`, both fixed and mapped below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117970414
Disposition: FIXED
Commit: 02b06b8d5
Evidence: [deploy/PRODUCTION.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/deploy/PRODUCTION.md:204), [deploy/WORKFLOW.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/deploy/WORKFLOW.md:217), [deploy/WORKFLOW.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/deploy/WORKFLOW.md:325)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117970442
Disposition: FIXED
Commit: 6943052e6
Evidence: [docs/review/PR_1488_FIXED_MAPPING.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/docs/review/PR_1488_FIXED_MAPPING.md:17)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4149616401
Disposition: FIXED
Commit: see mapping entries below
Evidence: review covered by `#discussion_r3119216490` and the `app.env_file` contract assertion in [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:27).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3119216490
Disposition: FIXED
Commit: ebed66e71
Evidence: [scripts/deploy_production.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/scripts/deploy_production.sh:369), [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:27)

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: rerun required after ready-state remediation commits.
- [ ] Required checks complete (no pending jobs)
  Evidence: rerun required after ready-state remediation commits.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: `check_review_threads_disposition.py --pr-number 1488 --require-auth` reported no resolved review threads before the ready-state remediation rerun.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: this artifact now records the ready-state Sourcery and CodeRabbit review URLs; latest-head bot rerun still pending.
- [ ] Pre-commit green on latest pushed head
  Evidence: local rerun passed before this artifact update; re-run on final pushed head pending.
- [ ] `make verify` green on latest pushed head
  Evidence: final rerun required after ready-state remediation commits.

## Deferred / Follow-ups

- staging fallback-vhost removal and full staging runtime readiness remain tracked under `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-staging-tls-fallback-seam-after-full-staging-readiness`
- runtime slimming, image-budget telemetry, signed provenance, SBOM/VEX, Dagger, and Cloudflare changes remain out of scope for PR #1488
