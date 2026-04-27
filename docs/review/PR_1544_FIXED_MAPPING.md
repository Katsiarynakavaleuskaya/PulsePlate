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
Commit: 6a4dfd325
Evidence: core/food_sources/source_preflight.py:235-249.
Reason: `collision_resolution` is normalized through explicit `Literal`-safe branching after validation, and no longer passes a raw `str` into the typed policy constructor.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#discussion_r3146869212 -> 6a4dfd325
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#pullrequestreview-4180427280 -> 6a4dfd325

Disposition: FIXED
Commit: 6a4dfd325
Evidence: `make typecheck` passes locally after `6a4dfd325`; `tests/test_install_codex_skills.py` remains aligned.
Reason: The earlier CodeRabbit process-gate issue was resolved by the code-level fixes in `scripts/install_codex_skills.sh` and `core/food_sources/source_preflight.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544#pullrequestreview-4180433907 -> 6a4dfd325

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
- `c8cbb2615` - `docs(review): map actionable bot findings for PR 1544`
- `6a4dfd325` - `fix: tighten collision resolution typing`
