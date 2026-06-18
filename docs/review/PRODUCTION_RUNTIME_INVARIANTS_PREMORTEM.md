# Production Runtime Invariants Premortem

Mode: `pr-premortem`

Skill: `pulseplate-premortem-risk-review`

Packet: `artifacts/orchestration/task_packets/3112b85f242c.json`

Frame: It is 48 hours from now. This security guard PR made things worse. We are
looking backward to understand why.

## Summary

This PR adds fail-closed production/staging runtime invariant guards for
security posture, rate limiting, private exports, secure cookies, and synthetic
CI verification.

## Most Likely Failure

The most likely failure is a false-green guard caused by tests exercising only
the synthetic helper while startup behavior or workflow wiring drifts. The PR
closes this by calling `assert_production_runtime_invariants()` from
`run_startup_guards()`, adding workflow-contract tests for both security
workflows, and covering the startup wiring directly.

Disposition: FIXED

Evidence:

- `app/bootstrap/startup_guards.py`
- `tests/test_production_runtime_invariants.py::test_startup_guards_call_production_invariants`
- `tests/guards/test_security_devtooling_regression_guards.py::test_security_workflows_run_production_runtime_invariant_guard`

## Most Dangerous Failure

The most dangerous failure is accidentally weakening production protections by
making a readiness assertion mutate shared limiter state or accept malformed
production DB URLs. That would let CI repair unsafe runtime state instead of
proving it is safe. The PR closes this with read-only rate-limit readiness,
PostgreSQL URL validation, and explicit regression tests.

Disposition: FIXED

Evidence:

- `app/security/rate_limit.py`
- `app/security/production_invariants.py`
- `tests/test_production_runtime_invariants.py::test_rate_limit_readiness_does_not_mutate_limiter_state`
- `tests/test_production_runtime_invariants.py::test_production_runtime_invariants_reject_non_postgres_database_url`

## Hidden Assumption

The hidden assumption was that existing settings helpers enforce every
production-like mode consistently. They already cover explicit production,
prod, and staging, but the new guard treats unknown runtime labels with
`DEBUG=false` as production-like too. The PR closes this by enforcing export
secret placeholders inside the production invariant layer itself.

Disposition: FIXED

Evidence:

- `app/security/production_invariants.py`
- `tests/test_production_runtime_invariants.py::test_production_runtime_invariants_reject_export_secret_placeholder_for_unknown_prod_like_env`

## Pre-Merge Checklist

- Run coordinator bootstrap and role order from packet `3112b85f242c`.
- Run focused invariant, workflow, lifespan, cookie, and export tests.
- Run `scripts/ci/check_production_runtime_invariants.py --synthetic-production` through repo Python.
- Run `make validate-changed` and `pre-commit run --all-files`.
- Open non-draft PR and create `docs/review/PR_<N>_FIXED_MAPPING.md`.
- Run post-open QA, bug-hunter, security-auditor, Codex Security diff scan, and `pulseplate-pr-review`.

## Decision

`proceed with changes` before implementation; all identified premortem changes
are now fixed in code, tests, or workflow guards before PR open.
