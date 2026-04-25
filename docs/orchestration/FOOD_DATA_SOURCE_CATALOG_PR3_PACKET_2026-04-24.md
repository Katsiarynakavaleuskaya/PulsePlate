# Food Data Source Catalog PR3 Packet

**Effective date:** 2026-04-24 (`America/New_York`)
**Status:** Active PR3 source catalog lane
**Mode:** coordinator-owned deterministic catalog lane

## Goal

Turn the merged PR1 planning baseline and merged PR2 preflight tooling skeleton
into a deterministic source catalog and replacement-source shortlist before any
USDA, Open Food Facts, MenuStat replacement, JPTN, recipe, regional,
PostgreSQL staging, or runtime authority work begins.

## Relationship to PR1 and PR2

- Baseline PR1: PR `#1513` merged the source-update preflight packet and ADR.
- Baseline PR2: PR `#1517` merged strict file-only manifest validation and
  dry-run diff tooling.
- PR3 does not ingest data. It classifies source candidates and keeps the
  manifest/diff tooling contract ready for later source-specific onboarding.
- MenuStat stays `legacy_static`; restaurant/menu replacement candidates are
  cataloged only, not approved for ingest.

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

- Add a deterministic catalog contract for source candidates and legacy sources.
- Preserve PR2 `source_classification` values:
  `current`, `legacy_static`, `commercial_contract`, `unresolved`.
- Classify USDA Foundation, USDA Branded, USDA FNDDS, Open Food Facts,
  MenuStat legacy/static, commercial restaurant/menu candidates, recipe/corpus
  candidates, regional catalogs, and unresolved `JPTN Food Facts`.
- Encode MenuStat as non-updating and require at least one replacement
  candidate before future restaurant/menu ingest.
- Validate catalog safety flags:
  `runtime_cutover=false`, `digitalocean_postgres_load=false`,
  `bulk_ingest=false`.

## Out of Scope

- No DigitalOcean PostgreSQL connection string, credential handling, or writes.
- No production, staging, or local bulk import.
- No network downloads from USDA, Open Food Facts, MenuStat, JPTN, recipes,
  regional catalogs, or commercial restaurant/menu providers.
- No runtime source switch, public API change, OpenAPI change, frontend/iOS
  change, Meilisearch update, pgvector update, or managed PostgreSQL authority.
- No final legal approval of commercial APIs or direct chain nutrition pages.

## Catalog Contract

Canonical PR3 catalog:

- `docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json`

Validator:

- `core/food_sources/source_catalog.py`

Required source entry fields:

- `source`
- `source_classification`
- `source_family`
- `status`
- `source_url`
- `license_review`
- `active_update_source`
- `manifest_required`
- `preflight_required`
- `replacement_required`
- `replacement_for`
- `notes`

## Source Decisions

- USDA Foundation, USDA Branded, and USDA FNDDS remain `current` candidates,
  each requiring source-version, checksum, row count, schema, and primary-key
  review before ingest.
- Open Food Facts remains a `current` candidate with explicit ODbL review.
- MenuStat remains `legacy_static`; it is not an active update source.
- Nutritionix, FatSecret Platform, Spoonacular, and Edamam are
  `commercial_contract` candidates. They require contract, cache, display,
  attribution, redistribution, and cost review before use.
- Direct chain public nutrition pages are `unresolved` until per-chain legal
  and anti-scraping review is complete.
- Regional catalogs are `unresolved` until locale-specific legal, language,
  unit, and nutrient normalization review is complete.
- `JPTN Food Facts` remains `unresolved` until provider identity, license,
  schema, and retrieval contract are clarified.

## Lineage Validation Policy

- Replacement edges are now validated as a directed acyclic graph (DAG):
  `replacement_for` may point only to existing source names, never to itself, and
  may not form cycles.
- If `replacement_for` is present:
  - `replacement_required` must be `false`.
  - `active_update_source` must match the source family policy defined in this
    catalog (`current` and `commercial_contract` are active by default; legacy
    and unresolved sources remain non-active).
- `legacy_static` entries may not declare `replacement_for` unless they are
  explicit baseline placeholders in their own follow-up lanes.
- `unresolved` and `legacy_static` entries are fail-closed for runtime cutover
  and ingest readiness contracts.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 -m pytest tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q`
- `python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_off_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_off_manifest.json --dry-run --json`
- `pre-commit run --all-files` before push

`make verify` is intentionally not part of the local PR3 loop under the
operator-approved machine-heavy exception; GitHub current-head CI remains the
heavy signal for this lane.

## Acceptance Criteria

- Catalog validation fails closed when safety flags imply runtime cutover,
  DigitalOcean PostgreSQL load, or bulk ingest.
- MenuStat cannot be marked as an active update source.
- MenuStat has explicit replacement candidates before any future restaurant
  ingest lane.
- `unresolved` sources are blocked instead of treated as ingest-ready.
- Commercial candidates require commercial-contract review status.
- PR3 updates the ledger and current packet pointer so later food-data lanes do
  not treat PR2 as still active.
