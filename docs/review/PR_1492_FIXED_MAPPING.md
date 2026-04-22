# PR #1492 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending after remediation head and current review-cycle reruns.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending after remediation head and current review-cycle reruns.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending current remediation for open review threads.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending current remediation for open CodeRabbit/Sourcery/Codex findings.
- [ ] Pre-commit green on latest pushed head
  Evidence: pending after remediation head is committed.
- [ ] `make verify` green on latest pushed head
  Evidence: not run for this lane; GitHub current-head checks remain the heavy signal.

## Deferred / Follow-ups

- hard image-size budget cap / failure threshold
- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
- provenance / attestation recovery
- Dagger or alternate control-plane work
