# Food Data PR10: MenuStat Source Decision Cleanup

## Summary

PR10 is a file-only governance cleanup after merged PR9 `#1590`. It narrows the
MenuStat replacement-source interpretation so `fatsecret_platform` is not routed
as a PulsePlate project source, MenuStat is explicitly archival/reference-only,
and `chain_public_nutrition_pages` becomes the next preferred low-cost research
lane while staying blocked for automation.

This lane does not reopen the core food database authority decision. PulsePlate
stays USDA-first for the main food database, with Open Food Facts as an auxiliary
source that may need a later schema/PostgreSQL review because upstream fields and
source structure have changed. PR10 focuses on the unresolved restaurant-menu,
dish/recipe database, and preference-menu planning problem space.

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
- Browser/web checks: official source evidence only.
- Documents: packet text support only.
- Spreadsheets: not used in PR10.

## Source Decision Policy

- MenuStat is `legacy_static`, archival/reference-only, and not a freshness
  authority. Its data requires validation before any comparison or downstream use.
- `fatsecret_platform` is `not_project_source` / `rejected_for_project_use`.
- `chain_public_nutrition_pages` is the preferred budget-first research lane, but
  automation is blocked until a dedicated per-chain legal, anti-scraping, cache,
  display, attribution, schema, freshness, and rollback review exists.
- Public restaurant websites and official social accounts may be used only as
  manual evidence after legal review. Allowed PR10 terminology:
  `public_web_evidence_policy=manual_evidence_only_legal_review_required`,
  `url_citation`, and `manual_screenshot_for_internal_review`. Blocked terminology:
  scraping, bulk collection, login/paywall bypass, redistribution, or public
  dataset claims.
- Under-$20 APIs are allowed only as adjacent review candidates, not source
  approval. PR10 records Edamam Food Database as `adjacent_recipe_food_db_review_only`
  because its official Food Database API page lists a $14/month basic plan and
  restaurant/food coverage, while its cache/attribution/automation terms still
  require review.
- `nutritionix` remains deferred for contract review only.
- `spoonacular` remains deferred for recipe experiments only, not restaurant-menu
  database authority.
- Food database baseline remains USDA-first; Open Food Facts remains auxiliary
  and future schema-review work, not PR10 runtime or Postgres work.
- Backend preference-menu planning, such as Mediterranean, gluten-free, and
  similar dietary preference menus, is related product context but is not changed
  by PR10.

## Evidence

- MenuStat public data page lists annual datasets through 2022:
  <https://www.menustat.org/data.html>
- FDA menu labeling rules explain why certain chain restaurant nutrition
  information is publicly available, but they do not grant scraping,
  redistribution, or automation rights:
  <https://www.fda.gov/food/nutrition-food-labeling-and-critical-foods/menu-labeling-requirements>
- FatSecret official editions and attribution pages show contract/attribution
  dependency; PR10 records the product decision not to use it:
  <https://platform.fatsecret.com/api-editions>,
  <https://platform.fatsecret.com/attribution>
- Spoonacular official pricing/cache language blocks database authority use:
  <https://spoonacular.com/food-api/pricing>
- Edamam official Food Database API page is captured as an adjacent under-$20
  recipe/food database review candidate only, not a MenuStat replacement:
  <https://developer.edamam.com/food-database-api>

## Boundaries

- No app API, OpenAPI, frontend, iOS, runtime food search, database authority,
  credentials, API calls, downloads, scraping, ingest, DigitalOcean Postgres, or
  runtime cutover.
- PR10 adds repo-local decision governance only:
  `docs/architecture/FOOD_DATA_MENUSTAT_SOURCE_DECISION_PR10_2026-04-30.json`,
  `core/food_sources/menustat_source_decision.py`, and
  `scripts/food_source_menustat_source_decision.py`.

## Recommended Follow-Up Assessment

The right way to decide whether USDA + Open Food Facts need more product sources
is a separate coverage-audit PR, not an ingest PR. That lane should compare the
current USDA-first/OFF-auxiliary corpus against product journeys:

- barcode/package lookup coverage;
- generic ingredient coverage;
- branded food coverage;
- restaurant-chain menu coverage;
- recipe/dish preference coverage such as Mediterranean, gluten-free, and other
  dietary patterns;
- regional/local food gaps;
- freshness, schema, license, attribution, cache, and rollback constraints.

Only gaps that survive that audit should become source-specific candidates. PR10
does not choose additional product sources.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR10 MenuStat source decision cleanup" --task-class "Orchestration" --pr-phase pre_open
python3 -m pytest tests/test_food_source_menustat_source_decision.py tests/test_food_source_menustat_replacement.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q
python3 -m scripts.food_source_menustat_source_decision --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --replacement docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json --decision docs/architecture/FOOD_DATA_MENUSTAT_SOURCE_DECISION_PR10_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Local `make verify` is intentionally deferred per operator policy for this
food-data lane; GitHub current-head CI remains the machine-heavy signal.
