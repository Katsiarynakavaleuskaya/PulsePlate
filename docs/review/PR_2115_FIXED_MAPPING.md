# PR #2115 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115

Branch: `codex/cfpropertylist-ruby34-compat`

## Summary

Pin the bounded `CFPropertyList 3.0.8` compatibility bridge required for the
Ruby 3.4.10 release-toolchain migration while preserving the rest of the
Fastlane/xcodeproj gem graph and all App Store workflow behavior.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/cfpropertylist_ruby34_compat.json`
  (local-only, gitignored).
- Pre-open role order executed:
  `agent-coordinator -> app-store-release-agent -> security-auditor -> marketing-strategist -> qa-engineer-agent`.
- The actual-diff premortem closed the missing `nkf` compatibility-anchor risk
  before PR open.
- Experiment Runner artifact:
  `artifacts/orchestration/experiments/results/cfpropertylist-ruby34-compat-oracle-result.json`
  (local-only, gitignored); accepted, 33 focused tests passed, shared tree
  untouched, contribution kind `oracle_review`.

## Implementation Commits

- `ecfa35461db561ff3d5d898a845277d04a2f7455` - pin the exact compatibility
  bridge, conservatively reconcile its lock entry, and add fail-closed graph
  guards.
- `c9c2159c3631d7a8481a9c14b39982a50f7f995d` - make the Phase-2 body and
  mapping evidence parser-safe and complete the post-open role checkboxes.
- `4677103c9a2f825508b6531e26e2fd82984dba0f` - reconcile the mandatory
  security-auditor status and record the sealed security-scan closure.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Pre-open packet role order completed.
- [x] Actual-diff premortem completed with no open blocker.
- [x] Experiment Runner oracle-only evidence accepted.
- [x] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` completed.
- [x] Codex Security diff scan completed for the material diff.
- [x] `pulseplate-pr-review` completed.
- [x] All current review threads dispositioned and resolved.
- [x] Current-head CI completed.
- [x] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4
Evidence: `docs/review/PR_2115_FIXED_MAPPING.md:38-39` and the post-comment evidence commit preserve both completed artifact-level checkboxes.
Reason: Discussion/mapping closure is complete, while merge-readiness and current-head CI stay separate pending gates.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571067367 -> 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4

Disposition: FIXED
Commit: ba3b3295cb7f78a2d9eea52a62e966d3c6cd6144
Evidence: `docs/review/PR_2115_FIXED_MAPPING.md:38-46` records the completed discussion/mapping/review-thread closure while retaining separate pending CI and merge-readiness gates.
Reason: The review-level CodeRabbit summary requested the same artifact-level checkbox closure as its inline thread; the post-review governance commit preserves the final parser-safe state.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#pullrequestreview-4685195469 -> ba3b3295cb7f78a2d9eea52a62e966d3c6cd6144

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor ecfa35461 HEAD` exits zero, and every `origin/main..HEAD` commit contains the canonical Experiment Runner co-author trailer.
Reason: The reviewer inspected a GitHub synthetic merge commit; the public PR branch preserves attribution on the implementation and governance commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571109947

Disposition: FIXED
Commit: 4677103c9a2f825508b6531e26e2fd82984dba0f
Evidence: `docs/review/PR_2115_FIXED_MAPPING.md:97-100`
Reason: Security Review now records the completed security-auditor and sealed diff-scan closure consistently with the checked role-chain status.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571109952 -> 4677103c9a2f825508b6531e26e2fd82984dba0f

Disposition: NOT-A-BUG
Evidence: On the public branch head `ba3b3295cb7f78a2d9eea52a62e966d3c6cd6144`, `git merge-base --is-ancestor ecfa35461db561ff3d5d898a845277d04a2f7455 HEAD` exits zero and every commit in `origin/main..HEAD` contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
Reason: The reviewer evaluated GitHub's synthetic merge commit `e719f874...`, not the public PR branch history used by the repository attribution contract; the accepted oracle contribution and canonical trailer are preserved on every branch commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571404141

Disposition: NOT-A-BUG
Evidence: On the public branch head `ba3b3295cb7f78a2d9eea52a62e966d3c6cd6144`, `git merge-base --is-ancestor 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4 HEAD` exits zero.
Reason: The mapped FIXED proof is reachable from the actual PR branch head; the non-reachability assertion is an artifact of reviewing GitHub's synthetic merge commit `e719f874...` as a standalone commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571404148

Disposition: NOT-A-BUG
Evidence: GitHub PR #2115 reports public `headRefOid=474cde8926581c829517f537ecb986bec31e400b`; in that branch history, `git merge-base --is-ancestor 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4 474cde8926581c829517f537ecb986bec31e400b` exits zero, as do the checks for the other mapped FIXED commits.
Reason: The reviewed `5a03d460...` object is GitHub's synthetic merge commit in a shallow reviewer checkout, not the PR branch head. Missing shallow ancestry is not evidence that the public branch lost its mapped commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571484039

Disposition: NOT-A-BUG
Evidence: GitHub PR #2115 reports public `headRefOid=474cde8926581c829517f537ecb986bec31e400b`; every commit in `origin/main..474cde8926581c829517f537ecb986bec31e400b`, including that head, contains `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`.
Reason: The reviewed `5a03d460...` object is GitHub's synthetic merge commit and is not the public branch head governed by the attribution contract; the required public attribution is present throughout the branch history.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571484042

## Experiment Runner Evidence

Artifact: artifacts/orchestration/experiments/results/cfpropertylist-ruby34-compat-oracle-result.json

The artifact is local-only and gitignored. It was accepted with 33 focused
tests passing, no shared-tree mutation, and contribution kind `oracle_review`.

## Validation Evidence

- PASS: orchestration preflight and agent consistency.
- PASS: 89 focused compatibility/toolchain/App Store tests.
- PASS: `bundle _2.4.22_ check --gemfile ios/Gemfile`.
- PASS: `make validate-changed`.
- PASS: `pre-commit run --all-files`.
- PASS: pre-push pip-audit, focused backend tests, and full-repo Bandit.
- PENDING: canonical current-head GitHub CI and strict merge readiness.

## Security Review

- PASS: mandatory post-open security-auditor found no security actionable.
- PASS: sealed Codex Security scan `07492320-eaa5-45f8-b238-2532b7e6a35c`
  reviewed all four diff rows through discovery, validation, and attack-path
  closure; zero reportable findings survived final policy adjustment.
- PASS: `pulseplate-pr-review` found no deterministic correctness, security,
  release, or governance finding on the final four-file diff.

## Risks / Rollback

If Ruby 3.4.10 CI still exposes a compatibility regression, revert this PR as
one unit and keep PR #2113 plus App Store upload workflows blocked until a
supported graph is restored. Do not bypass the compatibility guard or broaden
the gem update as an emergency workaround.

## Deferred / Follow-ups

PR #2113 remains the owner of the Ruby 3.4.10 workflow migration and is blocked
until this prerequisite is merged and rebased.
