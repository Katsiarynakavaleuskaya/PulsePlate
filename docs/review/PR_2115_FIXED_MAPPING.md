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
- [ ] Current-head CI completed.
- [ ] Strict authenticated merge readiness and mandatory wait window completed.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4
Evidence: `docs/review/PR_2115_FIXED_MAPPING.md:38-39` and the post-comment evidence commit preserve both completed artifact-level checkboxes.
Reason: Discussion/mapping closure is complete, while merge-readiness and current-head CI stay separate pending gates.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571067367 -> 66c89fe9c0c02badc0a2a6060b7a3607c7b853e4

Disposition: NOT-A-BUG
Evidence: `git merge-base --is-ancestor ecfa35461 HEAD` exits zero, and every `origin/main..HEAD` commit contains the canonical Experiment Runner co-author trailer.
Reason: The reviewer inspected a GitHub synthetic merge commit; the public PR branch preserves attribution on the implementation and governance commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571109947

Disposition: FIXED
Commit: 4677103c9a2f825508b6531e26e2fd82984dba0f
Evidence: `docs/review/PR_2115_FIXED_MAPPING.md:97-100`
Reason: Security Review now records the completed security-auditor and sealed diff-scan closure consistently with the checked role-chain status.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2115#discussion_r3571109952 -> 4677103c9a2f825508b6531e26e2fd82984dba0f

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
