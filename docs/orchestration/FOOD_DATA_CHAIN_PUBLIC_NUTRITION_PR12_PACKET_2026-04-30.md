# Food Data PR12: Chain Public Nutrition Pages Governance

## Summary

PR12 is a file-only governance lane after merged PR11 `#1601`. It defines how
PulsePlate may record official public chain nutrition pages as manual evidence
for future restaurant-menu review. It does not add restaurant calorie
calculator functionality; that backend capability already exists. PR12 only
governs evidence boundaries for McDonald's, Chipotle, Starbucks, and similar
chain nutrition pages before any source-specific legal or automation lane.

PR12 does not approve scraping, API calls, downloads, ingest, database writes,
DigitalOcean Postgres, cache authority, redistribution, public dataset claims,
or runtime source authority.

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
- `pulseplate-guards`: no ingest, no network, no DB writes, no runtime cutover,
  no scraping, and no paid-source use.
- `pulseplate-ledger`: backlog/current-pointer update.
- `pulseplate-pr-review`: `PR_<N>_FIXED_MAPPING.md`, review disposition, merge
  readiness mapping.
- `pulseplate-graphmap`: optional only if source-decision graph wording needs a
  deterministic map update.
- `pulseplate-monetization-gtm`: no-op guardrail; no pricing, paywall, or GTM
  surface changes.
- GitHub plugin/CLI: PR, current-head CI, review truth.
- Browser Use / web research: official source evidence confirmation only.
- Documents: packet text support only.
- Spreadsheets: not used in PR12.

## Governance Decision

- `chain_public_nutrition_pages` remains `source_classification=unresolved`.
- It remains `active_update_source=false`, `eligible_preflight=false`,
  `approved_ingest=false`, and `approved_runtime_authority=false`.
- Allowed evidence types are limited to:
  - `official_public_url_citation`
  - `manual_screenshot_internal_review`
- Blocked methods include scraping, automated collection, API calls, downloads,
  social-media harvesting, login/paywall bypass, cache authority,
  redistribution, runtime authority, and public dataset claims.
- Next lane is `per_chain_legal_anti_scraping_review`, not source ingest.

## Representative Evidence

- FDA menu labeling requirements explain why chain nutrition information can be
  publicly available, but they do not grant scraping, cache, automation, or
  redistribution permission:
  <https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/menu-labeling-requirements>
- McDonald's US nutrition calculator:
  <https://www.mcdonalds.com/us/en-us/about-our-food/nutrition-calculator.html>
- Chipotle nutrition calculator:
  <https://www.chipotle.com/nutrition-calculator>
- Starbucks nutrition page:
  <https://www.starbucks.com/menu/nutrition-info>

## Boundaries

- No app API, OpenAPI, frontend, iOS, runtime food search, database schema,
  credentials, paid API integration, source download, scraper, ingest,
  DigitalOcean Postgres, or runtime source authority changes.
- PR12 adds repo-local governance only:
  `docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json`,
  `core/food_sources/chain_public_nutrition.py`, and
  `scripts/food_source_chain_public_nutrition.py`.
- USDA remains core product-food authority and Open Food Facts remains
  auxiliary for product/barcode coverage. Restaurant-menu and recipe/dish
  corpora stay separate unresolved source areas.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR12 chain public nutrition pages governance" --task-class "Orchestration" --pr-phase pre_open
python3 -m pytest tests/test_food_source_chain_public_nutrition.py tests/test_food_source_gap_audit.py tests/test_food_source_menustat_source_decision.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py -q
python3 -m scripts.food_source_chain_public_nutrition --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --coverage docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json --governance docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON=.venv/bin/python
```

Local `make verify` is intentionally deferred per operator policy for this
food-data lane; GitHub current-head CI remains the machine-heavy signal.
