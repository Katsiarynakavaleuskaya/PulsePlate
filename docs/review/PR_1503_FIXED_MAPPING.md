# PR #1503 — Fixed in Commit Mapping (canonical)

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

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: pending initial review and current-head CI cycle.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head GitHub checks after PR open.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head GitHub checks after PR open.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending initial review cycle.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending post-open review cycle on current head.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before commit `0b6ea053e`.
- [ ] `make verify` green on latest pushed head
  Evidence: not run for this lane yet.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: pending post-open review lane.

Post-open QA notes:

- `qa-engineer-agent` found the earlier seed mapping artifact used prose where
  the Phase2 parser requires `- No actionable review comments`; fixed in
  commit `256ba89d7`.
- `qa-engineer-agent` found scoped Docker lane docs still described provenance
  as deferred and the active ledger item still targeted a TBD PR; fixed in the
  follow-up commit after PR open.
- `bug-hunter` found CD verification was checking for GitHub signed
  attestations without first generating them and that the SBOM predicate used
  the BuildKit-incompatible `/v2.3` suffix; fixed by adding explicit
  GitHub-signed provenance/SBOM attestation steps before verification and by
  verifying the SPDX predicate `https://spdx.dev/Document`.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
- Dagger follow-up after Docker baseline and provenance stabilization
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
