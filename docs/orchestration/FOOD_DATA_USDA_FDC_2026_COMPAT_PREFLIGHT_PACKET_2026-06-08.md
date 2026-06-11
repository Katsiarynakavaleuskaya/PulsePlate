# USDA/FDC 2026 Compatibility Preflight Packet

## Goal

Lock USDA FoodData Central compatibility assumptions to the current public
release contracts without changing runtime authority.

## Release Contracts

- Foundation Foods: `04/2026`
- Branded Foods: `04/2026`
- Full Download of All Data Types: `04/2026`
- FNDDS: `10/2024`, covering `2021-2023`
- SR Legacy: `04/2018`

## Scope

- Emit USDA/FDC manifests from caller-provided local files only.
- Use the existing `source_preflight` manifest contract.
- Refresh USDA Foundation, Branded, and FNDDS manifest fixtures to current
  release assumptions.
- Harden USDA API payload parsing tests for current FDC search/detail shapes.

## Out of Scope

- Live USDA API calls, downloads, `DEMO_KEY`, or network-dependent CI.
- DigitalOcean/Postgres staging or runtime writes.
- SQLite/local runtime authority changes.
- OpenAPI/client contract changes.
- Open Food Facts refresh.
- Semantic-cache, RAG, web, or iOS work.

## Safety Contract

The lane remains file-only:

- `runtime_cutover=false`
- `digitalocean_postgres_load=false`
- `bulk_ingest=false`
- `file_only=true`
- `network_allowed=false`
- `db_writes_allowed=false`

## Deferred / Follow-ups

- Additive `FoodRecord` metadata propagation for `fdc_id`, `brand`, and `gtin`
  with deterministic merge rules.
- Separate staging/Postgres dry-run loader lane.
- Separate governed runtime cutover packet, if staging proves safe.
- Separate Open Food Facts refresh lane.
