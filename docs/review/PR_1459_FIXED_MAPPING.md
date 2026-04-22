# PR #1459 — Fixed in Commit Mapping (canonical)

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
Commit: 34429eb5c
Evidence: `frontend/src/api/wsClient.ts:24`; `frontend/src/api/__tests__/wsClient.test.ts:59`
Reason: The follow-up commit adds a fail-closed empty-base guard and a matching regression test on the same PR branch head, satisfying both live Sourcery inline findings with post-comment proof.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1459#discussion_r3102820122 -> 34429eb5c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1459#discussion_r3102820133 -> 34429eb5c

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1459_FIXED_MAPPING.md:16`
Reason: The Sourcery review shell is an aggregate wrapper around the two inline review threads mapped immediately above, so it adds no separate unresolved obligation once those thread-level fixes are recorded.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1459#pullrequestreview-4131612862

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
  Evidence: current-head GitHub checks after the latest push.
- [ ] Required checks complete (no pending jobs)
  Evidence: `gh pr checks 1459 --repo Katsiarynakavaleuskaya/PulsePlate`.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: GraphQL `reviewThreads` for PR `#1459`.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: `python3 scripts/orchestration/check_merge_ready.py --pr-number 1459 --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`.
- [ ] Pre-commit green on latest pushed head
  Evidence: local `pre-commit run --all-files`.
- [ ] `make verify` green on latest pushed head
  Evidence: local `make verify`.

## Deferred / Follow-ups

- None for this narrow PR lane.
