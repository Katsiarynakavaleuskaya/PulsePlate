# PR #1590 Fixed in Commit Mapping

## Discussion Thread Pass

- Status: No GitHub review threads existed when this artifact was created.
- Mandatory post-open lane: `qa-engineer-agent -> bug-hunter`.
- External bots: no actionable CodeRabbit, Sourcery, or Cubic comments were
  available at artifact creation time.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 561e65a98
Evidence:
- `core/food_sources/menustat_replacement.py`
- `scripts/food_source_menustat_replacement.py`
- `docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json`
- `tests/test_food_source_menustat_replacement.py`

Summary:
- Added deterministic, file-only MenuStat replacement source gate.
- Kept MenuStat legacy/static and all replacement candidates blocked.
- Added safety checks for no runtime cutover, no DigitalOcean Postgres load, no
  bulk ingest, no network, and no DB writes.
- Added negative coverage for missing/unknown/duplicate candidates, premature
  approvals, unsafe flags, freshness approval drift, invalid evidence refs, and
  catalog/onboarding drift.

## Merge Readiness Evidence

Local gates on PR branch:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR9 MenuStat replacement source gate" --task-class "Orchestration" --pr-phase pre_open
python3 -m pytest tests/test_food_source_menustat_replacement.py tests/test_food_source_onboarding.py tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q
python3 -m scripts.food_source_menustat_replacement --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json --decision docs/architecture/FOOD_DATA_MENUSTAT_REPLACEMENT_PR9_2026-04-30.json --json
pytest -q tests/test_repo_policy_guards.py
make validate-changed VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python
pre-commit run --all-files
```

Local `make verify` is intentionally deferred for this food-data lane per
operator policy; GitHub current-head CI remains the machine-heavy signal.
