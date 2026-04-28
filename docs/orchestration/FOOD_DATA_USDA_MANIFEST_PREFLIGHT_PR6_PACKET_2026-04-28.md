# Food Data PR6: USDA Source Manifest Preflight Gate

## Summary

PR6 adds deterministic, file-only USDA manifest fixtures for FoodData Central
Foundation, Branded, and FNDDS sources. It proves that USDA manifests can pass
the PR2 dry-run preflight shape while staying governed by the PR3 source catalog
and PR5 onboarding gate.

PR6 does not download USDA data, compute live checksums, ingest records, connect
to a database, write to DigitalOcean Postgres, or change runtime food search.

## Coordinator Start

- Coordinator: `agent-coordinator`
- Branch: `codex/food-data-usda-manifest-preflight-pr6`
- Required role order:
  `agent-coordinator -> data-scientist-agent -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Scope

- Add deterministic USDA manifest fixtures for:
  - `usda_foundation`
  - `usda_branded`
  - `usda_fndds`
- Keep `source_classification=current` and source URL
  `https://fdc.nal.usda.gov/download-datasets`.
- Validate fixture manifests through the existing PR2 manifest parser and dry-run
  diff contract.
- Add a file-only source contract helper proving the manifest source is allowed
  by:
  - PR3 catalog identity/classification;
  - PR3 active update, manifest, and preflight flags;
  - PR5 onboarding `eligible_preflight` and `manifest_preflight_only` policy;
  - PR5 safety flags: `runtime_cutover=false`,
    `digitalocean_postgres_load=false`, `bulk_ingest=false`,
    `network_allowed=false`, and `db_writes_allowed=false`.

## Out Of Scope

- USDA source downloads.
- Live USDA row-count/checksum discovery.
- Snapshot promotion.
- Bulk ingest.
- PostgreSQL staging or DigitalOcean production load.
- Runtime authority or food-search cutover.
- OFF, JPTN, MenuStat replacement, restaurant-menu, recipe/corpus, or regional
  source onboarding.

## Fixture Policy

The USDA checksums, byte sizes, row counts, and artifact paths in PR6 fixtures
are synthetic deterministic metadata. They exist only to exercise the manifest
shape, diff output, schema/primary-key deltas, and collision policy validation.

USDA Foundation and FNDDS use `fdc_id` as primary key with reject-on-collision
policy. USDA Branded uses `fdc_id` as primary key, `gtin_upc` as dedupe field,
and quarantine-on-collision policy because branded package identifiers can
collide or be reused across provider changes.

## Validation

Required start gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR6 USDA manifest preflight gate" --task-class "Orchestration" --pr-phase pre_open
```

Targeted PR6 validation:

```bash
python3 -m pytest tests/test_food_source_preflight.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py -q
python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_usda_foundation_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_usda_foundation_manifest.json --dry-run --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Do not run local `make verify` for this lane; GitHub current-head CI remains the
machine-heavy signal.

## Security Notes

- PR6 is file-only.
- No network, database, credential, DigitalOcean, or production import path is
  allowed.
- The validator must fail closed when catalog identity, classification,
  onboarding status, ingestion path, or safety flags drift.

## Marketing & GTM

No product, API, UX, launch, pricing, or public dataset claim changes in PR6.
The later marketable claim remains: governed multi-source food data with
provenance, only after source-specific ingest and runtime authority lanes are
approved.

## Decision Log

- PR5 source-onboarding gate is the landed baseline in PR `#1559`.
- PR6 opens the first source-specific manifest preflight lane for USDA only.
- Fixture metadata is intentionally synthetic and must be replaced by verified
  source metadata in a later USDA ingest/staging PR.
