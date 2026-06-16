# PR #1987 Fixed Mapping

## Lane Start Provenance

- Branch: `codex/fix-legacy-export-reload-idempotency`
- Packet: `artifacts/orchestration/task_packets/a6cb67b5610b.json`
- Base: `main` at post-merge PR #1986 commit
  `083907804bad98e0c2a13e60e0a5e12b0861368b`.
- Trigger: post-merge `main` CI run `27649033733` failed in
  `test-main` matrix after PR #1986 merge.

## Scope Boundary

- In scope: route-bootstrap idempotency after `app.main` reload/module purge,
  stale-module-safe legacy export alias test assertion, targeted regression
  coverage, and two inline allowlist pragmas for existing synthetic Slack-token
  test literals required by mandatory `detect-secrets`.
- Out of scope: route semantics, auth/rate-limit behavior, legacy removal,
  cache/runtime/FoodDB/frontend/iOS work.

## Discussion Thread Pass

- [x] Discussion-thread pass completed.
- [x] Fixed in commit mapping completed.
- [x] Initial PR open: no review threads existed at artifact creation.
- [x] Sourcery post-open review fixed in `0a20a9764`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 2e72dfa20
Evidence: `app/main.py` now treats pre-existing canonical `app.routers.legacy_export_aliases` endpoints with the same function name as idempotent after reload, while still rejecting foreign duplicate handlers; `tests/test_main_paywall_bootstrap.py` covers reloaded canonical handlers; `tests/test_legacy_export_aliases.py` resolves the current `legacy_app` module after purge/reload.
Reason: Fixes post-merge main CI failures from run `27649033733`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1987 -> 2e72dfa20

Disposition: FIXED
Commit: 0a20a9764
Evidence: `app/main.py` derives the accepted legacy export alias module name from `app.routers.legacy_export_aliases` and explicitly rejects non-callable endpoint candidates before comparing module and function names.
Reason: Addresses Sourcery review feedback about avoiding a hard-coded module string and making endpoint equivalence more defensive.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1987#pullrequestreview-4510864368 -> 0a20a9764

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path tests/test_main_paywall_bootstrap.py --path tests/test_legacy_export_aliases.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --goal "Stabilize post-merge main CI by making legacy export alias router idempotent across app.main reload/module purge" --task-class Bugfix --pr-phase pre_open --path app/main.py --path tests/test_main_paywall_bootstrap.py --path tests/test_legacy_export_aliases.py --requested-agent agent-coordinator --requested-agent qa-engineer-agent --requested-agent bug-hunter --requested-agent security-auditor`
- PASS: `. .venv/bin/activate && pytest -q tests/test_legacy_export_aliases.py tests/test_main_paywall_bootstrap.py tests/test_module_purge.py::test_purge_modules_respects_exclusions_and_removes_only_targets tests/test_coverage_final_push.py::TestFinalCoveragePush::test_vip_import_fallbacks`
- PASS: `python3 scripts/ci/check_legacy_growth_guard.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS during commit/push hooks: changed-file mypy, pip-audit, backend
  tests, full-repo Bandit, and docker build test.

## Security Notes

- No auth, API-key, feature-gate, response, or rate-limit behavior changes.
- Existing route equivalence remains narrow: only canonical
  `app.routers.legacy_export_aliases` endpoints with matching function names
  are accepted after reload; foreign handlers still fail.
- Slack-token strings are synthetic redaction-test fixtures and are marked with
  inline `pragma: allowlist secret` comments only on the literal fixture lines.

## Merge Readiness

Not ready at artifact creation. Required before merge:

- [x] Numbered fixed-mapping artifact created.
- [ ] PR body mirror updated to point to this artifact.
- [ ] Current-head CI parity on latest pushed commit.
- [ ] Strict merge-readiness check with `--require-auth`.
- [ ] No unresolved actionable review or bot comments.
- [ ] Mandatory wait-window after latest bot/review activity.
