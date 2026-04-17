# Foods PostgreSQL Restaurant Bridge PR-B2 Task Packet

**Effective date:** 2026-04-13 (`America/New_York`)
**Status:** Historical merged execution packet
**Mode:** coordinator-owned backend/data bridge lane (closed)

## Goal

Land one narrow additive lane that bridges the existing MenuStat-compatible
restaurant importer into PostgreSQL `restaurant_chains` /
`restaurant_menu_items` without widening scope into runtime read-switch,
moderation/source parity, or public API cutover.

## Relationship to the Follow-Through Train

- This packet owns only **PR-B2**.
- The execution train is fixed as:
  - `PR-B1`: foods snapshot promotion into PostgreSQL `foods` (merged in PR `#1413`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - `PR-B2`: restaurant relational bridge for importer persistence (merged in PR `#1419`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - `PR-B3`: restaurant PostgreSQL shadow reads + parity checks (merged in PR `#1435`; evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`)
  - cutover (deferred): runtime read-switch / PostgreSQL authority change after B3 (ADR: `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:11-24`; backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`)
- `PR-B1`, `PR-B2`, and `PR-B3` are already merged (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:7-10`).
- Post-B3 docs/governance reconciliation now lives in:
  - `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`)
- The next bounded implementation lane after post-B3 closeout is:
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership` (evidence: `docs/review/FOODS_POSTGRES_TRAIN_MERGED_STATE_CANON_2026-04-17.md:12-14`)
- `PR-B2` stays importer-only. It does not claim that current restaurant runtime
  is already PostgreSQL-backed.

## Source of Truth

- Repo code remains the final source of truth for vocabulary, CLI compatibility,
  and runtime boundaries.
- The source/target contract for this lane must stay grounded in:
  - `alembic/versions/202604120001_add_foods_catalog_foundation.py`
  - `scripts/import_restaurant_menu.py`
  - `app/services/restaurant_store.py`
  - `app/routers/restaurants.py`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`

## PR Metadata

- Branch: `feat/pr-b2-restaurant-relational-bridge`
- PR title: `feat(data): bridge restaurant importer into PostgreSQL restaurant catalog`
- Merge method: **merge commit** via `gh pr merge --merge --delete-branch`

## In Scope

- Add one explicit PostgreSQL writer bridge for importer persistence:
  - `app/services/restaurant_postgres_bridge.py`
- Extend `scripts/import_restaurant_menu.py` with explicit PostgreSQL target mode
  while preserving the current normalization and CLI contract
- Write only to:
  - `restaurant_chains`
  - `restaurant_menu_items`
- Keep deterministic importer compatibility for:
  - `chain_name`
  - `item_name`
  - `category`
  - `country`
  - `serving_size_g`
  - `kcal`
  - `protein_g`
  - `fat_g`
  - `carbs_g`
  - `sodium_mg`
  - `source_id`
- Keep `restaurant_menu_items.food_id` nullable in this lane
- Add deterministic tests for idempotent PostgreSQL upsert behavior and
  importer-path compatibility

## Out of Scope

- No runtime read-switch or PostgreSQL cutover
- No public API/OpenAPI changes
- No migration or parity work for:
  - `source_catalog`
  - `user_submissions`
  - `submission_audit`
- No rewrite of `app/services/restaurant_store.py` into a hybrid runtime store
- No `foods.id` linking requirement for imported restaurant rows in this lane
- No Meilisearch/vector/deploy widening

## Primary Implementation Files

This list names the lane-owned implementation surfaces. Full PR inventory may
also include the canonical review artifact plus merge-sync dependency files
pulled from `origin/main`.

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/FOODS_POSTGRES_RESTAURANT_BRIDGE_PR_B2_TASK_PACKET_2026-04-13.md`
- `docs/review/PR_1419_FIXED_MAPPING.md`
- `scripts/import_restaurant_menu.py`
- `app/services/restaurant_postgres_bridge.py`
- `tests/test_import_restaurant_menu_script.py`
- `tests/test_restaurant_postgres_bridge.py`
- `requirements-lock.txt`
- `scripts/ci/emergency_python_wheels.json`
- `.secrets.baseline`

## Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## Lifecycle Notes

- Work from a dedicated lane worktree, not the main checkout
- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Pre-open bootstrap:
  - `python3 scripts/orchestration/task_bootstrap.py --goal "<B2 goal>" --task-class backend --path scripts/import_restaurant_menu.py --path app/services/restaurant_store.py --pr-phase pre_open`
- Open as **draft PR** immediately after packet scope lock and first docs/governance commit
- Immediately after opening the PR:
  - create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`
  - run post-open synthesis with `--pr-phase post_open_review`
- Current-head merge verdict is canonical only through:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`
- Post-merge cleanup for this lane:
  - `git checkout main`
  - `git fetch --prune origin`
  - `git merge --ff-only origin/main`
  - remove only lane-specific worktree, local branch, and gitignored local artifacts

## Validation Plan

- Targeted tests:
  - `pytest -q tests/test_import_restaurant_menu_script.py tests/test_restaurant_postgres_bridge.py`
- Keep existing SQLite restaurant runtime tests green:
  - `pytest -q tests/test_restaurant_store_service.py`
- Full local gates before undraft:
  - `pre-commit run --all-files`
  - `make verify`

## Acceptance Criteria

- Importer normalization aliases remain unchanged
- Existing SQLite/default importer behavior remains safe and deterministic
- PostgreSQL mode upserts `restaurant_chains` deterministically and idempotently
- PostgreSQL mode upserts `restaurant_menu_items` deterministically and idempotently
- Duplicate importer rows do not create duplicate PostgreSQL menu rows
- Missing `source_id` falls back deterministically
- `restaurant_menu_items.food_id` may remain `NULL` without failing the lane
- No runtime read-path or moderation/source-table ownership moves into PostgreSQL
