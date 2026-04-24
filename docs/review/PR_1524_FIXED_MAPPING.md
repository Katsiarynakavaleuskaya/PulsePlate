# PR #1524 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

This artifact was created immediately after the draft PR opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

No review threads have been posted yet.

## Initial Implementation Commits

- `f0f53c5f8` - `feat(food-data): add source catalog preflight`

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [ ] Draft converted to ready after pending-base gate is clear
- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete with no pending required jobs
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least
      one review cycle before merging
- [x] `python3 scripts/orchestration/check_preflight.py`
- [x] `python3 scripts/orchestration/check_agent_consistency.py`
- [x] `python3 -m pytest tests/test_food_source_catalog.py tests/test_food_source_preflight.py -q`
      (`15 passed`)
- [x] `python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_off_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_off_manifest.json --dry-run --json`
- [x] `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python make validate-changed`
      (`6 passed`)
- [x] `pre-commit run --all-files`
- [x] Pre-push hooks passed during
      `git push -u origin codex/food-data-source-catalog-pr3`
- [ ] `make verify` green on latest pushed head
      Local owner override on 2026-04-24: full local `make verify` is not run
      for this PR3 lane because the long full-suite path overloads the local
      machine; use GitHub current-head required checks as the heavy signal.

## Pending Base Gate

- Operator override on 2026-04-24: PR #1524 was opened while post-merge
  `main` CI for merge commit `feaf8d6f1` was still in progress.
- PR remains draft until `main` current-head health and PR current-head checks
  are stable.

## Scope Boundary Proof

- Absent: DigitalOcean PostgreSQL connection strings, credentials, and writes.
- Source downloads and production/staging/local bulk ingest are not performed.
- Runtime source authority is unchanged; catalog safety flags keep
  `runtime_cutover=false`, `digitalocean_postgres_load=false`, and
  `bulk_ingest=false`.
- Public API, OpenAPI, frontend, iOS, Meilisearch, pgvector, and restaurant
  endpoint behavior are unchanged.
- MenuStat is non-updating `legacy_static`; replacement candidates are
  cataloged only and not approved for ingest.
