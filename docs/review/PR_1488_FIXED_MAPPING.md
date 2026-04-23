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
Evidence: [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:20), [tests/test_cd_workflow_production_deploy_gate.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_cd_workflow_production_deploy_gate.py:64)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4148229640 -> 02b06b8d5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117952073 -> 02b06b8d5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117952077 -> 02b06b8d5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117952082 -> 02b06b8d5

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4148251408
Disposition: FIXED
Commit: see mapping entries below
Evidence: [deploy/PRODUCTION.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/deploy/PRODUCTION.md:204), [deploy/WORKFLOW.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/deploy/WORKFLOW.md:217), [docs/review/PR_1488_FIXED_MAPPING.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/docs/review/PR_1488_FIXED_MAPPING.md:1)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4148251408 -> 6943052e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117970414 -> 02b06b8d5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3117970442 -> 6943052e6

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4149616401
Disposition: FIXED
Commit: see mapping entries below
Evidence: [scripts/deploy_production.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/scripts/deploy_production.sh:369), [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:25)

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4149616401 -> ebed66e71
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#discussion_r3119216490 -> ebed66e71

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1488#pullrequestreview-4150072953
Disposition: NOT-A-BUG
Evidence: [scripts/deploy_production.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/scripts/deploy_production.sh:232), [scripts/deploy_production.sh](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/scripts/deploy_production.sh:369), [tests/test_deploy_contract_scripts.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/fix-docker-deploy-contract-reconciliation/tests/test_deploy_contract_scripts.py:104)
Reason: The duplicated compose-path normalization is confined to two fail-closed call sites with identical guarded behavior and test coverage; widening this docs/deploy lane into a refactor would increase scope without changing the deploy contract or fixing a correctness bug.

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
