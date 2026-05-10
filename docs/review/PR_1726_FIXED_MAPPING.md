# PR #1726 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1726
Branch: `codex/fix-replay-sort-crash-on-supersession`
Title: `fix(evidence): replay supersession chains topologically`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Local Evidence

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `.venv/bin/python -m pytest -q tests/core/evidence/test_replay.py`
- `make validate-min`
- `pre-commit run --all-files`
- `make validate-changed`
- `gh pr checks 1726` (local snapshot after last push)

## Premortem Risk Review

No new P0/P1 risks identified beyond existing scope.

## Bug-Hunter Pass

- Renamed test name to remove incorrect ordering implication
  (`test_existing_supersession_chain_replays_all_entries`) and added
  `test_existing_supersession_chain_supports_cumulative_supersedes` to cover
  cumulative supersede replay behavior.
- Existing idempotency/conflict/orphan behavior preserved in replay seeding.
- Added linear-traversal and orphaning edge-case tests in
  `tests/core/evidence/test_replay.py`:
  - `test_existing_supersession_chain_with_multiple_leaves_is_orphaned`
  - `test_existing_supersession_chain_with_disconnected_supersession_cycle_is_orphaned`
  - `test_existing_supersession_chain_with_cumulative_supersede_uses_linear_traversal`

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: core/evidence/replay.py:206, tests/core/evidence/test_replay.py:288

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1726#discussion_r3215460445 -> c5d4990be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1726#discussion_r3215463433 -> c5d4990be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1726#pullrequestreview-4259863855 -> c5d4990be
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1726#pullrequestreview-4259960495 -> c5d4990be

## Merge Readiness

- review-thread disposition mapped for all actionable threads
- pending current-head checks and required CI parity in PR branch
