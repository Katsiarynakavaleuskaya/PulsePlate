# Food Data Source Preflight Tooling PR2 Packet

**Effective date:** 2026-04-24 (`America/New_York`)
**Status:** Merged PR2 tooling baseline (`#1517`)
**Mode:** coordinator-owned deterministic tooling lane

## Goal

Turn the merged PR1 source-update criteria into a deterministic, file-only
preflight tooling skeleton before any USDA, Open Food Facts, MenuStat
replacement, JPTN, recipe, regional, PostgreSQL staging, or runtime authority
work begins.

## Relationship to PR1

- Baseline: PR `#1513` merged the PR1 planning packet and ADR.
- Canonical criteria remain in
  [`FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md`](./FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_PR1_PACKET_2026-04-24.md).
- PR2 implemented the first strict manifest/diff tooling contract only.
- PR3 extends the line with a deterministic source catalog and replacement
  shortlist without widening into ingest.
- MenuStat stays `legacy_static`; replacement restaurant/menu sources remain a
  later classification and approval decision.

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

- Strict source manifest validation with top-level `source_classification`.
- Allowed classifications: `current`, `legacy_static`,
  `commercial_contract`, `unresolved`.
- Deterministic dry-run diff report for source version, checksum, row count,
  size, schema-field deltas, and primary-key deltas.
- Fixture/schema checks for current OFF-style data, legacy MenuStat, invalid
  classification, and schema/PK drift.
- Repo-local CLI contract:
  `python3 scripts/food_source_preflight.py --current-manifest <path> --incoming-manifest <path> --dry-run --json`.

## Out of Scope

- No DigitalOcean PostgreSQL connection string, credential handling, or writes.
- No production, staging, or local bulk import.
- No network downloads from USDA, Open Food Facts, MenuStat, JPTN, recipes, or
  commercial restaurant providers.
- No runtime source switch, public API change, OpenAPI change, frontend/iOS
  change, Meilisearch update, pgvector update, or managed PostgreSQL authority.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- Targeted pytest for `tests/test_food_source_preflight.py`
- CLI smoke with valid and invalid fixtures
- `pre-commit run --all-files` before push

`make verify` is intentionally not part of the local PR2 loop; GitHub current
head CI is the heavy signal for this lane.

## Acceptance Criteria

- Invalid or missing `source_classification` fails closed in PR2 tooling.
- Valid `legacy_static` MenuStat manifests are accepted but do not imply fresh
  restaurant-menu ingest.
- Dry-run output always includes `runtime_cutover: false`.
- Dry-run command does not require network, database, DigitalOcean credentials,
  or source archive existence.
- Ledger and current packet pointer link PR2 back to the merged PR1 criteria.
