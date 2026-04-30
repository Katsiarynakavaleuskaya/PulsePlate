# Food Data PR13: Per-Chain Legal / Anti-Scraping Review Gate

## Summary

PR13 is a file-only governance lane downstream of merged PR12 `#1609`. It
records the per-chain legal and anti-scraping review requirements for
McDonald's, Chipotle, Starbucks, and similar future official public chain
nutrition pages before any source-specific automation, cache, ingest, or
runtime lane can open.

PR13 does not approve scraping, API calls, downloads, ingest, database writes,
DigitalOcean Postgres, cache authority, redistribution, public dataset claims,
or runtime source authority.

## Coordinator And Role Order

- `agent-coordinator`
- `security-auditor`
- `data-scientist-agent`
- `backend-engineer`
- `qa-engineer-agent`
- `bug-hunter`
- `dev-operator`
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`

## Custom Skills And Plugins

- `pulseplate-workflow`: isolated worktree, PR lifecycle, PR body, merge/cleanup.
- `pulseplate-gates`: start gates, targeted tests, machine-heavy `make verify`
  deferral evidence.
- `pulseplate-guards`: no ingest, no network, no DB writes, no runtime cutover,
  no scraping, no automation, no cache authority, and no redistribution.
- `pulseplate-ledger`: backlog/current-pointer update.
- `pulseplate-pr-review`: `PR_<N>_FIXED_MAPPING.md`, review disposition, merge
  readiness mapping.
- GitHub plugin/CLI: PR, current-head CI, review truth.
- Browser Use / Computer Use: optional manual evidence inspection only; no
  automated collection or bypass of PR12/PR13 restrictions.

## Governance Decision

- `chain_public_nutrition_pages` remains `source_classification=unresolved`.
- `per_chain_reviews` must exactly match the PR12 representative chain page
  order and official URLs.
- Each chain remains `manual_evidence_internal_review_only`.
- Per-chain required fields stay blocked or unapproved:
  legal review, anti-scraping review, cache, display, attribution,
  redistribution, freshness, schema, screenshot evidence, and rollback.
- Next lane is `recipe_dish_corpus_governance`, not source ingest.

## Boundaries

- No app API, OpenAPI, frontend, iOS, runtime food search, database schema,
  credentials, paid API integration, source download, scraper, ingest,
  DigitalOcean Postgres, or runtime source authority changes.
- PR13 adds repo-local governance only:
  `docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json`,
  `core/food_sources/per_chain_legal_review.py`, and
  `scripts/food_source_per_chain_legal_review.py`.
- Recipe/dish corpus governance is explicitly deferred to the next food lane.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR13 per-chain legal anti-scraping review gate" --task-class "Orchestration" --pr-phase pre_open
python3 -m pytest tests/test_food_source_per_chain_legal_review.py -q
python3 -m pytest tests/test_food_source_chain_public_nutrition.py tests/test_food_source_per_chain_legal_review.py tests/test_food_source_gap_audit.py tests/test_food_source_menustat_source_decision.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py -q
python3 -m scripts.food_source_per_chain_legal_review --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --coverage docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json --chain-public-nutrition docs/architecture/FOOD_DATA_CHAIN_PUBLIC_NUTRITION_PR12_2026-04-30.json --governance docs/architecture/FOOD_DATA_PER_CHAIN_LEGAL_ANTI_SCRAPING_PR13_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make validate-changed VENV_PYTHON=.venv/bin/python
```

Local `make verify` is intentionally deferred per operator policy for this
food-data lane; GitHub current-head CI remains the machine-heavy signal.
