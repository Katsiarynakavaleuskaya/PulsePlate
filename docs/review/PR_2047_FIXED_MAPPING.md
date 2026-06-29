# PR #2047 Fixed in Commit Mapping SoT

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2047

Branch: `codex/fix-main-manual-billing-auth-ci`

## Summary

This PR stabilizes manual RU/BY billing auth for current main CI by requiring
manual billing transport calls to use the configured app API key validator
instead of legacy `app.get_api_key` dependency override behavior.

## Scope

- Bind manual RU/BY billing transport validation to canonical
  `validate_app_api_key`.
- Add `manual_billing_headers` for tests that call manual billing transport
  routes under strict `API_KEY=test_key`.
- Keep PRO/VIP entitlement keys on paid-route access tests only.
- Add a guard that blocks regressions to tier-key or dependency-override
  authorization for manual billing transport.

## Out Of Scope

No proxy/dependency PR #2046 work, route registration changes, OpenAPI changes,
frontend, iOS, macOS, or provider-secret setup is included. This PR does not
solve real operator/user attribution for manual rails; it restores strict
transport-auth semantics only.

## Implementation Commits

- `8eb1bd1b7` - fix manual billing transport auth and strict CI regression
  coverage.
- `63cf62d39` - add parser-safe PR mapping evidence and adapt async tests for
  the CI pre-commit hook environment.

## Lane Start Provenance

- Base branch: `main`
- Branch: `codex/fix-main-manual-billing-auth-ci`
- Packet: `artifacts/orchestration/task_packets/72cde377b0bd.json`
- Pre-open role order executed:
  `agent-coordinator -> backend-engineer -> qa-engineer-agent -> security-auditor -> bug-hunter`
