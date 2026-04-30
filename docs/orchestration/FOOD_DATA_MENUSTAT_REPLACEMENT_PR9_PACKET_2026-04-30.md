# Food Data PR9: MenuStat Replacement Source Gate

## Summary

PR9 adds a deterministic, file-only decision gate for MenuStat replacement
sources. MenuStat remains a legacy/static restaurant-menu baseline and reference
format only; it is not approved as a current restaurant-menu authority.

PR9 does not approve a replacement source, download data, call provider APIs,
scrape restaurant websites, connect to a database, write to DigitalOcean
Postgres, or change runtime food search.

## Coordinator Start

- Coordinator: `agent-coordinator`
- Branch: `codex/food-data-menustat-replacement-pr9`
- Required role order:
  `agent-coordinator -> data-scientist-agent -> backend-engineer -> security-auditor -> qa-engineer-agent -> bug-hunter -> dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`
- Bootstrap packet: `eaa00d34d92e`

## Scope

- Mark PR8 JPTN identity/license gate as landed in PR `#1577`.
- Add the canonical MenuStat replacement decision artifact:
  [`FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json`](../architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json).
- Validate existing replacement candidates only:
  - `nutritionix`;
  - `fatsecret_platform`;
  - `spoonacular`;
  - `chain_public_nutrition_pages`.
- Validate each candidate against:
  - PR3 source catalog identity and `replacement_for=menustat`;
  - PR5 onboarding blocked state;
  - explicit no-cutover safety flags.
- Add a repo-local dry-run CLI:
  `python3 -m scripts.food_source_menustat_replacement --catalog <path> --onboarding <path> --decision <path> --json`.

## Out Of Scope

- Adding Edamam, OpenMenu, ChowAPI, or any new replacement candidate.
- Live API calls, key validation, web scraping, source downloads, checksum
  discovery, or row-count discovery.
- Restaurant-menu ingest, staging, snapshot promotion, PostgreSQL staging,
  DigitalOcean production load, or runtime authority cutover.
- Changing app APIs, OpenAPI, frontend, iOS, Meilisearch, or food search.

## Evidence Policy

- MenuStat official data page lists free annual datasets through 2022, so it is
  preserved only as `legacy_static` historical baseline:
  <https://www.menustat.org/data.html>.
- Nutritionix remains a contract-review restaurant-menu candidate:
  <https://developer.nutritionix.com/> and
  <https://developer.nutritionix.com/docs/v2>.
- FatSecret Platform remains a low-cost/startup-oriented candidate for future
  API proof, but attribution, cache, redistribution, and contract terms are not
  approved in PR9:
  <https://platform.fatsecret.com/platform-api>,
  <https://platform.fatsecret.com/api-editions?cpc=true>, and
  <https://platform.fatsecret.com/attribution>.
- Spoonacular remains useful for recipe/menu query experiments, but not as
  database authority by default because pricing/docs include tight free quota
  and cache restrictions:
  <https://spoonacular.com/food-api/pricing> and
  <https://spoonacular.com/food-api/docs>.
- Direct chain nutrition pages remain public evidence references only; per-chain
  license, anti-scraping, cache, display, attribution, schema, and freshness
  review are required before use beyond manual evidence.

The committed validator performs no live search or network request.

## Validation

Required start gates:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR9 MenuStat replacement source gate" --task-class "Orchestration" --pr-phase pre_open
```

Targeted PR9 validation:

```bash
python3 -m pytest tests/test_food_source_menustat_replacement.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q
python3 -m scripts.food_source_menustat_replacement --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --decision docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Do not run local `make verify` for this lane; GitHub current-head CI remains the
machine-heavy signal.

## Security Notes

- PR9 is file-only.
- No network, database, credential, DigitalOcean, production import, scraping,
  or runtime cutover path is allowed in the validator.
- Commercial APIs stay blocked until contract, cache, display, attribution,
  redistribution, rate-limit, rollback, and removal terms are approved.
- Chain public pages stay blocked until per-chain legal and anti-scraping review
  is complete.
- The CLI report must keep `runtime_cutover=false`,
  `digitalocean_postgres_load=false`, `bulk_ingest=false`,
  `network_allowed=false`, and `db_writes_allowed=false`.

## Marketing & GTM

No product, API, UX, launch, pricing, or public dataset claim changes in PR9.
Safe external language remains: MenuStat replacement evaluation is in progress;
no new restaurant-menu source is approved yet.

## Decision Log

- PR8 JPTN identity/license gate landed in PR `#1577`.
- PR9 approves only a deterministic replacement-source decision gate.
- A later source-specific PR must prove provider terms, cache/display rights,
  attribution, redistribution, rate limits, freshness, schema, rollback, and
  manifest preflight before any restaurant-menu ingest begins.
