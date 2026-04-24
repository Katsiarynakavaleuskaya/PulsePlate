# Food Data Source Update Preflight PR1 Packet

**Effective date:** 2026-04-24 (`America/New_York`)
**Status:** Active execution packet
**Mode:** coordinator-owned docs/tooling-contract lane

## Goal

Define the first guarded food-data update lane before any refreshed USDA, Open
Food Facts, JPTN Food Facts, or restaurant-menu data is imported into local
snapshots, PostgreSQL staging, or production infrastructure.

## Relationship to the Food Data Line

- PR `#1462` and PR `#1468` are already merged; downgrade ownership is no
  longer the next active lane.
- This packet owns the source-update preflight contract for
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-usda-foundation-foods-preflight`.
- This lane keeps SQLite/local snapshots as runtime authority and does not
  connect DigitalOcean PostgreSQL, bulk-load production data, or switch runtime
  reads.
- MenuStat is treated as a legacy/static baseline. The restaurant-menu update
  path must pick and approve a replacement source before any new restaurant
  data import is shipped.

## Source Version Manifest

PR1 must classify each source before ingest:

- **USDA FoodData Central Foundation Foods:** official download page currently
  lists December 2025 Foundation Foods. Verify release files, checksum, schema,
  record IDs, and nutrient-field diff before ingest.
- **USDA FoodData Central Branded:** official update log currently shows
  FoodData Central 14.4 on April 23, 2026 for branded updates. Decide whether
  branded volume is in scope or deferred behind a separate performance gate.
- **USDA FNDDS / survey foods:** official downloads currently include FNDDS
  2021-2023. Treat as a separate survey/meal-consumption source, not as a
  substitute for branded, restaurant, or recipe data.
- **Open Food Facts:** keep as ODbL-governed source. The official dump page
  must be manually verified because automated fetch can be blocked. Confirm
  dump format, checksum, attribution, derivative-db duties, and delta strategy.
- **MenuStat:** legacy/static only. Public annual datasets currently stop at
  2022, so it cannot be the update source for fresh restaurant menus.
- **Restaurant-menu replacement:** evaluate candidates separately: commercial
  APIs, direct chain snapshots, partner-provided menus, or another reviewed
  dataset. Candidate examples include Nutritionix-style providers, OpenMenu-style
  menu APIs, and restaurant nutrition APIs such as Macros.Menu; none are
  approved until cache, display, redistribution, attribution, and rollback rules
  are documented.
- **Recipe templates and synthesized recipes:** repo-owned recipe templates are
  internal product data, not a nutrition-source replacement. External recipe
  corpus or recipe-analysis onboarding, including Edamam/Spoonacular-style
  providers, needs the same source/license/cache gate as food data.
- **Regional catalogs:** EU/RF/EAEU/local-market catalogs remain candidates
  only after source-specific legal and locale normalization review.
- **JPTN Food Facts:** unresolved source identity in this repo. Identify exact
  provider, license, fields, locale coverage, and redistribution/cache rights
  before any ingest.

## Role Order

1. `agent-coordinator`
2. `data-scientist-agent`
3. `backend-engineer`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`
7. `dev-operator`

Mandatory post-open review lane remains: `qa-engineer-agent -> bug-hunter`.

## In Scope

- Add the PR1 source-update preflight packet and architecture decision record.
- Update the backlog ledger so the next food-data PR is this preflight lane.
- Update the food database platform strategy so MenuStat is no longer treated
  as an actively updating source.
- Define deterministic preflight requirements:
  - source version manifest
  - schema/field diff
  - record-count and primary-key delta
  - dedupe/collision checks
  - license/attribution review
  - storage and rollback decision

## Out of Scope

- No DigitalOcean PostgreSQL connection or credential handling.
- No production, staging, or local bulk import of USDA, Open Food Facts,
  MenuStat, JPTN, or replacement restaurant data.
- No runtime authority cutover from SQLite/local-first reads to PostgreSQL.
- No public API, OpenAPI, frontend, iOS, Meilisearch, pgvector, or restaurant
  endpoint behavior change.
- No provider contract acceptance for Nutritionix-style commercial data.

## Storage Decision Gate

PR1 must decide storage before implementation:

- **Local immutable snapshots:** default for raw source archives and manifests;
  gitignored data stays outside PR diffs.
- **PostgreSQL staging:** allowed only in a later PR after checksum, rollback,
  and non-production DSN policy are documented.
- **DigitalOcean production PostgreSQL:** blocked until source preflight,
  staging proof, rollback, and runtime cutover packet are complete.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- Docs-only local check for packet/ledger links.
- `pre-commit run --all-files` before push.
- `make verify` remains the merge-ready hard gate; do not claim readiness until
  it passes or the repo owner explicitly chooses GitHub current-head checks as
  the heavy signal for this docs-only lane.

## Acceptance Criteria

- Backlog points to this source-update preflight as the next food-data PR.
- MenuStat replacement is explicit and cannot be bypassed by treating MenuStat
  as a live annual update source.
- USDA, Open Food Facts, MenuStat legacy, restaurant-menu replacement,
  recipe/corpus, regional catalog, and JPTN sources all have source-specific
  pre-ingest decisions.
- Runtime authority and DigitalOcean production load remain explicitly blocked.

## Official Source Checks

- USDA FoodData Central downloads:
  `https://fdc.nal.usda.gov/download-datasets`
- USDA FoodData Central update log:
  `https://fdc.nal.usda.gov/log/`
- Open Food Facts data dump page:
  `https://world.openfoodfacts.org/data`
- MenuStat public data page:
  `https://www.menustat.org/data.html`
- OpenMenu API:
  `https://openmenu.com/api/`
- Macros.Menu API:
  `https://www.macros.menu/api`
- Edamam recipe licensing and nutrition APIs:
  `https://developer.edamam.com/recipe-database-licensing`
