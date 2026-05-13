# Food Data PR14: Recipe/Dish Corpus Governance Gate

## Summary

PR14 is a file-only governance lane downstream of merged PR13 `#1613`. It
records recipe/dish corpus review requirements for Edamam Food Database,
Spoonacular, and similar future recipe or dish-corpus candidates before any
source-specific API, paid plan, cache, ingest, database, or runtime lane can
open.

PR14 does not approve scraping, API calls, downloads, paid API use, ingest,
database writes, DigitalOcean Postgres, cache authority, redistribution, public
dataset claims, product display, or runtime source authority.

## Coordinator And Role Order

- `agent-coordinator`
- `security-auditor`
- `data-scientist-agent`
- `backend-engineer`
- `qa-engineer-agent`
- `bug-hunter`
- `dev-operator`
- Reviewer: `architecture-specialist`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Custom Skills And Plugins

- `pulseplate-workflow`: isolated worktree, PR lifecycle, PR body, merge/cleanup.
- `pulseplate-gates`: start gates, targeted tests, machine-heavy `make verify`
  deferral evidence if approved.
- `pulseplate-guards`: no ingest, no network, no DB writes, no runtime cutover,
  no scraping, no API calls, no paid source use, no cache authority, and no
  redistribution.
- `pulseplate-premortem-risk-review`: required before pre-open scope lock and
  repeated after PR-open if review or security findings change the risk surface.
- `pulseplate-ledger`: backlog/current-pointer update.
- `pulseplate-pr-review`: `PR_<N>_FIXED_MAPPING.md`, review disposition, merge
  readiness mapping.
- GitHub plugin/CLI: PR, current-head CI, review truth.
- CodeRabbit and Codex Security plugins: post-open review, security, and bug
  finding loops.

## Governance Decision

- `recipe_dish_corpora` remains governance-only.
- `edamam_food_database` and `spoonacular` remain review candidates only.
- Every candidate keeps legal review, contract review, cache, display,
  attribution, redistribution, freshness, schema, and rollback unapproved.
- Next lane is `preference_recipe_mapping_contract`, not source ingest.

## Boundaries

- No app API, OpenAPI, frontend, iOS, runtime food search, database schema,
  credentials, paid API integration, source download, scraper, ingest,
  DigitalOcean Postgres, or runtime source authority changes.
- PR14 adds repo-local governance only:
  `docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json`,
  `core/food_sources/recipe_dish_corpus.py`, and
  `scripts/food_source_recipe_dish_corpus.py`.
- Preference-to-recipe mapping is explicitly deferred to the next food lane.

## Pre-Open Premortem Closure

Failure frame: six months after merge, PR14 failed because a governance-only
artifact was misread as approval to use recipe APIs or paid food sources.

- Finding 1: PR14 could accidentally approve recipe source use.
  - Disposition: FIXED
  - Evidence: `docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json`
    keeps every unsafe top-level and per-source flag false; the validator rejects
    ingest, runtime authority, scraping, automation, API calls, downloads, DB
    writes, paid source use, cache authority, and redistribution.
- Finding 2: PR13 could remain stale in the source-update pointer, causing agents
  to reopen the wrong lane.
  - Disposition: FIXED
  - Evidence: `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
    now lists PR14, and `docs/roadmap/BACKLOG_LEDGER.md` marks PR13 merged while
    identifying PR14 as the active lane.
- Finding 3: PR14 could drift away from earlier food-source gates.
  - Disposition: FIXED
  - Evidence: `core/food_sources/recipe_dish_corpus.py` validates the PR14
    artifact against PR5 onboarding, PR11 coverage/source-gap audit, PR12 chain
    public nutrition, and PR13 per-chain legal review.
- Finding 4: Local validation could be falsely green if untracked Python files or
  a system Python without repo dependencies were used.
  - Disposition: FIXED
  - Evidence: focused and adjacent pytest were run through the repo `.venv`;
    `pre-commit run --all-files` was rerun after staging so new files were
    included.
- Finding 5: The packet could drift from coordinator routing by omitting the
  routed reviewer.
  - Disposition: FIXED
  - Evidence: this packet records `architecture-specialist` as reviewer while
    preserving the required role order and post-open `qa-engineer-agent ->
    bug-hunter` lane.
- Finding 6: Price-like wording could be misread as current market research in
  a no-network, file-only PR.
  - Disposition: FIXED
  - Evidence:
    `docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json`
    uses price-neutral Edamam wording.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR14 recipe dish corpus governance gate" --task-class "Orchestration" --pr-phase pre_open --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_food_source_recipe_dish_corpus.py -q
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest tests/test_food_source_recipe_dish_corpus.py tests/test_food_source_per_chain_legal_review.py tests/test_food_source_chain_public_nutrition.py tests/test_food_source_gap_audit.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py -q
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m scripts.food_source_recipe_dish_corpus --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --coverage docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json --chain-public-nutrition docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json --per-chain-legal docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json --governance docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json --json
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pytest -q tests/test_repo_policy_guards.py
/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python -m pre_commit run --all-files
make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python
```

Local `make verify` may be deferred only if coordinator/operator explicitly
documents a machine-heavy deferral; otherwise it remains the full local gate.
