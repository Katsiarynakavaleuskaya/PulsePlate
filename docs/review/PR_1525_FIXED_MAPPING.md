# PR #1525 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md`; `RUNBOOK_AGENT.md`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md`.

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

This artifact was created immediately after the draft PR opened per repo
governance. Record every actionable human/bot disposition here before resolving
threads on GitHub.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Commit: 7d656bb3df98b3f2acbac6a587b1d2835008ef02
Evidence: `tests/test_payment_source_contract_api.py:13`; `tests/test_payment_source_contract_api.py:68`; `core/food_sources/source_preflight.py:124`.
Reason: Main CI run `24911580731` failed in jobs `72954280558` and `72954280584`
because stale `legacy_app.get_api_key` dependency override keys could survive
inside the shared `app.main.app` test singleton during long shard execution,
letting the manual billing negative auth test receive `201 Created` instead of
the expected `401`.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path core/food_sources/source_preflight.py --path tests/test_payment_source_contract_api.py --path tests/conftest.py` — PASS
- `python3 scripts/orchestration/check_agent_consistency.py` — PASS
- `.venv/bin/pytest -q tests/test_payment_source_contract_api.py tests/test_paid_route_guards.py::test_manual_ru_by_entry_routes_remain_callable_before_entitlement` — PASS (`12 passed`)
- `.venv/bin/python -m mypy --no-incremental --cache-dir=/dev/null app core` — PASS
- `pre-commit run --all-files` — PASS
- `make validate-changed` — PASS
- Pre-push hooks — PASS: changed-file mypy, pip-audit, backend tests, full-repo bandit, docker build test

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
  Evidence: pending current-head CI for commit `7d656bb3df98b3f2acbac6a587b1d2835008ef02`.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending current-head CI.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: pending post-open review cycle.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: no actionable review comments were present when this artifact was created.
- [x] Pre-commit green on latest pushed head
  Evidence: `pre-commit run --all-files` passed before push.
- [ ] `make verify` green on latest pushed head
  Evidence: not satisfied locally; see Validation Evidence note.
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
  Evidence: pending post-open review pass.

## Deferred / Follow-ups

- None.
