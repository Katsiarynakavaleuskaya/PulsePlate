# PR 1701 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701
Branch: `codex/fix-codex-coordinator-start-bridge`
Head at open: `e3c3c40bc4ed569288739e2f23ff2f58ebcd34be`

## Summary

This artifact records the canonical review-thread mapping source of truth for
PR #1701. Mapping is evidence after fix or disposition; it is not a substitute
for fixes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Post-open review comments were checked after the PR left draft. Actionable
comments are mapped below with disposition evidence.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#discussion_r3203366433 -> 72fd7ae42f1bf3ebb6472ff358d0f335ab24f9c1
Disposition: FIXED
Commit: 72fd7ae42f1bf3ebb6472ff358d0f335ab24f9c1
Evidence: docs/review/PR_1701_PREMORTEM.md now cites concrete commit SHAs for premortem FIXED proof instead of the placeholder `follow-up governance commit in PR #1701`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#discussion_r3203450476 -> 83f0f69a786954da1214633066fc698553645005
Disposition: FIXED
Commit: 83f0f69a786954da1214633066fc698553645005
Evidence: tests/test_render_codex_start_prompt.py now covers packet role-order fallback without native_subagent_bridge, including the missing optional secondary_agents path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#pullrequestreview-4246264972 -> 83f0f69a786954da1214633066fc698553645005
Disposition: FIXED
Commit: 83f0f69a786954da1214633066fc698553645005
Evidence: The CodeRabbit review summary repeated the fallback coverage finding; tests/test_render_codex_start_prompt.py now covers packet role-order fallback without native_subagent_bridge and without optional secondary_agents.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#discussion_r3203548639 -> b9895eb71425e6e534e0d63d477582022776653b
Disposition: FIXED
Commit: b9895eb71425e6e534e0d63d477582022776653b
Evidence: scripts/orchestration/render_codex_start_prompt.py now iterates optional native bridge secondary/advisory lists through `bridge.get(...) or []`, and tests/test_render_codex_start_prompt.py covers packet bridge fields set to null.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#pullrequestreview-4246381746 -> b9895eb71425e6e534e0d63d477582022776653b
Disposition: FIXED
Commit: b9895eb71425e6e534e0d63d477582022776653b
Evidence: The CodeRabbit review summary's null-iteration finding is fixed in scripts/orchestration/render_codex_start_prompt.py and covered by tests/test_render_codex_start_prompt.py; its full-SHA consistency nit was fixed in 6270cb66bcfc4b440db09c0c88a4a08939c77cfd.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#pullrequestreview-4246437320 -> b9895eb71425e6e534e0d63d477582022776653b
Disposition: FIXED
Commit: b9895eb71425e6e534e0d63d477582022776653b
Evidence: tests/test_render_codex_start_prompt.py now catches FileNotFoundError around the premortem SKILL.md read and reports it with pytest.fail and the expected path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#discussion_r3203749010 -> 3e62b081669da162bc2d10586bf0e935c82e93c5
Disposition: FIXED
Commit: 3e62b081669da162bc2d10586bf0e935c82e93c5
Evidence: tests/test_render_codex_start_prompt.py now annotates all `capsys` fixture parameters as `pytest.CaptureFixture[str]`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1701#pullrequestreview-4246617415 -> 3e62b081669da162bc2d10586bf0e935c82e93c5
Disposition: FIXED
Commit: 3e62b081669da162bc2d10586bf0e935c82e93c5
Evidence: The CodeRabbit review summary repeated the untyped `capsys` fixture finding; tests/test_render_codex_start_prompt.py now includes explicit `pytest.CaptureFixture[str]` annotations for all affected tests.

## Pre-Open And Post-Open Governance Findings

Premortem and coordinator/role-agent findings are tracked in
[`docs/review/PR_1701_PREMORTEM.md`](./PR_1701_PREMORTEM.md). They are not
review-thread URLs, but their findings still require FIXED, NOT-A-BUG, or
DEFERRED closure before merge readiness or merge.
