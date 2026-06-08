# USDA/FDC 2026 Compatibility Premortem

Mode: `pr-premortem`
Task packet: `artifacts/orchestration/task_packets/cd01c7fc4ed5.json`
Branch: `codex/food-data-usda-fdc-2026-compat-preflight`

## Summary

It is six months from now. The USDA/FDC compatibility PR failed because it
looked like a harmless fixture/parser refresh but accidentally weakened data
validation or implied source/runtime authority that the repo had not approved.

## Findings And Closure

### PM-USDA-001: Parallel Manifest Contract Drift

Failure story: The new USDA/FDC emitter creates a second manifest shape, so later
food-data lanes validate emitter output differently from `source_preflight`.
Diff reports continue to pass, but future staging work reads a subtly different
contract.

Disposition: FIXED

Evidence:
- `core/food_sources/usda_fdc_manifest.py` routes generated payloads through
  `parse_source_manifest(...)`.
- `tests/test_usda_fdc_manifest_emitter.py` validates emitter output against
  the existing catalog/onboarding source contract.

### PM-USDA-002: Malformed Nutrient Values Become Silent Partial Truth

Failure story: Parser hardening accepts malformed mapped nutrient amounts as a
partial successful parse. A branded payload with bad iron/protein/fat values
looks valid enough to flow downstream, hiding source quality problems.

Disposition: FIXED

Evidence:
- `core/food_apis/usda_client.py` now fails closed for malformed mapped
  nutrient values while preserving valid zero values.
- `tests/test_food_apis.py` covers both current branded payload parsing and
  rejection of malformed mapped nutrient values.

### PM-USDA-003: Compatibility PR Implies Runtime Or Staging Approval

Failure story: Reviewers see current USDA release versions and assume the PR
approves downloads, DigitalOcean/Postgres staging, SQLite authority changes, or
an ingest cutover.

Disposition: FIXED

Evidence:
- `docs/orchestration/FOOD_DATA_USDA_FDC_2026_COMPAT_PREFLIGHT_PACKET_2026-06-08.md`
  declares file-only scope and out-of-scope runtime/staging/network work.
- `docs/roadmap/BACKLOG_LEDGER.md` keeps metadata propagation, staging/Postgres,
  cutover, and Open Food Facts refresh as deferred follow-ups.

### PM-USDA-004: Live USDA API Or DEMO_KEY Leaks Into CI

Failure story: A manifest or parser test calls USDA FDC endpoints, passes
locally with `DEMO_KEY`, then flakes or rate-limits CI.

Disposition: FIXED

Evidence:
- `scripts/food_source_usda_fdc_manifest.py` accepts local files only and emits
  JSON to stdout.
- `tests/test_usda_fdc_manifest_emitter.py` runs the CLI with no USDA key, a
  hostile `DATABASE_URL`, and asserts no temp data directory is created.

## Decision

`proceed with changes` was the premortem decision before closure. All findings
above were fixed or documented as deferred before PR open.

## Pre-Open Checklist

- Focused USDA/FDC manifest, source-preflight, and parser pytest passes.
- Focused mypy passes on changed Python modules/tests.
- Experiment Runner oracle-only evidence runs on the actual diff.
- `make validate-changed` and `pre-commit run --all-files` run before push.
