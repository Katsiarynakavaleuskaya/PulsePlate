# Food Data Source Onboarding Gate PR5 Packet

**Effective date:** 2026-04-28 (`America/New_York`)
**Status:** Active PR5 source-onboarding gate lane
**Mode:** coordinator-owned deterministic preflight governance lane

## Goal

Define and enforce a file-only source-onboarding gate before any source-specific
USDA, Open Food Facts, JPTN, restaurant/menu, recipe/corpus, regional catalog,
PostgreSQL staging, or runtime authority work begins.

## Relationship to prior PRs

- PR1 (`#1513`) defined source-update preflight criteria.
- PR2 (`#1517`) implemented strict file-only manifest validation and diff scaffolding.
- PR4 (`#1531`) added deterministic dedupe/mapping collision policy.
- PR3 lineage follow-up (`#1532`) hardened source catalog replacement validation.
- PR5 adds the legal/cache/display/redistribution onboarding gate that must pass
  before any later source-specific manifest onboarding or ingest lane.

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

- Add a canonical PR5 onboarding snapshot aligned with the PR3 source catalog.
- Add deterministic file-only validation for onboarding decisions.
- Require exact catalog coverage: no missing, duplicate, or unknown source entries.
- Preserve hard safety flags:
  `runtime_cutover=false`, `digitalocean_postgres_load=false`,
  `bulk_ingest=false`, `file_only=true`, `network_allowed=false`,
  and `db_writes_allowed=false`.
- Enforce source-specific legal/cache/display/redistribution gates for:
  USDA-style current sources, Open Food Facts ODbL, MenuStat legacy/static,
  commercial restaurant/recipe APIs, and unresolved JPTN/regional/chain sources.

## Out of Scope

- No source downloads.
- No staging, ingest, or database writes.
- No runtime source switch.
- No DigitalOcean PostgreSQL credential handling.
- No app API, OpenAPI, frontend, iOS, Meilisearch, or pgvector changes.
- No paywall, pricing, subscription, ASO, or GTM copy changes.

## Validation Plan

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR5 source onboarding gate" --task-class "Orchestration" --pr-phase pre_open`
- `python3 -m pytest tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q`
- `pytest -q tests/test_repo_policy_guards.py`
- `python3 scripts/food_source_onboarding.py --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --json`
- `pre-commit run --all-files` before push

`make verify` is intentionally not part of the local PR5 loop per the
operator-approved machine-heavy exception; GitHub current-head CI remains the
heavy merge signal for this lane.

## Acceptance Criteria

- Onboarding snapshot validates against the current source catalog.
- Every catalog source has exactly one onboarding entry.
- OFF cannot pass without ODbL policy linkage and attribution/redistribution gates.
- Commercial sources cannot pass without contract-blocked cache, display, and
  redistribution decisions.
- Unresolved sources remain blocked.
- MenuStat remains `legacy_static`, inactive, and replacement-required.
- Dry-run report is deterministic JSON and always declares no runtime cutover,
  no DigitalOcean load, no bulk ingest, no network, and no DB writes.
