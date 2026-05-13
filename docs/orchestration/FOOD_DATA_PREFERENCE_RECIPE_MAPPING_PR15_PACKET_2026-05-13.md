# Food Data PR15: Preference Recipe Mapping Contract

## Summary

PR15 is a file-only governance lane downstream of merged PR14 `#1743`. It
records the preference-to-recipe mapping contract before any preference label,
recipe text, user preference text, LLM output, public chain evidence, Edamam,
Spoonacular, or public menu page can be treated as nutrition authority.

This packet does not approve scraping, API calls, downloads, paid API use,
recipe ingest, DB writes, cache authority, product display, runtime source
authority, DigitalOcean PostgreSQL load, OpenAPI changes, or runtime behavior.

## Coordinator Start

Bootstrap packet: `artifacts/orchestration/task_packets/21a58a9d82bc.json`

Operator override: current-head `main` monitoring/stabilization is owned by the
operator for this lane start. This override permits PR15 worktree preparation
but does not permit merge-readiness claims while current-head PR checks,
review findings, or merge-governance gates are pending or red.

Role order unless coordinator updates this packet:

```text
agent-coordinator -> security-auditor -> data-scientist-agent -> backend-engineer -> qa-engineer-agent -> bug-hunter -> dev-operator
```

Mandatory post-open role lane:

```text
qa-engineer-agent -> bug-hunter
```

## Scope

In scope:

- `docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json`
- typed validator and deterministic report builder under `core/food_sources/`
- CLI wrapper under `scripts/`
- focused pytest coverage for valid artifact load, malformed artifact rejection,
  CLI success/failure, unsafe flag rejection, no-network/no-ingest/no-runtime
  authority invariants, and PR11/PR14 handoff checks
- `docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- PR fixed-mapping artifact after PR number exists

Out of scope:

- API calls, scraping, downloads, or paid provider access
- recipe text ingest or recipe corpus import
- database writes, cache authority, redistribution, or product display
- runtime source authority, PostgreSQL cutover, OpenAPI changes, or API behavior
- provider integration or legal approval for Edamam, Spoonacular, chain pages,
  public menu pages, LLM output, or user preference text

## Premortem Findings

Frame: six months after merge, PR15 failed because a governance-only mapping
contract was mistaken for permission to use recipe/provider/runtime sources.

- Finding 1: PR15 could approve recipe text, preference text, or LLM output as
  nutrition authority.
  - Disposition: FIXED in planned validator/tests.
  - Evidence: top-level and per-mapping authority flags must remain false.
- Finding 2: PR15 could drift from PR11/PR14 handoff.
  - Disposition: FIXED in planned validator/tests.
  - Evidence: validator cross-checks PR11 `preference_menu_planning.next_action`
    and PR14 `next_recommended_lane`.
- Finding 3: PR15 could be treated as ingest/runtime preparation.
  - Disposition: FIXED in packet scope and artifact notes.
  - Evidence: explicit out-of-scope list and `file_only=true` gate.

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR15 preference recipe mapping contract" --task-class Orchestration --pr-phase pre_open --requested-agent agent-coordinator --requested-agent security-auditor --requested-agent data-scientist-agent --requested-agent backend-engineer --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent dev-operator --path docs/orchestration/FOOD_DATA_SOURCE_UPDATE_PREFLIGHT_CURRENT.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/architecture --path core/food_sources --path scripts --path tests
${VENV_PYTHON:-.venv/bin/python} -m pytest tests/test_food_source_preference_recipe_mapping.py -q
${VENV_PYTHON:-.venv/bin/python} -m pytest tests/test_food_source_preference_recipe_mapping.py tests/test_food_source_recipe_dish_corpus.py tests/test_food_source_gap_audit.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py -q
${VENV_PYTHON:-.venv/bin/python} -m scripts.food_source_preference_recipe_mapping --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --coverage docs/architecture/FOOD_DATA_COVERAGE_SOURCE_GAP_PR11_2026-04-30.json --recipe-dish-corpus docs/architecture/FOOD_DATA_RECIPE_DISH_CORPUS_PR14_2026-05-13.json --governance docs/architecture/FOOD_DATA_PREFERENCE_RECIPE_MAPPING_PR15_2026-05-13.json --json
${VENV_PYTHON:-.venv/bin/python} -m pytest -q tests/test_repo_policy_guards.py
${VENV_PYTHON:-.venv/bin/python} -m pre_commit run --all-files
make validate-changed VENV_PYTHON=${VENV_PYTHON:-.venv/bin/python}
```
