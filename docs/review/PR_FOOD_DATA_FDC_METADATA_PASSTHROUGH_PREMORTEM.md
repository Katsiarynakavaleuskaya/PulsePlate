# Food Data FDC Metadata Passthrough Premortem

Mode: `pr-premortem`
Skill: `pulseplate-premortem-risk-review`
Task packet: `artifacts/orchestration/task_packets/897c356ac39e.json`
Experiment Runner artifact: `artifacts/orchestration/experiments/results/food-data-fdc-record-metadata-passthrough-oracle.json`
Branch: `codex/food-data-fdc-record-metadata-passthrough`

## Summary

It is six months from now. This metadata passthrough slice failed because a
small compatibility update either broke legacy `FoodRecord` construction,
damaged barcode identifiers, or was misread as approval for a broader food-data
runtime/cutover change.

## Findings And Closure

### PM-FDC-META-001: FoodRecord Constructors Break

Failure story: Adding metadata fields to `FoodRecord` changes positional
constructor behavior or requires every existing call site to pass new values.
Older tests and import paths then fail even though the feature is meant to be
additive.

Disposition: FIXED

Evidence:
- `core/food_sources/base.py` adds `brand`, `gtin`, and `fdc_id` as optional
  fields with `None` defaults at the end of the dataclass.
- `tests/test_food_sources_simple.py` asserts existing `FoodRecord`
  construction still yields `None` metadata defaults.

### PM-FDC-META-002: GTIN Cleanup Destroys Barcode Identity

Failure story: USDA or OFF rows preserve non-digit barcode separators, or the
cleanup path casts values through numbers and drops leading zeroes. Stored
barcodes then stop matching existing lookup surfaces.

Disposition: FIXED

Evidence:
- `core/food_sources/base.py` centralizes optional metadata and GTIN cleanup.
- `tests/test_food_sources_simple.py` covers USDA/OFF blank handling and digit
  cleanup while preserving leading zeroes from string inputs.

### PM-FDC-META-003: Merge Drops Representative Metadata

Failure story: Source normalization keeps metadata, but the name-based merge
output omits it, so downstream storage still cannot populate the existing
barcode columns.

Disposition: FIXED

Evidence:
- `core/food_merge.py` carries the first non-empty `brand`, `gtin`, and
  `fdc_id` into merged records without changing merge keys, provenance, or
  source-priority semantics.
- `tests/test_food_merge.py` proves merged records preserve metadata from
  USDA/OFF inputs.

### PM-FDC-META-004: Barcode Storage Surface Still Loses Metadata

Failure story: The storage lookup API already exposes `brand`, `gtin`, and
`fdc_id`, but a temp SQLite path fails to round-trip the new normalized values.

Disposition: FIXED

Evidence:
- `tests/test_food_store_service.py` adds a temp-SQLite barcode lookup case for
  stored `brand`, `gtin`, and `fdc_id` through `get_food_by_barcode()`.

### PM-FDC-META-005: Compatibility Slice Becomes Runtime Expansion

Failure story: Reviewers see USDA/OFF metadata fields and infer approval for
live provider calls, a Postgres cutover, new source activation, or OpenAPI/client
regeneration.

Disposition: NOT-A-BUG

Evidence:
- The branch changes only food source normalization, merge behavior, tests, and
  this review artifact.
- No Alembic/Postgres migration, OpenAPI schema, runtime route expansion,
  provider client, or ingestion scheduler files are changed.

## Decision

`proceed with changes`. The identified implementation risks are closed by the
code/tests in this branch, and the scope-creep risk is closed by the unchanged
runtime/cutover surfaces.

## Pre-Open Checklist

- Focused USDA/OFF source, merge, and store-service pytest passes.
- `make validate-changed` passes against the committed branch diff.
- `pre-commit run --all-files` passes before push.
- Experiment Runner oracle-only evidence is accepted with no mutations.
- PR body keeps Postgres cutover, new data sources, runtime food-pipeline
  expansion, and live USDA/OFF calls out of scope.
