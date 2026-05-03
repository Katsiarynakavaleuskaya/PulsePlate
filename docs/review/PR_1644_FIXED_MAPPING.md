# PR #1644 Fixed in Commit Mapping

<!-- markdownlint-disable MD013 -->

## Summary

Add `pulseplate-premortem-risk-review` skill for stress-testing high-downside PulsePlate plans before merge or launch.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178001793 -> de31d6e3a
Disposition: FIXED
Commit: de31d6e3a
Evidence: scripts/orchestration/skill_router.py:1100 — added `pre-mortem` and `pre mortem` keyword variants

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178001795 -> de31d6e3a
Disposition: FIXED
Commit: de31d6e3a
Evidence: tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:50 — reworded "being premortemed" to standard English

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178010065 -> de31d6e3a
Disposition: FIXED
Commit: de31d6e3a
Evidence: tests/test_skill_router.py:1810 — removed `design-system` trigger, assert both `figma` and `figma-implement-design` absent

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178010066 -> de31d6e3a
Disposition: FIXED
Commit: de31d6e3a
Evidence: tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:62 — replaced hardcoded `--task-class "Orchestration"` with placeholder

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178003390
Disposition: NOT-A-BUG
Evidence: scripts/orchestration/skill_router.py:1079
Reason: `min_score=6` is intentional high threshold; skill fires when multiple signals combine; same threshold as `pulseplate-pr-review` and `pulseplate-agent-product`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1644#discussion_r3178030380
Disposition: NOT-A-BUG
Evidence: scripts/orchestration/skill_router.py:1079
Reason: Repeat of min_score threshold suggestion; intentional design — see disposition for discussion_r3178003390

## Merge Readiness

- [x] CI green (all canonical checks pass; iOS/coverage correctly skipped for docs/orchestration-only PR)
- [x] Skill routing tests green (141 passed)
- [x] Review mapping artifact created
- [ ] No actionable bot comments remain
- [ ] Mandatory wait-window elapsed
