# PR #1644 Fixed in Commit Mapping

<!-- markdownlint-disable MD013 -->

## Summary

Add `pulseplate-premortem-risk-review` skill for stress-testing high-downside PulsePlate plans before merge or launch.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

- Sourcery `scripts/orchestration/skill_router.py:1100` -> 43e45412c: add `pre-mortem` and `pre mortem` keyword variants
- Sourcery `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:50` -> 43e45412c: reword "being premortemed" to standard English
- CodeRabbit `tools/codex_skills/pulseplate-premortem-risk-review/SKILL.md:63` -> 43e45412c: replace hardcoded `--task-class "Orchestration"` with placeholder
- CodeRabbit `tests/test_skill_router.py:1817` -> 43e45412c: tighten Figma-bleed test (remove `design-system` trigger, assert both `figma` and `figma-implement-design` absent)
- Codex connector `scripts/orchestration/skill_router.py:1079` (NOT-A-BUG: `min_score=6` is intentional high threshold; skill fires when multiple signals combine; same threshold as `pulseplate-pr-review` and `pulseplate-agent-product`)

## Merge Readiness

- [x] CI green (all canonical checks pass; iOS/coverage correctly skipped for docs/orchestration-only PR)
- [x] Skill routing tests green (141 passed)
- [x] Review mapping artifact created
- [ ] No actionable bot comments remain
- [ ] Mandatory wait-window elapsed
