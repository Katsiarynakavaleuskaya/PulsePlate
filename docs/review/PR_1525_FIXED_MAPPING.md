# PR #1525 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `RUNBOOK_AGENT.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the draft PR was opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Post-Open Role Review

- `qa-engineer-agent`: PASS. Reviewed the two-test isolation patch and local
  validation coverage; no missing blocking negative-path test was found.
- `bug-hunter`: PASS. Reviewed stale override removal/restoration and
  cross-test state leakage risk; no blocking edge-case findings were found.

## Implementation Evidence

Commit: 50a02aec1
Evidence: `tests/test_payment_source_contract_api.py:17`; `tests/test_payment_source_contract_api.py:29`; `tests/test_payment_source_contract_api.py:71`; `tests/test_payment_source_contract_api.py:110`.
Reason: Main CI run `24911580731` failed in jobs `72954280558` and `72954280584`
because stale `legacy_app.get_api_key` dependency override keys could survive
inside the shared `app.main.app` test singleton during long shard execution,
letting the manual billing negative auth test receive `201 Created` instead of
the expected `401`.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path tests/test_payment_source_contract_api.py --path tests/conftest.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `.venv/bin/pytest -q tests/test_payment_source_contract_api.py tests/test_paid_route_guards.py::test_manual_ru_by_entry_routes_remain_callable_before_entitlement tests/test_food_source_preflight.py` — PASS (`21 passed`)
- `make validate-changed` — PASS
- `pre-commit run --all-files` — PASS

Local `make verify` note: attempted before PR open. It passed `verify-env`,
`lint`, `typecheck`, and `test-fast`, then was externally terminated during the
full coverage phase with `make: *** [diff-cov] Terminated: 15`. This is not a
green full local gate claim.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md`; `RUNBOOK_AGENT.md`; `docs/orchestration/COORDINATOR_MERGE_READINESS_RULES.md`.

- [ ] Mandatory wait-window satisfied (final check pass completed, then waited >=1 review cycle after latest bot/review activity)
  Evidence: pending post-open review cycle.
- [ ] Current-head CI is green for PR branch head
  Evidence: pending current-head CI for the next pushed head.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head CI.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending post-open review cycle.
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: pending final review-governance pass after latest bot comments.
- [ ] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed after rebase.
- [ ] `make verify` green on latest pushed head
  Evidence: not satisfied locally; see Validation Evidence note.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: both post-open role passes reported no blocking findings.

## Deferred / Follow-ups

- None.
