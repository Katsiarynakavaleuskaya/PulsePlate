# Food Data PR11: Coverage / Source-Gap Audit

## Summary

PR11 is a file-only coverage/source-gap audit after merged PR10 `#1597`. It
answers the product-source question before any new source-specific onboarding:
USDA remains the core product food authority, Open Food Facts remains auxiliary
for barcode/branded coverage, and the unresolved areas are restaurant-chain
menus, recipe/dish corpora, regional/local foods, and preference-menu planning.

PR11 does not approve ingest, API calls, scraping, paid-source use, database
writes, DigitalOcean Postgres, or runtime cutover.

## Coordinator And Role Order

- `agent-coordinator`
- `data-scientist-agent`
- `backend-engineer`
- `security-auditor`
- `qa-engineer-agent`
- `bug-hunter`
- `dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Custom Skills And Plugins

- `pulseplate-workflow`: isolated worktree, PR lifecycle, PR body, merge/cleanup.
- `pulseplate-gates`: start gates, targeted tests, machine-heavy `make verify`
  deferral evidence.
- `pulseplate-guards`: no ingest, no network, no DB writes, no runtime cutover.
- `pulseplate-ledger`: backlog/current-pointer update.
- `pulseplate-pr-review`: `PR_<N>_FIXED_MAPPING.md`, review disposition, merge
  readiness mapping.
- `pulseplate-graphmap`: optional only if source-decision graph wording needs a
  deterministic map update.
- `pulseplate-monetization-gtm`: no-op guardrail; no pricing, paywall, or GTM
  surface changes.
- GitHub plugin/CLI: PR, current-head CI, review truth.
- Browser Use/browser context: official source page confirmation only. The Open
  Food Facts data page is available in the in-app browser; crawler-style fetches
  may be blocked and must not be required by PR11 tooling.
- Documents: packet text support only.
- Spreadsheets: not used in PR11.

## Coverage Decisions

- Generic food composition: `usda_foundation` with `usda_fndds` support is an
  adequate baseline after manifest/schema preflight.
- Branded/barcode products: `usda_branded` is primary and `open_food_facts` is
  auxiliary; OFF ODbL obligations remain explicit.
- Restaurant-chain menus: unresolved gap. MenuStat is archival/reference-only;
  chain public nutrition pages are the preferred low-cost governance lane only.
- Recipe/dish corpora: unresolved gap. Edamam and Spoonacular remain review
  candidates only, with no API calls or cache authority.
- Preference-menu planning: requires governed dish/recipe mapping; recipe text,
  user preference text, public menu evidence, and LLM output must not become
  canonical nutrition facts.
- Regional/local products: deferred until source identity, license, language,
  unit, nutrient semantics, cache, and redistribution review exists.
- User/manual evidence: internal evidence only after legal review; not dataset
  authority and not a redistributable asset.

## Evidence

- USDA FoodData Central downloads currently show April 2026 Foundation Foods and
  Branded releases plus FNDDS 2021-2023:
  <https://fdc.nal.usda.gov/download-datasets>
- Open Food Facts data page is the canonical human-browser data URL:
  <https://world.openfoodfacts.org/data>
- Open Food Facts ODbL governance:
  <https://wiki.openfoodfacts.org/ODBL_License>
- Edamam Food Database is captured only as an adjacent under-$20 review
  candidate:
  <https://developer.edamam.com/food-database-api>
- FDA menu-labeling rules support public nutrition-information availability but
  do not grant scraping, automation, cache, or redistribution rights:
  <https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/menu-labeling-requirements>

## Boundaries

- No app API, OpenAPI, frontend, iOS, runtime food search, database schema,
  credentials, paid API integration, source download, scraper, ingest,
  DigitalOcean Postgres, or runtime source authority changes.
- PR11 adds repo-local audit governance only:
  `docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json`,
  `core/food_sources/source_gap_audit.py`, and
  `scripts/food_source_gap_audit.py`.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR11 coverage source-gap audit" --task-class "Orchestration" --pr-phase pre_open
python3 -m pytest tests/test_food_source_gap_audit.py tests/test_food_source_menustat_source_decision.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q
python3 -m scripts.food_source_gap_audit --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --coverage docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python
```

Local `make verify` is intentionally deferred per operator policy for this
food-data lane; GitHub current-head CI remains the machine-heavy signal.
