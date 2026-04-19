# Foods Foundation Downgrade Ownership Task Packet

**Effective date:** 2026-04-18 (`America/New_York`)
**Status:** Active execution packet
**Mode:** coordinator-owned backend/data migration follow-up lane

## Goal

Land one narrow follow-up lane that makes revision `202604120001` downgrade
behavior ownership-aware so rollback removes only schema objects created by the
revision and preserves pre-existing compatible `foods` catalog objects.

## Relationship to the Food Epic Data Train

- This packet owns only the downgrade-ownership follow-up lane for backlog item
  `ledger-p1-foods-foundation-downgrade-ownership`.
- The prior foundation lane (`PR-A`) already landed the additive schema and
  upgrade-time existence guards.
- This lane does not reopen runtime cutover, importer rewiring, or restaurant
  shadow-read work.
- Immediately after this lane closes, coordinator opens the next planning lane
  for the following food epic data PR from the current backlog order.

## Source of Truth

- Repo code remains the final source of truth for migration semantics and
  rollback safety.
- This lane must stay grounded in:
  - `alembic/versions/202604120001_add_foods_catalog_foundation.py`
  - `tests/test_foods_catalog_foundation_migration.py`
  - `docs/review/PR_1468_FIXED_MAPPING.md`
  - `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-foods-foundation-downgrade-ownership`
  - `docs/orchestration/FOODS_CATALOG_FOUNDATION_PR_A_TASK_PACKET_2026-04-12.md`

## PR Metadata

- PR number: `1468`
- PR URL: `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1468`
- Branch: `codex/foods-foundation-downgrade-ownership`
- PR title: `fix(data): make foods foundation downgrade ownership-aware`
- Merge method: **merge commit** via `gh pr merge --merge --delete-branch`

## In Scope

- Edit revision `202604120001` in place; do not add a new Alembic revision
- Add explicit revision-owned object tracking for objects created by
  `202604120001`
- Make downgrade delete only revision-owned tables and indexes
- Preserve compatible pre-existing `foods` and companion indexes on downgrade
- Keep downgrade ordering dependency-safe across child/parent tables
- Add deterministic migration-focused tests for:
  - clean-room upgrade/downgrade ownership
  - pre-existing `foods` table preservation
  - pre-existing index preservation
  - owned index removal when created by the revision
- Add packet/governance artifacts for this PR lane

## Out of Scope

- No runtime cutover from SQLite/local-first authority
- No importer rewiring
- No OpenAPI/public API changes
- No mutation or rename of `food_items`
- No Meilisearch/vector/deploy widening
- No retroactive repair path for databases that already applied the old
  `202604120001` without ownership tracking

## Primary Implementation Files

- `docs/orchestration/FOODS_FOUNDATION_DOWNGRADE_OWNERSHIP_TASK_PACKET_2026-04-18.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `alembic/versions/202604120001_add_foods_catalog_foundation.py`
- `tests/test_foods_catalog_foundation_migration.py`
- `docs/review/PR_<N>_FIXED_MAPPING.md`

## Role Order

1. `agent-coordinator`
2. `backend-engineer`
3. `security-auditor`
4. `qa-engineer-agent`
5. `bug-hunter`
6. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## Skills / Workflow Notes

- Start the lane with `pulseplate-workflow` discipline
- Use migration/test scoped `AGENTS.md` rules as the implementation SoT
- Use PR-governance wrappers for current-head truth and mapping discipline
- Use cheap local bundles for iteration; do not widen into unrelated full-suite
  exploration on this machine

## Lifecycle Notes

- Work only from this dedicated lane branch/worktree; do not mutate the dirty
  root checkout or colleague-owned files
- Before edits:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
- Pre-open bootstrap:
  - `python3 scripts/orchestration/task_bootstrap.py --goal "Make revision 202604120001 downgrade ownership-aware without dropping pre-existing foods catalog objects" --task-class backend --path alembic/versions/202604120001_add_foods_catalog_foundation.py --path tests/test_foods_catalog_foundation_migration.py --pr-phase pre_open`
- Open as **draft PR** after packet scope lock and first local stabilization
- Immediately after opening the PR:
  - create canonical artifact `docs/review/PR_<N>_FIXED_MAPPING.md`
  - run post-open synthesis with `--pr-phase post_open_review`
- Current-head merge verdict remains canonical only through:
  - `python3 scripts/orchestration/check_merge_ready.py --pr-number <N> --repo Katsiarynakavaleuskaya/PulsePlate --require-auth`

## Validation Plan

- Mandatory every iteration:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `pytest -q tests/test_foods_catalog_foundation_migration.py`
  - `pre-commit run --all-files`
- Optional cheap reinforcement when needed:
  - `make validate-min`
  - `make validate-changed`
- Canonical repo policy still treats `make verify` as the hard merge-ready gate,
  but this lane does not wait for green `main` and does not promise full local
  `make verify` on this machine before the operational merge decision is handed
  to the user.

## Acceptance Criteria

- Revision `202604120001` tracks which objects it created during upgrade
- Downgrade no longer blind-drops `foods` or companion indexes
- Clean-room downgrade still fully removes revision-owned objects
- Pre-existing compatible `foods` table survives downgrade
- Pre-existing companion indexes survive downgrade
- Revision-owned indexes created against a pre-existing `foods` table are
  removed on downgrade
- No runtime/API contract drift is introduced
