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

Disposition: FIXED
Commit: 39d77cf8c
Evidence: `pytest -q tests/test_check_docker_provenance_attestation.py tests/test_python_supply_chain_controls.py` -> 54 passed. The fix commit hardens the helper timeout, parser, failure evidence path, workflow verification condition, workflow-contract tests, ADR Markdown links, ADR evidence anchors, and ledger traceability.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4163080758 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131356723 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131356747 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131356752 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131356759 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131357170 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131386002 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131386015 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131386020 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131386032 -> 39d77cf8c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4163115645 -> 39d77cf8c

Disposition: FIXED
Commit: 0fdeaa100
Evidence: `python3 scripts/ci/check_pr_body_phase2_gates.py --pr-number 1503 --body "$(gh pr view 1503 --json body --jq .body)"` -> passed; canonical artifact now enumerates bot/agent dispositions instead of `No actionable review comments`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3131386028 -> 0fdeaa100

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1503_FIXED_MAPPING.md:43-48` keeps the actual final merge-cycle items (`Mandatory wait-window satisfied`, `Current-head CI is green`, `Required checks complete`) unchecked while only already-confirmed local items remain checked below.
Reason: the CodeRabbit follow-up misread the current artifact state; the merge-cycle checkboxes it flagged are already unchecked on the latest head, so no code or docs change is required beyond recording the disposition.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#discussion_r3133574264
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4165661733
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4165727884

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1503_FIXED_MAPPING.md:49-64` keeps the merge-readiness checklist intentionally conservative and uses review-level URLs as rollup references for artifact-only follow-ups.
Reason: the review-level CodeRabbit summary is a rollup comment over optional style guidance and checklist-state guidance on this same artifact; recording the review URL here is sufficient and does not require a distinct commit mapping entry.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4165903700

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1503_FIXED_MAPPING.md:81-83` now records the exact historical fix commit `a61b7c1d9` for the QA note that previously said `follow-up commit after PR open`.
Reason: the review-level CodeRabbit summary is an artifact auditability rollup; the underlying note is now concrete and no implementation change is required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1503#pullrequestreview-4165977146

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: latest bot/review activity was the post-ready review cycle on April 23, 2026; coordinator reran checks and delayed merge claim until after the subsequent push + CI cycle.
- [ ] Current-head CI is green for PR branch head
  Evidence: the next PR head after this governance-evidence update still needs a green CI cycle before merge claim.
- [ ] Required checks complete (no pending jobs)
  Evidence: the next PR head after this governance-evidence update still needs a completed green CI cycle before merge claim.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: GraphQL review-thread check returned `0` unresolved threads after coordinator resolution pass.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: Sourcery, CodeRabbit, and Codex actionables are mapped above, including review-level URLs `#pullrequestreview-4163080758`, `#pullrequestreview-4165661733`, and `#pullrequestreview-4165727884`.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed on the governance-evidence tree before push.
- [ ] `make verify` green on latest pushed head
  Evidence: the governance-refresh head after this artifact update still needs a fresh exact-head `make verify` pass before merge claim.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: `qa-engineer-agent` completed on the current head; `bug-hunter` still needs to run after the governance-refresh push.

Post-open QA notes:

- `qa-engineer-agent` found the earlier seed mapping artifact used prose where
  the Phase2 parser requires `- No actionable review comments`; fixed in
  commit `256ba89d7`.
- `qa-engineer-agent` found scoped Docker lane docs still described provenance
  as deferred and the active ledger item still targeted a TBD PR; fixed in
  commit `a61b7c1d9`.
- `bug-hunter` found CD verification was checking for GitHub-signed
  attestations without first generating them and that the SBOM predicate used
  the BuildKit-incompatible `/v2.3` suffix; fixed by adding explicit
  GitHub-signed provenance/SBOM attestation steps before verification and by
  verifying the SPDX predicate `https://spdx.dev/Document`.
- Sourcery, Codex, and CodeRabbit found post-ready hardening gaps in helper
  timeout/configurability, parser shape tolerance, failure evidence emission,
  verification-step execution after attestation failures, production workflow
  contract coverage, ADR markdownlint/evidence anchors, and ledger
  traceability; fixed in commit `39d77cf8c`.

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md` line 540 (`P1: Shared Safety audit script after install-profile split`)
- Dagger follow-up after Docker baseline and provenance stabilization
  Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-dagger-pilot-after-docker-baseline`
