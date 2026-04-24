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

Evidence anchors:

- PR `#1468` downgrade-ownership closeout:
  `docs/review/PR_1468_FIXED_MAPPING.md:26`
- SQLite/local-first runtime cutover seam:
  `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md:7`
- MenuStat legacy/static classification:
  `docs/architecture/FOOD_DATABASE_PLATFORM_STRATEGY_v1.md:63`
- USDA, Open Food Facts, MenuStat, and JPTN source-status contract:
  `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md:30`
  and
  `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md:56`

## Decision

The next food-data lane is a source-update preflight, not an ingest or runtime
cutover lane.

The canonical PR1 packet section `Canonical Preflight Criteria` defines the
source-version manifest, schema diff, dedupe/collision, license/attribution,
storage target, and rollback requirements that must pass before any new data is
loaded into PostgreSQL or promoted into runtime reads.

## Exit Criteria

This ADR can be retired only when a later governed implementation lane proves:

1. source versions are recorded and signed off by the data owner;
2. schema diffs are reviewed and approved;
3. dedupe/collision rules are documented and validated;
4. license, attribution, cache, display, and redistribution status is confirmed;
5. storage target, retention, and rollback policy are configured;
6. staging smoke tests prove rollback and data verification;
7. monitoring/alerting expectations are documented when staging or runtime data
   paths are touched;
8. the owning Backlog Ledger item is marked done with explicit DoD evidence and
   no open blockers;
9. retirement date and release-manager sign-off are recorded in the follow-up
   ADR or closeout artifact.

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
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md#canonical-preflight-criteria`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-food-data-source-update-preflight`
- `docs/architecture/ADR_FOODS_POSTGRES_RUNTIME_CUTOVER_SEAM_2026-04-17.md`
- `docs/legal/EXTERNAL_FOOD_SOURCE_OPERATING_POLICY.md`
