<!-- markdownlint-disable MD034 -->
# PR #1435 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Latest actionable bot review is mapped below. If new review comments arrive, record
their disposition here before resolving them on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 0f601ed72
Evidence: `app/services/restaurant_postgres_read.py:51`; `app/services/restaurant_postgres_read.py:57`; `tests/test_restaurant_postgres_read.py:79`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446187 -> 0f601ed72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446194 -> 0f601ed72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476592 -> 0f601ed72

Disposition: FIXED
Commit: 0f601ed72
Evidence: `app/services/restaurant_postgres_read.py:116`; `app/services/restaurant_postgres_read.py:156`; `tests/test_restaurant_postgres_read.py:121`; `tests/test_restaurant_postgres_read.py:136`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095429150 -> 0f601ed72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446199 -> 0f601ed72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476597 -> 0f601ed72
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476600 -> 0f601ed72

Disposition: FIXED
Commit: 0f601ed72
Evidence: `tests/test_restaurant_postgres_read.py:204`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446232 -> 0f601ed72

Disposition: FIXED
Commit: 0f601ed72
Evidence: `tests/test_restaurant_shadow_parity.py:140`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446238 -> 0f601ed72

Disposition: FIXED
Commit: 0f601ed72
Evidence: `tests/test_restaurants_router.py:385`; `tests/test_restaurants_router.py:427`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446242 -> 0f601ed72

Disposition: FIXED
Commit: 3abe93218
Evidence: `tests/test_restaurants_router.py:348`; `tests/test_restaurants_router.py:387`; `tests/test_restaurants_router.py:425`; `tests/test_restaurants_router.py:467`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3096464873 -> 3abe93218

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`
Reason: evidence-pointer reconciliation for historical B1/B2/B3 packets now lives in `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md` (evidence: `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md:13-25`); runtime authority cutover remains deferred under `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`) until a separate governed cutover packet exists (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446204
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446208
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446213
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446217
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446225
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#issuecomment-4262405205

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446187`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446194`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446199`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446232`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446238`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446242`
Reason: the CodeRabbit status comment is only an index of the inline actionable items above and does not add a distinct unresolved requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#issuecomment-4262405219

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`
Reason: the Sourcery review contains high-level follow-through suggestions about engine reuse, env-flag utility centralization, and richer shadow-read diagnostics. Historical train reconciliation now lives in `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md` (evidence: `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md:13-25`), while those runtime/operability refinements remain deferred beyond merged B3 under `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`; ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4123393209

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446187`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446194`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476592`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095429150`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446199`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476597`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095476600`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446232`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446238`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446242`; `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`
Reason: the first CodeRabbit review is an aggregate summary of the inline findings already dispositioned above as FIXED or DEFERRED and does not add a separate unresolved requirement at the review level.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4123424402

Disposition: NOT-A-BUG
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446187`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3095446194`
Reason: the Cubic review is a review-level summary of the bounded timeout and deterministic ordering issues already fixed in commit `0f601ed72`; it does not introduce a distinct unresolved review-level requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4123456955

Disposition: NOT-A-BUG
Evidence: `app/services/restaurant_postgres_read.py:85`; `app/services/restaurant_postgres_read.py:96`; `tests/test_restaurant_postgres_read.py:79`; `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4123424402`
Reason: the second CodeRabbit review is a duplicate aggregate summary for a schema-error hygiene suggestion that does not correspond to a separate open thread; the review-level URL is mapped here so merge governance sees the duplicate as explicitly dispositioned.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4124383150

Disposition: FIXED
Commit: 3abe93218
Evidence: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#discussion_r3096464873`; `tests/test_restaurants_router.py:348`; `tests/test_restaurants_router.py:387`; `tests/test_restaurants_router.py:425`; `tests/test_restaurants_router.py:467`
Reason: the latest CodeRabbit review contains one actionable inline comment about env-precedence isolation in router tests, and that comment is fixed in commit `3abe93218`; the review-level URL is mapped to the same commit so governance sees the aggregate review as dispositioned.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#pullrequestreview-4124533202

Disposition: NOT-A-BUG
Evidence: `AGENTS.md:64`; `AGENTS.md:65`
Reason: the Codecov issue comment is advisory-only bot telemetry; merge truth for this repo is governed by the canonical local/CI gates, not by external bot commentary.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1435#issuecomment-4262488104

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
