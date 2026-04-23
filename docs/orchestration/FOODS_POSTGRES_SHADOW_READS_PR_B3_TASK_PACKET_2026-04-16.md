# Foods PostgreSQL Shadow Reads PR-B3 Task Packet

**Effective date:** 2026-04-16 (`America/New_York`)
**Status:** Historical merged execution packet
**Mode:** coordinator-owned backend/runtime parity lane (closed)

## Goal

Land one narrow runtime lane that adds PostgreSQL shadow reads and parity checks for
restaurant search/menu while preserving SQLite as canonical response authority.

## Relationship to the Follow-Through Train

- This packet owns only **PR-B3**.
- The execution train is fixed as:
  - `PR-B1`: foods snapshot promotion into PostgreSQL `foods` (merged in PR `#1413`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - `PR-B2`: restaurant relational bridge for importer persistence (merged in PR `#1419`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - `PR-B3`: restaurant PostgreSQL shadow reads + parity checks (merged in PR `#1435`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - cutover (deferred): runtime read-switch / PostgreSQL authority change after B3 (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`; backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`)
- `PR-B3` merged in PR `#1435` on April 16, 2026 (`America/New_York`) (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:10-10`).
- Post-B3 docs/governance reconciliation now lives in:
  - `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`)
- The next bounded implementation lane after post-B3 closeout is:
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`)
- `PR-B3` is shadow-only and does not claim PostgreSQL-backed runtime authority (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`).

## Source of Truth

- Repo code remains the final source of truth for runtime and contract boundaries.
- This lane must stay grounded in:
  - `app/routers/restaurants.py`
  - `app/services/restaurant_store.py`
  - `app/services/restaurant_postgres_bridge.py`
  - `app/schemas/restaurants.py`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`

## PR Metadata

- Branch: `feat/pr-b3-restaurant-postgres-shadow-reads`
- PR title: `feat(data): add restaurant PostgreSQL shadow reads and parity checks`
- Merge method: **merge commit** via `gh pr merge --merge --delete-branch`

## In Scope

- Add read-only PostgreSQL adapter for:
  - `search_restaurants`
  - `get_restaurant_menu`
- Add explicit shadow-read compatibility wrapper in `app/routers/restaurants.py`:
  - SQLite remains canonical response path
  - PostgreSQL read executes only in shadow mode
- Add parity normalization/comparison for restaurant search/menu results
- Add deterministic tests for:
  - parity match and mismatch
  - ordering drift mismatch
  - shadow fail-open behavior for HTTP responses
- Keep parity v1 scoped to common runtime fields and intentionally exclude
  provenance-only fields not available in PostgreSQL foundation tables

## Out of Scope

- No public cutover to PostgreSQL runtime authority
- No migration/parity work for `source_catalog`, `user_submissions`, `submission_audit`
- No submission/moderation authority migration from SQLite
- No `food_id` linking policy changes
- No OpenAPI/deploy/Meili/vector scope widening

## Role Order

1. `agent-coordinator`
2. `architecture-specialist`
3. `backend-engineer`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

Add `security-auditor` only if this lane introduces new required env/deploy/auth surface.
Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## Lifecycle Notes

- Work from a dedicated lane worktree, not main checkout
- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Open as **draft PR** after packet + backlog realignment and first local stabilization
- Immediately after opening PR:
  - create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`
  - run post-open synthesis with `--pr-phase post_open_review`
- Current-head merge verdict is canonical only through:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Validation Plan

- Targeted tests:
  - `pytest -q tests/test_restaurant_postgres_read.py tests/test_restaurant_shadow_parity.py`
  - plus router shadow behavior tests in the touched restaurant router test surface
- Full local gates before undraft:
  - `pre-commit run --all-files`
  - `make verify`

## Acceptance Criteria

- PostgreSQL read adapter exists for restaurant search/menu only
- Router keeps SQLite canonical responses; PostgreSQL executes as default-off shadow lane
- Parity checks are explicit and deterministic
- Provenance drift handling is intentional and test-covered
- Submission/moderation flows remain on SQLite unchanged
- `PR-B3` introduces no runtime authority cutover claim
