# ADR: Food Data Source Update Preflight Before Bulk Ingest

**Effective date:** 2026-04-24 (`America/New_York`)
**Status:** Accepted for PR1 planning

## Context

- The food PostgreSQL foundation train through PR `#1468` has already merged,
  but runtime authority still remains SQLite/local-first until a separate
  governed cutover packet retires the existing seam.
- USDA FoodData Central, Open Food Facts, JPTN Food Facts, restaurant-menu
  coverage, and recipe/corpus coverage now need a sharper update contract before
  new bulk data is imported.
- MenuStat can no longer be treated as an actively updating restaurant source;
  its public annual dataset line is legacy/static for this program.

## Decision

The next food-data lane is a source-update preflight, not an ingest or runtime
cutover lane.

This preflight must define source versions, schema diffs, dedupe/collision
rules, license/attribution status, storage target, and rollback policy before
any new data is loaded into PostgreSQL or promoted into runtime reads.

## Source Policy

- USDA Foundation/Branded/FNDDS and Open Food Facts remain candidate Tier 1
  food sources, subject to release-version checks, checksums, and field-diff
  validation.
- MenuStat remains usable only as historical baseline data and format
  compatibility for `MenuStat-style` imports.
- Restaurant-menu updates require a replacement-source decision before ingest.
  Nutritionix-style commercial data, direct chain snapshots, and other APIs are
  candidates only after license, cache, display, and redistribution review.
- Recipe templates that are already repo-owned may continue as product logic
  inputs. External recipe corpora are treated as new food/menu sources and must
  pass the same source, license, cache, attribution, and rollback review.
- Regional catalogs remain candidate sources only after locale-specific
  normalization and legal review.
- JPTN Food Facts is blocked until the exact provider and legal/source contract
  are identified.

## Consequences

- No DigitalOcean PostgreSQL production load occurs in PR1.
- No public API or runtime behavior changes occur in PR1.
- Later implementation PRs can add preflight tooling or importer changes only
  after this contract is reflected in the backlog and packet.

## References

- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-usda-foundation-foods-preflight`
- `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md`
- `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`
