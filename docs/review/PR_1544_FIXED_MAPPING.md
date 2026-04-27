# PR #1544 - Fixed in Commit Mapping (canonical)

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544>
Branch: `codex/fix-main-nightly-python-tests-2026-04-27`
Date: 2026-04-27

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was updated after the mandatory post-open `qa-engineer-agent -> bug-hunter` cycle and must stay aligned with PR body.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: bb8c9d3af
Evidence: scripts/install_codex_skills.sh:291-300.
Reason: `unlink_skills` now guards canonical path resolution failures before comparisons, and avoids duplicate canonicalization calls while preserving unlink safety for copied mirrors.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#discussion_r3146875221 -> bb8c9d3af

Disposition: FIXED
Commit: bb8c9d3af
Evidence: core/food_sources/source_preflight.py:235-239.
Reason: Removed a redundant cast warning path by returning `collision_resolution` directly from the validated Literal, restoring `make typecheck` pass under this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#discussion_r3146869212 -> bb8c9d3af
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#pullrequestreview-4180427280 -> bb8c9d3af

Disposition: FIXED
Commit: bb8c9d3af
Evidence: `make typecheck` passes locally after `bb8c9d3af`; `tests/test_install_codex_skills.py` remains aligned.
Reason: The earlier CodeRabbit process gate issue was resolved by the above code-level fixes that remove pre-existing blockages.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#pullrequestreview-4180433907 -> bb8c9d3af

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `make lint` (PASS)
- `make typecheck` (PASS)
- `make test-fast` (PASS)
- `make diff-cov` (blocked by local process semaphore env: `SC_SEM_NSEMS_MAX` in `run_main_test_shards`)
- `pre-commit run --all-files` (PASS)
- `python3 -m pytest tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources` (PASS)

## Initial Implementation Commits

- `bb8c9d3af` - `fix: harden skill unlink and collision resolution typing`
