# PR #1517 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`;
`docs/orchestration/AGENTS.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the draft PR opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: dc9ddecc7
Evidence: `core/food_sources/source_preflight.py`; `scripts/food_source_preflight.py`
Reason: CodeRabbit's docstring coverage warning was addressed with concise helper/CLI docstrings; the remaining service rate-limit notice did not request code or documentation changes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#issuecomment-4313826624 -> dc9ddecc7

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4171119355
Reason: Sourcery posted a service rate-limit notice only; no code or documentation changes were requested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4171119355

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#issuecomment-4313917207
Reason: Codecov reported all modified coverable lines covered by tests and did not request code or documentation changes.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#issuecomment-4313917207

Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172022518
Reason: Sourcery posted a second service rate-limit notice after ready-for-review; no code or documentation changes were requested.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172022518

Disposition: FIXED
Commit: dc9ddecc7
Evidence: `core/food_sources/source_preflight.py`; `tests/test_food_source_preflight.py`
Reason: Manifest `retrieved_on` parsing now rejects compact/non-YYYY-MM-DD forms before ISO parsing, with regression coverage for compact dates.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172033067 -> dc9ddecc7
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#discussion_r3139062053 -> dc9ddecc7

Disposition: FIXED
Commit: 3759d03aa
Evidence: `tests/test_food_source_preflight.py`
Reason: CLI file-only test now runs the subprocess from `tmp_path`, so the before/after file-tree assertion checks the actual working directory used by the CLI process.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172181086 -> 3759d03aa

Disposition: FIXED
Commit: 49efc9ec9
Evidence: `docs/review/PR_1517_FIXED_MAPPING.md`
Reason: The review artifact now records portable validation commands and keeps the scope-boundary proof readable without host-specific absolute paths.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#discussion_r3139309011 -> 49efc9ec9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172299948 -> 49efc9ec9
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1517#pullrequestreview-4172242156 -> 49efc9ec9

## Initial Implementation Commits

- `1a2c265b7` - `feat(food-data): add source preflight skeleton`
- `dc9ddecc7` - `fix(food-data): enforce manifest date format`
- `3c706a0fc` - `fix(food-data): add source delta preflight report`
- `3759d03aa` - `test(food-data): verify cli working directory isolation`
- `49efc9ec9` - `docs: remove local path from pr1517 artifact`

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete with no pending required jobs
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] After latest bot/review activity, perform a final check and wait at least
      one review cycle before merging
- [x] `python3 scripts/orchestration/check_preflight.py`
- [x] `python3 scripts/orchestration/check_agent_consistency.py`
- [x] `python3 -m pytest tests/test_food_source_preflight.py -q`
      after review fix (`9 passed`)
- [x] `python3 scripts/food_source_preflight.py --current-manifest tests/fixtures/food_source_preflight/current_off_manifest.json --incoming-manifest tests/fixtures/food_source_preflight/incoming_off_manifest.json --dry-run --json`
- [x] invalid-manifest CLI smoke returned exit `1` with JSON
      `validation_errors`
- [x] `pre-commit run --all-files`
- [x] Pre-push hooks passed during
      `git push -u origin codex/food-data-source-preflight-tooling`
- [ ] `make verify` green on latest pushed head
      Local owner override on 2026-04-24: full local `make verify` is not run
      for this PR2 lane because the long full-suite path overloads the local
      machine; use GitHub current-head required checks as the heavy signal.

## Scope Boundary Proof

- Absent: DigitalOcean PostgreSQL connection strings, credentials, and writes.
- Source downloads and production/staging/local bulk ingest are not performed.
- PR2 dry-run reports keep `runtime_cutover: false`; runtime authority remains
  unchanged.
- Public API, OpenAPI, frontend, iOS, Meilisearch, pgvector, and restaurant
  endpoint behavior are unchanged.
