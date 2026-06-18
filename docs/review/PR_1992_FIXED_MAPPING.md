# PR 1992 Fixed Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1992

Branch: `codex/add-production-runtime-invariant-guards`

## Summary

This PR adds fail-closed production runtime invariant guards for existing
security posture assumptions without dependency updates, legacy extraction,
OpenAPI changes, FoodDB/data migration, auth rewrite, frontend, iOS, or macOS
runtime changes.

## Operator Exceptions

- Full local `make verify` was not run under the operator-approved
  machine-heavy exception.
- Validation uses focused local gates, `make validate-changed`,
  `pre-commit run --all-files`, pre-push hooks, and current-head GitHub CI as
  the heavy signal.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py` -> PASS
- `python3 scripts/orchestration/check_agent_consistency.py` -> PASS
- `.venv/bin/python -m pytest -q tests/test_production_runtime_invariants.py tests/guards/test_security_devtooling_regression_guards.py tests/test_pro_session_cookie_auth.py tests/test_app_lifespan_additional.py tests/test_plan_export_additional.py tests/test_python_supply_chain_controls.py tests/test_app_public_surface.py tests/test_app_openapi_coverage.py tests/test_app_creation_coverage.py tests/test_openapi_namespace_guards.py tests/test_app_endpoints_combined.py` -> PASS
- `.venv/bin/python scripts/ci/check_production_runtime_invariants.py --synthetic-production` -> PASS
- `.venv/bin/python -m mypy app/security/production_invariants.py app/security/rate_limit.py app/security/web_session.py app/bootstrap/startup_guards.py scripts/ci/check_production_runtime_invariants.py` -> PASS
- `make validate-changed` -> PASS; selected changed Python tests after commit
- `pre-commit run --all-files` -> PASS
- pre-push hooks -> PASS, including changed-file mypy, pip-audit, pre-push
  backend tests, full-repo Bandit, and docker build test

## Premortem

Artifact: `docs/review/PRODUCTION_RUNTIME_INVARIANTS_PREMORTEM.md`

Dispositions:

- False-green startup/workflow guard risk: FIXED
  - Evidence: `app/bootstrap/startup_guards.py`
  - Evidence: `tests/test_production_runtime_invariants.py`
  - Evidence: `tests/guards/test_security_devtooling_regression_guards.py`
- Readiness guard mutation / malformed DB URL risk: FIXED
  - Evidence: `app/security/rate_limit.py`
  - Evidence: `app/security/production_invariants.py`
  - Evidence: `tests/test_production_runtime_invariants.py`
- Export placeholder hidden assumption risk: FIXED
  - Evidence: `app/security/production_invariants.py`
  - Evidence: `tests/test_production_runtime_invariants.py`

## Experiment Runner

Packet: `artifacts/orchestration/experiments/production-runtime-invariants-oracle.json`

Result: `artifacts/orchestration/experiments/results/production-runtime-invariants-oracle-result.json`

Disposition: ACCEPTED

Evidence:

- Oracle 1 focused pytest -> PASS
- Oracle 2 synthetic production invariant script -> PASS
- Oracle 3 focused mypy -> PASS

Attribution:

- Commit `f45139cfb` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the
  accepted oracle-only result materially shaped validation and commit decision.

## Discussion Thread Pass

No review threads existed at PR open.

Post-open governance still required:

- `qa-engineer-agent`
- `bug-hunter`
- `security-auditor`
- Codex Security diff scan when available
- CodeRabbit when authenticated
- `pulseplate-pr-review`

## Fixed in Commit Mapping

- Initial implementation: `f45139cfb`
  - Evidence: `app/security/production_invariants.py`
  - Evidence: `app/security/rate_limit.py`
  - Evidence: `app/security/web_session.py`
  - Evidence: `app/bootstrap/startup_guards.py`
  - Evidence: `scripts/ci/check_production_runtime_invariants.py`
  - Evidence: `.github/workflows/ci.yml`
  - Evidence: `.github/workflows/security.yml`
  - Evidence: `tests/test_production_runtime_invariants.py`

## Deferred / Follow-Ups

- Existing default-branch Dependabot alerts are not claimed closed by this PR.
- Torch/RAG alert handling remains separate and upstream-blocked unless a
  patched torch release appears or the optional vector profile is retired.

## Merge Readiness

Status: NOT READY at artifact creation.

Required before merge:

- Current-head PR CI parity.
- No unresolved actionable human or bot review comments.
- Post-open role passes and security review complete.
- Strict merge-readiness with auth.
- Mandatory wait-window after latest review/bot activity.
