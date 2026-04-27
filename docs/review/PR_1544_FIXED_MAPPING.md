# PR #1544 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1544>
Branch: `codex/fix-main-nightly-python-tests-2026-04-27`
Date: 2026-04-27

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- 0f2825bc3 -> stabilize nightly dependency install + codex skill path marker

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `make lint` (PASS)
- `make typecheck` (fails: pre-existing `core/food_sources/source_preflight.py:238` cast warning)
- `make test-fast` (PASS)
- `make diff-cov` (blocked by local process semaphore env: `SC_SEM_NSEMS_MAX` in `run_main_test_shards`)
- `pre-commit run --all-files` (PASS)
- `python3 -m pytest tests/test_install_codex_skills.py::test_repo_agents_skills_mirror_points_to_codex_skill_sources` (PASS)
