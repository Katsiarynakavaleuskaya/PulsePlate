# Food Data PR7: Open Food Facts Manifest Preflight Gate

## Summary

PR7 adds deterministic, file-only Open Food Facts manifest fixtures and proves
that OFF can pass the PR2 dry-run preflight contract while staying governed by
the PR3 source catalog and PR5 onboarding gate.

PR7 does not download Open Food Facts data, compute live checksums, ingest
records, connect to a database, write to DigitalOcean Postgres, or change
runtime food search.

## Coordinator Start

- Coordinator: `agent-coordinator`
- Branch: `codex/food-data-off-manifest-preflight-pr7`
- Required role order:
  `agent-coordinator -> data-scientist-agent -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Scope

- Add deterministic Open Food Facts manifest fixtures for:
  - full-dump current/incoming snapshots;
  - delta/export-style incoming candidate.
- Keep `source=open_food_facts`, `source_classification=current`, and source
  URL `https://world.openfoodfacts.org/data`.
- Validate fixture manifests through the existing PR2 manifest parser
  (`core/food_sources/source_preflight.py:276`) and dry-run diff contract
  (`core/food_sources/source_preflight.py:316`).
- Prove OFF manifests are allowed by:
  - PR3 catalog identity/classification
    (`core/food_sources/source_preflight.py:432`);
  - PR3 active update, manifest, and preflight flags
    (`core/food_sources/source_preflight.py:466`);
  - PR5 onboarding `eligible_preflight`, `manifest_preflight_only`, and ODbL
    policy ref (`core/food_sources/source_onboarding.py:352`);
  - PR5 safety flags: `runtime_cutover=false`,
    `digitalocean_postgres_load=false`, `bulk_ingest=false`,
    `network_allowed=false`, and `db_writes_allowed=false`
    (`core/food_sources/source_onboarding.py:523`).

## Out Of Scope

- Open Food Facts downloads.
- Live OFF row-count/checksum discovery.
- Snapshot promotion.
- Bulk ingest.
- PostgreSQL staging or DigitalOcean production load.
- Runtime authority or food-search cutover.
- JPTN, MenuStat replacement, restaurant-menu, recipe/corpus, or regional
  source onboarding.

## Fixture Policy

The OFF checksums, byte sizes, row counts, fixture dates, and artifact paths in
PR7 are synthetic deterministic metadata. They exist only to exercise manifest
shape, source identity, schema/primary-key deltas, ODbL policy continuity, and
collision policy validation.

OFF uses `code` as the primary key and dedupe field. Collision resolution is
`quarantine` because barcode/product records can be corrected, reused, edited,
or malformed across provider changes. The delta/export-style fixture is a
candidate preflight shape only and does not approve incremental ingestion.

## Validation

Required start gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR7 Open Food Facts manifest preflight gate" --task-class "Orchestration" --pr-phase pre_open
```

Targeted PR7 validation:

```bash
python3 -m pytest tests/test_food_source_preflight.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py -q
python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_off_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_off_manifest.json --dry-run --json --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Do not run local `make verify` for this lane; GitHub current-head CI remains the
machine-heavy signal.

## Security Notes

- PR7 is file-only.
- No network, database, credential, DigitalOcean, production import, or runtime
  cutover path is allowed.
- OFF must keep `provider_policy_ref=docs/legal/ODbL_COMPLIANCE.md`,
  `redistribution_decision=odbl_obligations_required`, and
  `attribution_required=true` (`docs/legal/ODbL_COMPLIANCE.md:21`,
  `core/food_sources/source_onboarding.py:352`).
- The validator must fail closed when ODbL policy, catalog identity,
  onboarding status, ingestion path, or safety flags drift
  (`core/food_sources/source_preflight.py:421`,
  `core/food_sources/source_preflight.py:495`).

## Marketing & GTM

No product, API, UX, launch, pricing, or public dataset claim changes in PR7.
The later marketable claim remains a governed multi-source food database with
provenance, only after source-specific ingest and runtime authority lanes are
approved.

## Decision Log

- PR6 USDA manifest preflight landed in PR `#1563`.
- PR7 adds the Open Food Facts source-specific manifest preflight gate.
- Fixture metadata is intentionally synthetic and must be replaced by verified
  source metadata in a later OFF ingest/staging PR.
