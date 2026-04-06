# Raw food snapshots (W1)

This directory holds **local, git-ignored** Open Food Facts raw snapshot trees.

## Layout

- `off/manifest.json` — append-only manifest written by `core.food_sources.snapshot_manager.SnapshotManager`
- `off/<YYYY-MM-DD>/` — per-run snapshot files (for example `openfoodfacts-products.jsonl.gz`)

## Environment

- `PULSEPLATE_FOOD_RAW_SNAPSHOT_ROOT` — optional absolute path overriding the default
  `<repo>/data/raw/snapshots`.

## Commands

- Sync OFF snapshots: `python scripts/sync_food_snapshots.py` (optional `--root`, `--force`).
- Verify manifest + files before DB build: `python scripts/build_food_db.py --validate-raw-snapshots`.

Programmatic sync: `core.food_apis.snapshot_sync.sync_openfoodfacts_snapshot` or
`DatabaseUpdateManager.sync_openfoodfacts_raw_snapshot`.