- Packet creation was treated as provenance/routing only; role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2047`.
- [x] Initial PR open: no GitHub review threads existed and none were resolved.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed.
- [x] `pulseplate-pr-review` completed.
- [ ] Current-head CI complete before readiness language.
- [ ] Strict merge-readiness checks run after the final review/check cycle.

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED

Commit: `8eb1bd1b7`

Evidence: `app/routers/billing.py`, `tests/conftest.py`,
`tests/guards/test_manual_billing_auth_contract_guard.py`,
`tests/test_paid_route_guards.py`,
`tests/test_payment_source_contract_api.py`,
`tests/test_payment_reconciliation_api.py`, and
`tests/test_subscription_activation_api.py`.

## Pre-Open Role Findings

Role: `security-auditor`

Disposition: FIXED

Commit: `8eb1bd1b7`

Evidence: Security review found stale CI-selected paid-route guard tests still
expected PRO/VIP entitlement keys to authorize manual billing transport routes.
Commit `8eb1bd1b7` updates `tests/test_paid_route_guards.py` so manual
transport calls use `manual_billing_headers` and paid-route entitlement tests
seed backend state for the PRO/VIP subject explicitly.

Role: `bug-hunter`

Disposition: FIXED

Commit: `8eb1bd1b7`

Evidence: Bug-hunter found the local validation bundle initially omitted
CI-selected billing entitlement suites. Commit `8eb1bd1b7` was validated with
the expanded billing entitlement group:
`tests/test_api_tiers_db_lookup.py`,
`tests/test_billing_openapi_contract.py`,
`tests/test_ios_receipt_verification_api.py`,
`tests/test_paid_route_guards.py`,
`tests/test_payments_activation_paywall_events.py`,
`tests/test_payment_reconciliation_api.py`,
`tests/test_payment_source_contract_api.py`,
`tests/test_payment_webhook_signature_api.py`,
`tests/test_pro_payments_openapi_contract.py`, and
`tests/test_subscription_activation_api.py`.

Disposition: FIXED

Commit: `8eb1bd1b7`

Evidence: Bug-hunter found a behavioral dependency-override regression test
was using a local fake `get_api_key` instead of the real app dependency key.
Commit `8eb1bd1b7` updates
`tests/test_payment_source_contract_api.py::test_manual_intent_uses_configured_api_key_not_app_dependency_override`
to install the override on `_APP_GET_API_KEY`.

Role: `pulseplate-premortem-risk-review`

Disposition: FIXED

Commit: `8eb1bd1b7`

Evidence: Premortem identified stale entitlement-header manual billing tests,
dependency-override auth regression risk, missing final local gates, and a
misleading test name. Commit `8eb1bd1b7` adds the guard, updates the tests,
runs the expanded billing group, and renames the misleading test.

Disposition: NOT-A-BUG

Evidence: Premortem noted that manual rail HTTP issuer derivation still follows
the existing transport-key contract. This PR intentionally does not redesign
operator/user attribution for manual rails; the PR body records that boundary
under Out of scope.

## Experiment Runner Evidence

Packet: `artifacts/orchestration/experiments/exp-f966e6c85a0b.json`

Artifact: `artifacts/orchestration/experiments/results/exp-f966e6c85a0b.json`

Status: accepted oracle-only reviewer result.

Co-author trailer: not required (`contribution_kind=none`).

## Post-Open Review Evidence

Role: `qa-engineer-agent`

Disposition: NOT-A-BUG

Evidence: Post-open QA reviewed the actual PR diff and found no actionable QA
defects. The review confirmed the canonical validator binding, strict
`API_KEY=test_key` manual headers, PRO/VIP rejection, dependency-override
negative coverage, and paid-route entitlement separation.

Role: `bug-hunter`

Disposition: NOT-A-BUG

Evidence: Post-open bug-hunter reviewed `manual-intent -> reconcile -> status`
issuer behavior and found no actionable runtime bug in the PR diff. Real
operator/user attribution for manual rails remains explicitly out of scope.

Role: `pulseplate-pr-review`

Disposition: FIXED

Commit: `63cf62d39`

Evidence: Dry-run report found only advisory governance items: missing mapping
artifact in head and diff size above the review-risk threshold. This artifact
closes the missing mapping artifact. The diff-size advisory is accepted as
NOT-A-BUG because the seven-file hotfix keeps one billing-auth failure mode and
its deterministic regression tests together; local `make validate-changed`,
focused pytest, expanded billing pytest, and pre-commit evidence are recorded
below.

Role: `security-auditor`

Disposition: FIXED

Commit: `63cf62d39`

Evidence: Post-open security review found no actionable auth or billing
security defect, and flagged one artifact-hygiene issue: a local absolute
Python path in the validation command. This artifact now uses the repo Python
resolver form instead of a machine-local absolute path.

Role: `Codex Security diff scan`

Disposition: NOT-A-BUG

Evidence: Scan `1bfc84fb-197c-4c90-bffa-25b98465f7a9` completed against
range `5ee821e13194825fac58497e2777b56028cf3bed..d5d855472a0692f736646fd306623dc78544b835`
with complete coverage and 0 reportable findings. The sealed report records:
manual RU/BY billing transport auth binds to `validate_app_api_key`, rejects
missing, blank, invalid, tier-key, and dependency-override bypass attempts,
and preserves fail-closed behavior.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/routers/billing.py --path tests/conftest.py --path tests/test_payment_reconciliation_api.py --path tests/test_payment_source_contract_api.py --path tests/test_subscription_activation_api.py`
- `python3 scripts/orchestration/check_preflight.py --mode execute --primary qa-engineer-agent --secondary bug-hunter --reviewer agent-coordinator --path app/routers/billing.py --path tests/conftest.py --path tests/guards/test_manual_billing_auth_contract_guard.py --path tests/test_paid_route_guards.py --path tests/test_payment_source_contract_api.py --path tests/test_payment_reconciliation_api.py --path tests/test_subscription_activation_api.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `VENV_PYTHON="$(. scripts/hooks/repo_python.sh; resolve_repo_python "$PWD")"; API_KEY=test_key APP_ENV=test ENVIRONMENT=test "$VENV_PYTHON" -m pytest -q tests/guards/test_manual_billing_auth_contract_guard.py tests/test_api_tiers_db_lookup.py tests/test_billing_openapi_contract.py tests/test_ios_receipt_verification_api.py tests/test_paid_route_guards.py tests/test_payments_activation_paywall_events.py tests/test_payment_reconciliation_api.py tests/test_payment_source_contract_api.py tests/test_payment_webhook_signature_api.py tests/test_pro_payments_openapi_contract.py tests/test_subscription_activation_api.py`
- `pre-commit run --all-files`
- `pre-commit run --hook-stage pre-push --files app/routers/billing.py`
- `make validate-changed`
- Pre-push hooks on `git push`: passed mypy, backend tests, Bandit, and Docker
  build.

Local full `make verify` was not run per repo machine-budget policy; GitHub CI
supplies the heavy full signal.

## Merge Readiness

- Local narrow bundle: complete.
- Current-head GitHub CI: pending after PR open.
- Post-open mandatory role review and `pulseplate-pr-review`: complete.
- Codex Security scan: complete, 0 reportable findings.
- Strict merge-readiness checks: pending.
