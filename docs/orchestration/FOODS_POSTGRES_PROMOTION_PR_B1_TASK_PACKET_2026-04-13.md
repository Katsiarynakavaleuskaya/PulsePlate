# Foods PostgreSQL Promotion PR-B1 Task Packet

**Effective date:** 2026-04-13 (`America/New_York`)
**Status:** Historical merged execution packet
**Mode:** coordinator-owned backend/data promotion lane (closed)

## Goal

Land one narrow offline promotion lane that copies the existing SQLite foods
snapshot into PostgreSQL `foods` without widening scope into schema redesign,
runtime cutover, or restaurant importer rewiring.

## Relationship to the Follow-Through Train

- This packet owns only **PR-B1**.
- The execution train is fixed as:
  - `PR-B1`: foods snapshot promotion into PostgreSQL `foods` (merged)
  - `PR-B2`: restaurant relational bridge (merged)
  - `PR-B3`: restaurant PostgreSQL shadow reads + parity checks
  - cutover (deferred): runtime read-switch / PostgreSQL authority change after B3
- The former Postgres deploy-foundation blocker is closed separately via
  repo/runtime evidence reconciliation.
- Post-B3 docs/governance reconciliation now lives in:
  - `docs/orchestration/FOODS_POSTGRES_POST_B3_CLOSEOUT_PACKET_2026-04-17.md`
- The next bounded implementation lane after post-B3 closeout is:
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership`

## Source of Truth

- Repo code remains the final source of truth for vocabulary and compatibility
  boundaries.
- The source/target contract for this lane must stay grounded in:
  - `alembic/versions/202604120001_add_foods_catalog_foundation.py`
  - `app/services/food_store.py`
  - `scripts/build_food_db.py`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-postgres-foundation-followthrough`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p0-self-hosted-postgres-droplet-foundation`

## PR Metadata

- Branch: `feat/pr-b1-foods-offline-etl-postgres`
- PR title: `feat(data): promote offline foods snapshot into PostgreSQL foods`
- Merge method: **merge commit** via `gh pr merge --merge --delete-branch`

## In Scope

- Add one offline promotion script:
  - `scripts/promote_foods_snapshot_to_postgres.py`
- Add deterministic tests for promotion behavior:
  - `tests/test_promote_foods_snapshot_to_postgres.py`
  - optional integration coverage when a PostgreSQL path is available
- Promote only `data/food.sqlite::foods` into PostgreSQL `foods`
- Use deterministic `id`-based upsert and a fixed column allowlist aligned to
  Alembic revision `202604120001`
- Validate and transfer JSON-shaped fields deterministically:
  - `flags`
  - `nutrition_inputs_json`
  - `nutrition_provenance_json`
  - `nutrition_nutrient_confidence_json`
- Emit a promotion summary/report under gitignored `artifacts/`

## Out of Scope

- No new Alembic revision and no schema redesign
- No changes to `core/models.py`
- No runtime cutover or read-switch from SQLite/local-first behavior
- No rewiring of `scripts/import_restaurant_menu.py`
- No changes to `app/services/restaurant_store.py`
- No API/OpenAPI, deploy, Meilisearch, vector, or feature-flag changes
- No direct execution of `PR-B2`

## Touched Files

- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/FOODS_POSTGRES_PROMOTION_PR_B1_TASK_PACKET_2026-04-13.md`
- `scripts/promote_foods_snapshot_to_postgres.py`
- `tests/test_promote_foods_snapshot_to_postgres.py`
- optional: `docs/runbooks/FOODS_POSTGRES_PROMOTION.md`

## Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## Lifecycle Notes

- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Pre-open bootstrap:
  - `python3 scripts/orchestration/task_bootstrap.py --goal "<B1 goal>" --task-class backend --path scripts/promote_foods_snapshot_to_postgres.py --path scripts/build_food_db.py --path app/services/food_store.py --path tests/test_promote_foods_snapshot_to_postgres.py --pr-phase pre_open`
- Open as **draft PR** after local stabilization and packet scope lock.
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
  - `pytest -q tests/test_promote_foods_snapshot_to_postgres.py`
- Full local gates before undraft:
  - `pre-commit run --all-files`
  - `make verify`
- Conditional PostgreSQL proof when target DB is available:
  - run the promotion script against a PostgreSQL path with existing `foods`
  - confirm idempotent rerun behavior
  - confirm deterministic report output in `artifacts/`

## Acceptance Criteria

- The source contract is fixed to `data/food.sqlite::foods`
- The target contract is fixed to PostgreSQL `foods`
- Missing source table fails closed
- Missing target table fails closed
- Promotion uses deterministic `ON CONFLICT(id)` upsert semantics
- JSON-shaped fields are validated and preserved deterministically
- The lane introduces no runtime/importer/schema/OpenAPI drift
- PR `#1409` is historical merged evidence only; runtime authority cutover remains deferred beyond merged B3 until a separate cutover packet exists
