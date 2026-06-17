# PR #1988 Fixed Mapping

## Lane Start Provenance

- Branch: `codex/fix-legacy-export-api-key-contract-test`
- Packet: `artifacts/orchestration/task_packets/bbe1149e83c7.json`
- Base: `main` at post-merge PR #1987 commit
  `f6c66ba5e16a178849b17670f7d9d1eb0ddefef5`.
- Trigger: post-merge `main` CI run `27657385344` failed in
  `test-main (3.11, 60)`.

## Scope Boundary

- In scope: make the legacy export alias route ownership test assert stable
  API-key dependency contract by callable module/name instead of stale module
  object identity.
- Out of scope: runtime route changes, auth/rate-limit behavior changes, legacy
  removal, cache/runtime/FoodDB/frontend/iOS work.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Initial PR open: no review threads existed at artifact creation.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: faac8b570
Evidence: `tests/test_legacy_export_aliases.py` now accepts the stable `legacy_app._get_api_key_dynamic` callable contract by module/name instead of requiring object identity across module reloads; focused legacy export alias tests and `make validate-changed` pass.
Reason: Fixes post-merge main CI failure from run `27657385344`, `test-main (3.11, 60)`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1988 -> faac8b570

Disposition: FIXED
Commit: 312bfbac773b077ec83f8f42bc9595fcdb154faa
Evidence: `tests/test_legacy_export_aliases.py` now resolves the dependency module with `inspect.getmodule(...)` against `legacy_app.__name__` and includes method/path/dependency details in the failure message; `pytest -q tests/test_legacy_export_aliases.py`, `make validate-changed`, and `pre-commit run --all-files` pass.
Reason: Addresses Sourcery review feedback on robust module matching and assertion diagnostics.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1988#discussion_r3425005305 -> 312bfbac773b077ec83f8f42bc9595fcdb154faa
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1988#pullrequestreview-4511526104 -> 312bfbac773b077ec83f8f42bc9595fcdb154faa

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path tests/test_legacy_export_aliases.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Stabilize post-merge main CI by making legacy export alias API-key dependency ownership test resilient to module reload identity churn" --task-class Bugfix --pr-phase pre_open --path tests/test_legacy_export_aliases.py --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor`
- PASS: `. .venv/bin/activate && pytest -q tests/test_legacy_export_aliases.py::test_legacy_export_alias_routes_are_hidden_shim_owned_and_protected tests/test_legacy_export_aliases.py::test_legacy_export_aliases_reject_missing_api_key tests/test_main_paywall_bootstrap.py::test_legacy_export_alias_route_registration_allows_reloaded_canonical_handlers tests/test_main_paywall_bootstrap.py::test_legacy_export_alias_route_registration_rejects_foreign_handlers`
- PASS: `. .venv/bin/activate && pytest -q tests/test_legacy_export_aliases.py`
- PASS: `.venv/bin/ruff check tests/test_legacy_export_aliases.py`
- PASS: `.venv/bin/black --check tests/test_legacy_export_aliases.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS after Sourcery fix: `. .venv/bin/activate && pytest -q tests/test_legacy_export_aliases.py`
- PASS after Sourcery fix: `.venv/bin/black tests/test_legacy_export_aliases.py && .venv/bin/ruff check tests/test_legacy_export_aliases.py`
- PASS after Sourcery fix: `make validate-changed`
- PASS after Sourcery fix: `pre-commit run --all-files`
- PASS during push hooks: pip-audit, backend tests, full-repo Bandit, and docker
  build test.

## Experiment Runner Evidence

Not applicable: this PR is a test-oracle correction for a post-merge main CI
failure; no Experiment Runner artifact shaped the code, tests, mapping, or
commit decision.

## Security Notes

- Runtime auth behavior is unchanged.
- The missing API-key 403 test still exercises FastAPI dependency execution.
- This PR narrows only a stale object-identity test oracle.

## Merge Readiness

Not ready at artifact creation. Required before merge:

- [x] Numbered fixed-mapping artifact created.
- [x] PR body mirror updated to point to this artifact and include exact
  `## Scope`, `## Out of Scope`, and `## Tests` headings.
- [ ] Current-head CI parity on latest pushed commit.
- [ ] Strict merge-readiness check with `--require-auth`.
- [ ] No unresolved actionable review or bot comments.
- [ ] Mandatory wait-window after latest bot/review activity.
