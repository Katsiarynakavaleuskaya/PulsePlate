# PR 1313 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 61dc2f4b
Evidence: AGENTS.md:22
Reason: Added the required `docs(agents): update instructions` commit and aligned the validation-helper wording to the branch-scoped merge-base behavior implemented in this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#discussion_r3032097012 -> 61dc2f4b

Disposition: NOT-A-BUG
Evidence: legacy_app.py:1513
Reason: `/api/v1/health` is an implemented compatibility alias that delegates to `/health`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#discussion_r3032097015

Disposition: FIXED
Commit: 832f662f
Evidence: docs/review/PR_1313_FIXED_MAPPING.md:14
Reason: Reset the merge-readiness checklist so those items stay unchecked until the final merge pass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#discussion_r3032097017 -> 832f662f

Disposition: FIXED
Commit: d6b1db1b
Evidence: README.md:256; scripts/quick_check.sh:13; scripts/run-backend-tests-pre-commit.sh:53
Reason: Closed the remaining CodeRabbit review-level follow-ups by preferring the active virtualenv for syntax checks, removing the contradictory dev-compose port literal, and stopping branch-diff resolution at the first merge-base candidate.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#pullrequestreview-4054939041 -> d6b1db1b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#pullrequestreview-4054961272 -> d6b1db1b

Disposition: NOT-A-BUG
Evidence: git log --oneline origin/main..HEAD includes `61dc2f4b docs(agents): update instructions`
Reason: The follow-up README thread re-reported the dedicated docs(agents) commit requirement after that exact commit was already present on the branch, so no new code change was required.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#discussion_r3032183185

Disposition: FIXED
Commit: PENDING_COMMIT
Evidence: scripts/quick_check.sh:23
Reason: Switched staged Python file discovery to a NUL-safe `git diff --name-only -z --diff-filter=ACMR` loop so filenames with spaces/newlines and renamed files are handled correctly.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#discussion_r3032183188 -> PENDING_COMMIT
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1313#pullrequestreview-4055021657 -> PENDING_COMMIT

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
Notes: PR `#1313` is the onboarding/validation compatibility lane. Keep scope limited to docs-first startup guidance, validation-loop clarity, and the associated helper commands/docs updates. Do not widen it into runtime observability or unrelated product/docs work.
