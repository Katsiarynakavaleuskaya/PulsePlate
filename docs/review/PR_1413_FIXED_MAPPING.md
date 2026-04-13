<!-- markdownlint-disable MD034 -->
# PR 1413 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ddd15df92
Evidence: `scripts/promote_foods_snapshot_to_postgres.py:68`; `scripts/promote_foods_snapshot_to_postgres.py:71`; `scripts/promote_foods_snapshot_to_postgres.py:85`; `scripts/promote_foods_snapshot_to_postgres.py:194`; `tests/test_promote_foods_snapshot_to_postgres.py:215`; `tests/test_promote_foods_snapshot_to_postgres.py:246`; `tests/test_promote_foods_snapshot_to_postgres.py:493`; `tests/test_promote_foods_snapshot_to_postgres.py:545`
Reason: The follow-up commit removes the deprecated SQLAlchemy `future=True` engine argument, drops the dead first definition of `REQUIRED_SOURCE_COLUMNS`, aligns the integration fixtures with the actual `nutrition_inputs_json -> list` contract, and tightens the CLI success assertion to the real `main() -> int` behavior. The false-negative fixture issue was also identified by cubic.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#pullrequestreview-4099306933 -> ddd15df92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#pullrequestreview-4099333522 -> ddd15df92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073551798 -> ddd15df92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073556736 -> ddd15df92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073581105 -> ddd15df92

Disposition: NOT-A-BUG
Evidence: `scripts/promote_foods_snapshot_to_postgres.py:116`; `scripts/promote_foods_snapshot_to_postgres.py:125`; `scripts/promote_foods_snapshot_to_postgres.py:126`; `tests/test_promote_foods_snapshot_to_postgres.py:477`; `tests/test_promote_foods_snapshot_to_postgres.py:628`
Reason: The aggregate Sourcery summary is fully triaged by the thread-level entries below. The only real regression it surfaced was the fixture-type mismatch already fixed in `ddd15df92`; the remaining items in that summary are compatibility or enhancement suggestions, so the summary URL itself does not represent an additional unresolved defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#pullrequestreview-4099299619

Disposition: NOT-A-BUG
Evidence: `scripts/promote_foods_snapshot_to_postgres.py:116`; `scripts/promote_foods_snapshot_to_postgres.py:125`; `scripts/promote_foods_snapshot_to_postgres.py:126`; `tests/test_promote_foods_snapshot_to_postgres.py:477`
Reason: The report intentionally keeps both `checksum` and `source_checksum` during the B1 promotion lane to preserve additive compatibility for local artifact consumers while still exposing `checksum` as the canonical field checked by the tests. Removing the alias here would widen the output contract for a non-runtime helper beyond the packet's narrow scope.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073549993

Disposition: NOT-A-BUG
Evidence: `scripts/promote_foods_snapshot_to_postgres.py:85`; `scripts/promote_foods_snapshot_to_postgres.py:205`; `scripts/promote_foods_snapshot_to_postgres.py:214`; `scripts/promote_foods_snapshot_to_postgres.py:242`; `tests/test_promote_foods_snapshot_to_postgres.py:635`; `tests/test_promote_foods_snapshot_to_postgres.py:670`; `tests/test_promote_foods_snapshot_to_postgres.py:721`
Reason: These comments request extra coverage, not a correctness fix. The current lane already fails closed on missing `foods`, missing required source columns, malformed JSON, and legacy snapshots without optional JSON columns; the suggested empty-snapshot, wrong-container-shape, and missing-required-column additions are valid future hardening ideas but do not indicate that the current implementation is incorrect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073550005
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073550015
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073550032

Disposition: NOT-A-BUG
Evidence: `scripts/promote_foods_snapshot_to_postgres.py:29`; `scripts/promote_foods_snapshot_to_postgres.py:35`; `scripts/promote_foods_snapshot_to_postgres.py:205`; `scripts/promote_foods_snapshot_to_postgres.py:287`; `docs/orchestration/FOODS_POSTGRES_PROMOTION_PR_B1_TASK_PACKET_2026-04-13.md:40`
Reason: The flagged SQL strings interpolate only repo-owned constants (`SOURCE_TABLE_NAME = "foods"`, `CHECKSUM_SORT_KEY = "id"`) inside a packet that fixes the source contract to `data/food.sqlite::foods`. There is no user-controlled identifier or query fragment here, so the opengrep SQL-injection heuristic is a false positive for this offline promotion helper.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073550045
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1413#discussion_r3073550050

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
