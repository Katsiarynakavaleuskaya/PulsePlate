# PR #1436 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#discussion_r3096626954 -> 6d7b993da
Disposition: FIXED
Commit: 6d7b993da
Evidence: `scripts/orchestration/skill_router.py:120-126` now excludes `pulseplate-app-store-release` from the docs-only envelope, and `tests/test_skill_router.py:1371-1385` locks the App Store runbook docs-only regression called out in the Codex thread.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#pullrequestreview-4124715979 -> 6d7b993da
Disposition: FIXED
Commit: 6d7b993da
Evidence: `scripts/orchestration/skill_router.py:120-126` and `tests/test_skill_router.py:1371-1385` close Cubic's docs-only routing concern for the new release skill.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#discussion_r3096643833 -> 6d7b993da
Disposition: FIXED
Commit: 6d7b993da
Evidence: `scripts/orchestration/skill_router.py:120-126` adds the missing docs-only exclusion, while `tests/test_skill_router.py:1352-1385` proves the filtered envelope contract stays deterministic for generic docs and App Store rollout docs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#pullrequestreview-4124688108 -> 6d7b993da
Disposition: FIXED
Commit: 6d7b993da
Evidence: `tools/codex_skills/pulseplate-app-store-release/SKILL.md:24-27` replaces brittle `sed -n '1,220p'` snippets with pattern-based `rg -n -C 2` lookups, and the file-specific rollout-runbook prefix remains intentional because `scripts/orchestration/skill_router.py:120-126` now strips docs-only App Store runbook edits from implementation routing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#discussion_r3096698261 -> 68d860bb9
Disposition: FIXED
Commit: 68d860bb9
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md:124-131` now documents the docs-only suppression and promotion criteria for `pulseplate-app-store-release`, and commit `68d860bb9` satisfies the root `AGENTS.md:2101-2104` requirement for a `docs(agents): update instructions` commit on routing-behavior changes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#pullrequestreview-4124772172 -> 68d860bb9
Disposition: FIXED
Commit: 68d860bb9
Evidence: `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md:124-131` adds the required operator routing guidance for the new skill, while `tools/codex_skills/pulseplate-app-store-release/SKILL.md:55-58` also incorporates the remaining guardrail wording cleanup from the CodeRabbit review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#discussion_r3096706208 -> 68d860bb9
Disposition: FIXED
Commit: 68d860bb9
Evidence: `tools/codex_skills/pulseplate-app-store-release/SKILL.md:24-27` now uses a case-insensitive pattern that matches `Validation-Only Path`, `Reviewer Notes Update Procedure`, protected-upload guidance, App Privacy, and rollback sections from the App Store rollout runbook.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1436#pullrequestreview-4124780246 -> 68d860bb9
Disposition: FIXED
Commit: 68d860bb9
Evidence: `tools/codex_skills/pulseplate-app-store-release/SKILL.md:24-27` fixes the runbook-section matcher called out by Cubic, and `tools/codex_skills/pulseplate-app-store-release/SKILL.md:55-58` keeps the updated guardrail wording aligned with the latest review pass.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head
