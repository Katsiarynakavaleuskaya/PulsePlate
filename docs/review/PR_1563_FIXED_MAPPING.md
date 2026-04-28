# PR #1563 Fixed Mapping

PR: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563>
Branch: `codex/food-data-usda-manifest-preflight-pr6`
Date: 2026-04-28

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Artifact status: PR opened as draft while `main` current-head CI was still in
progress. Post-open bot comments are mapped below.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: d6efa02de
Evidence: core/food_sources/source_preflight.py now invokes strict source-contract validation from build_source_preflight_report when catalog/onboarding paths are provided; scripts/food_source_preflight.py exposes optional --catalog/--onboarding args; tests/test_food_source_preflight.py covers the strict failure path and USDA CLI contract path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#discussion_r3156893650 -> d6efa02de

Disposition: FIXED
Commit: d6efa02de
Evidence: core/food_sources/source_preflight.py defines ELIGIBLE_PREFLIGHT_ONBOARDING_STATUS and MANIFEST_PREFLIGHT_ONLY_INGESTION_PATH constants and uses them in onboarding status/path checks.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#discussion_r3156892903 -> d6efa02de
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#pullrequestreview-4192051812 -> d6efa02de

Disposition: NOT-A-BUG
Evidence: core/food_sources/source_preflight.py ALLOWED_SOURCE_CLASSIFICATIONS intentionally allows only current, legacy_static, commercial_contract, and unresolved. tests/test_food_source_preflight.py validates incoming USDA fixtures as source_classification=current and rejects invalid classifications; changing fixture classification to incoming would violate the PR2 manifest contract.
Reason: incoming_* fixture filenames describe the candidate manifest position in a dry-run pair, not a source_classification enum value.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#discussion_r3156901601
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#discussion_r3156901623
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1563#pullrequestreview-4192061903

## Initial Evidence

- `python3 scripts/orchestration/check_preflight.py` (PASS)
- `python3 scripts/orchestration/check_agent_consistency.py` (PASS)
- `python3 scripts/orchestration/task_bootstrap.py --goal "Food Data PR6 USDA manifest preflight gate" --task-class "Orchestration" --pr-phase pre_open` (PASS)
- `python3 -m pytest tests/test_food_source_preflight.py tests/test_food_source_catalog.py tests/test_food_source_onboarding.py -q` (PASS, 64 passed after review fix)
- `python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_usda_foundation_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_usda_foundation_manifest.json --dry-run --json --catalog docs/architecture/FOOD_DATA_SOURCE_CATALOG_PR3_2026-04-24.json --onboarding docs/architecture/FOOD_DATA_SOURCE_ONBOARDING_PR5_2026-04-28.json` (PASS)
- `pytest -q tests/test_repo_policy_guards.py` (PASS, 13 passed)
- `pre-commit run --all-files` (PASS)
- Pre-push hooks: mypy changed files, pip-audit, backend pytest, full-repo bandit, and docker build test (PASS)

Local `make verify` was intentionally deferred for this machine-heavy food lane
per operator policy; GitHub current-head CI remains the heavy signal.

## Merge Readiness

- [ ] CI green on current head
- [ ] No unresolved actionable review threads
- [ ] CodeRabbit/Sourcery/Cubic statuses reviewed and mapped if present
- [ ] Fixed-mapping artifact and PR body mirror aligned
- [ ] `check_merge_ready.py --require-auth` PASS
