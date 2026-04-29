# Food Data PR8: JPTN Source Identity/License Resolution Gate

## Summary

PR8 adds a deterministic, file-only identity/license gate for
`jptn_food_facts`. It records exactly why JPTN cannot advance to manifest
preflight or ingest yet: provider identity, canonical source URL, license,
retrieval contract, schema, units, attribution, and redistribution rights are
not verified.

PR8 does not remove JPTN from the catalog, ingest JPTN data, download source
files, connect to a database, write to DigitalOcean Postgres, or change runtime
food search.

## Coordinator Start

- Coordinator: `agent-coordinator`
- Branch: `codex/food-data-jptn-identity-license-pr8`
- Required role order:
  `agent-coordinator -> data-scientist-agent -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Scope

- Add the canonical JPTN identity/license artifact:
  [`FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_2026-04-29.json`](../architecture/FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_2026-04-29.json).
- Validate JPTN against:
  - PR3 catalog entry `jptn_food_facts`;
  - PR5 onboarding entry `jptn_food_facts`;
  - explicit no-cutover safety flags.
- Keep JPTN blocked with:
  - `source_classification=unresolved`;
  - catalog `status=blocked_unresolved`;
  - onboarding `onboarding_status=unresolved_blocked`;
  - `final_gate_decision=blocked_until_verified`.
- Add a repo-local dry-run CLI:
  `python3 -m scripts.food_source_jptn_identity --catalog <path> --onboarding <path> --identity <path> --json`.

## Out Of Scope

- JPTN source downloads or live checksum discovery.
- JPTN manifest fixtures.
- JPTN ingest, staging, or snapshot promotion.
- PostgreSQL staging or DigitalOcean production load.
- Runtime authority or food-search cutover.
- MenuStat replacement, restaurant-menu, recipe/corpus, regional source, USDA,
  or OFF onboarding changes.

## Evidence Policy

The PR8 artifact records the reviewed query strings and the gate outcome. Public
searches for `"JPTN Food Facts" nutrition database`, `"JPTN" "Food Facts"`,
`"jptn_food_facts"`, and `"JPTN" food database nutrition` did not identify a
confirmed food-data provider, license, schema, or retrieval contract.

The committed validator performs no live search. Later PRs may update the
artifact only with explicit provider evidence, source URL, legal review, schema
contract, and retrieval policy.

## Validation

Required start gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR8 JPTN identity license gate" --task-class "Orchestration" --pr-phase pre_open
```

Targeted PR8 validation:

```bash
python3 -m pytest tests/test_food_source_jptn_identity.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q
python3 -m scripts.food_source_jptn_identity --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --identity docs/architecture/FOOD_DATA_JPTN_IDENTITY_LICENSE_PR8_2026-04-29.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Do not run local `make verify` for this lane; GitHub current-head CI remains the
machine-heavy signal.

## Security Notes

- PR8 is file-only.
- No network, database, credential, DigitalOcean, production import, or runtime
  cutover path is allowed in the validator.
- JPTN remains blocked until source identity and legal rights are verified.
- The CLI report must keep `runtime_cutover=false`,
  `digitalocean_postgres_load=false`, `bulk_ingest=false`,
  `network_allowed=false`, and `db_writes_allowed=false`.

## Marketing & GTM

No product, API, UX, launch, pricing, or public dataset claim changes in PR8.
The later marketable claim remains a governed multi-source food database with
provenance, only after source-specific ingest and runtime authority lanes are
approved.

## Decision Log

- PR7 Open Food Facts manifest preflight landed in PR `#1572`.
- PR8 does not delete JPTN. It records the unresolved identity/license gap and
  makes the blocked gate deterministic.
- A future JPTN source-specific PR must replace this blocked gate with verified
  provider, license, schema, attribution, redistribution, and retrieval evidence
  before any manifest preflight or ingest begins.
