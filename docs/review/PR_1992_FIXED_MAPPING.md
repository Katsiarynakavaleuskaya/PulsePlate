# PR 1992 Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1992

Branch: `codex/add-production-runtime-invariant-guards`

## Summary

This PR adds fail-closed production runtime invariant guards for existing
security posture assumptions without dependency updates, legacy extraction,
OpenAPI changes, FoodDB/data migration, auth rewrite, frontend, iOS, or macOS
runtime changes.

## Scope

- Add `app/security/production_invariants.py` for production/staging posture checks.
- Add production fail-closed rate-limit readiness checks in
  `app/security/rate_limit.py`.
- Wire startup guards through `app/bootstrap/startup_guards.py` and pass the
  serving FastAPI app from `legacy_app.py`.
- Align secure-cookie production detection in `app/security/web_session.py`.
- Add synthetic CI coverage, focused tests, and security evidence.

## Out Of Scope

Dependency updates, RAG/vector/torch alert handling, legacy route extraction,
FoodDB/data migration, entitlement/auth architecture rewrite, OpenAPI changes,
frontend, iOS, macOS, pyproject/uv migration, and runtime feature behavior.

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
- `make validate-changed` -> PASS
- `pre-commit run --all-files` -> PASS
- Pre-push hooks -> PASS, including changed-file mypy, pip-audit, pre-push
  backend tests, full-repo Bandit, and docker build test

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/3112b85f242c.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Pre-open role order executed:
  `agent-coordinator -> security-auditor -> backend-engineer -> qa-engineer-agent -> bug-hunter -> architecture-specialist`
- Post-open role order executed:
  `qa-engineer-agent -> bug-hunter -> security-auditor -> Codex Security diff scan -> pulseplate-pr-review`

## Premortem

Artifact: `docs/review/PRODUCTION_RUNTIME_INVARIANTS_PREMORTEM.md`

Disposition summary:

- False-green startup/workflow guard risk: FIXED.
- Readiness guard mutation / malformed DB URL risk: FIXED.
- Export placeholder hidden assumption risk: FIXED.

Evidence: `app/bootstrap/startup_guards.py`,
`app/security/production_invariants.py`, `app/security/rate_limit.py`,
`tests/test_production_runtime_invariants.py`, and
`tests/guards/test_security_devtooling_regression_guards.py`.

## Experiment Runner Evidence

- Packet: `artifacts/orchestration/experiments/production-runtime-invariants-oracle.json`
- Artifact:
  `artifacts/orchestration/experiments/results/production-runtime-invariants-oracle-result.json`
- Status: accepted.
- Oracle evidence: focused pytest passed, synthetic production invariant script
  passed, and focused mypy passed.
- Attribution: commit `f45139cfb` includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the
  accepted oracle-only result materially shaped validation and commit decision.

## Post-Open Review Evidence

- `qa-engineer-agent`: FIXED valid app-wiring coverage and synthetic flag-drift
  findings in `8c7e51f37`.
- `bug-hunter`: FIXED app-wiring false-green risk in `828fcbc0e`.
- `security-auditor`: FIXED global marker vs app-specific wiring risk in
  `a8bffffe7`.
- `pulseplate-pr-review`: NOT-A-BUG for large-diff advisory note. The scope is
  bounded to one coordinator-owned production invariant lane, and
  `make validate-changed` passed.
- Codex Security diff scan: PASS / no reportable findings. Report directory:
  `/tmp/codex-security-scans/BMI-App_2025_clean/0b7fdef76_20260618T120841Z`.
- CodeRabbit: two actionable findings fixed and resolved; see canonical mapping
  entries below.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

All actionable review threads are recorded below with disposition and proof
before resolution.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 43c116bc4
Evidence: `tests/test_production_runtime_invariants.py::test_synthetic_production_invariant_ci_checks`
Evidence: `.venv/bin/python -m pytest -q tests/test_production_runtime_invariants.py` -> PASS
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1992#discussion_r3435535472 -> 43c116bc4

Disposition: FIXED
Commit: b2ea2e419
Evidence: `app/security/rate_limit.py`
Evidence: `.venv/bin/python -m pytest -q tests/test_production_runtime_invariants.py` -> PASS
Evidence: `.venv/bin/python -m mypy app/security/rate_limit.py` -> PASS
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1992#discussion_r3435660191 -> b2ea2e419

## Deferred / Follow-Ups

- Existing default-branch Dependabot alerts are not claimed closed by this PR.
- Torch/RAG alert handling remains separate and upstream-blocked unless a
  patched torch release appears or the optional vector profile is retired.

## Merge Readiness

Status: NOT READY while current-head PR CI is pending or failing.

Required before merge:

- Current-head PR CI parity.
- No unresolved actionable human or bot review comments.
- Strict merge-readiness with auth.
- Mandatory wait-window after latest review/bot activity.
