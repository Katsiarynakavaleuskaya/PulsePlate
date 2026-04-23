<!-- markdownlint-disable MD034 -->
# PR 1365 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: `app/services/meili_swap_orchestration.py` (delete/create await `taskUid`; `run_full_pipeline` empty-doc guard), `scripts/meili_food_index_swap.py` (streaming JSONL), `docs/deploy/MEILISEARCH_ZERO_DOWNTIME_SWAP_RUNBOOK.md`, `tests/test_meili_swap_orchestration.py`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040128245 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040128250 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040157804 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040157806 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040157812 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040157818 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040157827 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040184880 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040184892 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040184896 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#discussion_r3040184902 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#pullrequestreview-4062742519 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#pullrequestreview-4062775056 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1365#pullrequestreview-4062807365 -> d4587d5795703d2a4fce7e2ac14fc28d7e631c83

## Merge Readiness

- [ ] All required checks pass (GitHub CI on current PR head after each push)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green locally

Notes: Resolve review threads on GitHub after verifying disposition; mirror `### Fixed in Commit Mapping` in the PR body if required by Phase 2 gates.

<!-- markdownlint-enable MD034 -->
