# PR #1495 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact is created immediately after the PR is opened per repo governance.
Record every actionable human/bot disposition here before resolving threads on GitHub.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `app/services/insight_runtime.py:123-191` declares `generate_traced_insight(...)` with a leading `*`, so all arguments are keyword-only and positional-call drift is impossible. The added `rollout_policy` parameter does not change positional compatibility because there is no positional call surface to preserve. The broader suggestion to hard-fail mixed `rollout_policy` plus legacy bool inputs is advisory future tightening, not a correctness blocker for this first-cut compatibility slice.
Reason: The reported “parameter reordering” breakage cannot occur on the live function signature, and the remaining high-level guidance does not identify a current behavioral regression in this bounded PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#discussion_r3123746307
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1495#pullrequestreview-4154439968

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: current-head CI is still in progress / needs the post-governance rerun on the latest branch head.
- [ ] Required checks complete (no pending jobs)
  Evidence: latest current-head required jobs are not complete yet.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: Sourcery review shell and inline thread are dispositioned here; GitHub thread resolution still needs to be performed after this artifact is pushed.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: current actionable Sourcery URLs are mapped above; re-check after any new bot activity remains mandatory.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed on the latest local branch head before governance update.
- [ ] `make verify` green on latest pushed head
  Evidence: this lane follows the user-approved narrow local gate bundle plus GitHub current-head CI as the heavyweight signal; no fresh full `make verify` claim is made here.
