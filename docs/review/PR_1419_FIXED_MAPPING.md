<!-- markdownlint-disable MD034 -->
# PR 1419 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review comments must be dispositioned here before resolving them on
GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076030998 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: `app/services/restaurant_postgres_bridge.py:380-396` now projects menu-item payloads onto the reflected table columns before `pg_insert(...).values(...)`, and `tests/test_restaurant_postgres_bridge.py:206-242` proves `chain_name` and `country` are excluded from the compiled `restaurant_menu_items` INSERT.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#pullrequestreview-4102167844 -> 1fb3ff258
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076032426 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: `app/services/restaurant_postgres_bridge.py:417-423` now places the required `pg_url` keyword-only argument before the defaulted keyword-only parameters, so the bridge signature matches the review request and the module imports cleanly under the targeted test run.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#pullrequestreview-4102186808 -> 1fb3ff258
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076048688 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: cubic identified the same insert-payload bug as the Codex thread, and the fix is the same projection guard at `app/services/restaurant_postgres_bridge.py:380-396` backed by `tests/test_restaurant_postgres_bridge.py:206-242`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054173
Disposition: NOT-A-BUG
Evidence: `app/services/restaurant_postgres_bridge.py:266-317` derives chain rows from all grouped menu records per `chain_id`, not from the single duplicate winner chosen by `_choose_preferred_record`, and `tests/test_restaurant_postgres_bridge.py:127-163` already proves the selected chain country comes from the grouped-record set (`CA`) rather than import order.
Reason: Adding `chain_name` / `country` to `_MENU_COMPLETENESS_FIELDS` is unnecessary for chain determinism because `_build_chain_records` aggregates and sorts chain metadata across the entire grouped record set.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054178
Disposition: NOT-A-BUG
Evidence: `app/services/restaurant_postgres_bridge.py:101-120` intentionally mirrors the existing importer compatibility contract, and the SQLite source-of-truth path keeps the same best-effort behavior in `app/services/restaurant_store.py:72-88`.
Reason: This B2 bridge is scoped to importer parity, so malformed optional numeric text continues to degrade to `None` instead of failing the import, matching the established SQLite importer/store behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054181 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: `app/services/restaurant_postgres_bridge.py:393-414` now annotates `_build_menu_item_upsert(...) -> PostgresInsert`, and the new `PostgresInsert` import at `app/services/restaurant_postgres_bridge.py:20` documents the concrete SQLAlchemy statement type.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054184 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: `app/services/restaurant_postgres_bridge.py:380-396` filters each record down to real table columns before building the PostgreSQL insert statement, and `tests/test_restaurant_postgres_bridge.py:206-242` covers the exact `chain_name` / `country` leak the review flagged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054195 -> 1fb3ff258
Disposition: FIXED
Commit: 1fb3ff258
Evidence: `docs/orchestration/FOODS_POSTGRES_RESTAURANT_BRIDGE_PR_B2_TASK_PACKET_2026-04-13.md:79-94` now explicitly labels the section as `Primary Implementation Files`, explains that the full PR inventory also includes merge-sync artifacts, and lists the missing review/dependency files called out in the review.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#pullrequestreview-4102194121
Disposition: NOT-A-BUG
Evidence: the aggregate CodeRabbit review is fully decomposed into the inline thread dispositions above, including FIXED entries for the real bridge/doc issues and NOT-A-BUG entries where the review proposed changing established importer semantics.
Reason: The review-summary URL does not add a separate defect beyond the individual inline comments that are already dispositioned explicitly in this artifact.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1419#discussion_r3076054197 -> a17be2149
Disposition: FIXED
Commit: a17be2149
Evidence: `docs/review/PR_1419_FIXED_MAPPING.md:14-54` in commit `a17be2149` replaced the blanket `- No actionable review comments` placeholder with explicit per-thread FIXED / NOT-A-BUG dispositions and proof, satisfying the review-governance contract for this PR.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`

<!-- markdownlint-enable MD034 -->
