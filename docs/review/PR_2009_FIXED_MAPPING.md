# PR #2009 - Fixed in Commit Mapping SoT

## Scope

Move PRO and VIP route registration ownership from `legacy_app.py` to canonical
`app/main.py` bootstrap without public API, auth, OpenAPI, generated-client, DB,
frontend, iOS, billing, entitlement, AI, FoodDB, or route-handler drift.

## Implementation Commit

- `afa840d50e00ae5b457b50c00321c8fcee7eeb2e` - move paid-tier registration
  ownership into canonical bootstrap and preserve legacy compatibility attrs.

## Discussion Thread Pass

Status: Opened PR; no actionable human or bot review threads were present at
artifact creation time.

## Fixed in Commit Mapping

- No actionable review comments at PR open.

## Governance Evidence

- Worktree isolation: branch
  `codex/move-paid-tier-registration-to-canonical-bootstrap` in
  `worktrees/move-paid-tier-registration-to-canonical-bootstrap`.
- Preflight:
  `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path scripts/ci/check_legacy_growth_guard.py`
  passed.
- Agent consistency:
  `python3 scripts/orchestration/check_agent_consistency.py` passed.
- Role dispatch packet:
  `artifacts/orchestration/task_packets/e2fbda40b04e.json` (local artifact).
- Role pass order completed: `agent-coordinator`, `architecture-specialist`,
  `backend-engineer`, `security-auditor`, `qa-engineer-agent`.
- Premortem against actual diff: risks were double registration, compatibility
  attr drift, OpenAPI/client drift, and empty-selector validation false
  confidence; all are covered by code removal, focused tests, OpenAPI diff
  check, and post-commit `make validate-changed`.
- Experiment Runner oracle-only evidence:
  `artifacts/orchestration/experiments/results/paid-tier-registration-ownership-oracle-result.json`
  (local artifact), experiment `exp-756e43207b6d`, status `accepted`,
  `mutated_paths=[]`, shared tree untouched.
- Experiment Runner attribution: implementation commit includes
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>` because the
  accepted oracle-only evidence shaped the commit decision.

## Local Validation

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path app/main.py --path legacy_app.py --path scripts/ci/check_legacy_growth_guard.py`
  - PASS
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS
- `python3 scripts/ci/check_legacy_growth_guard.py` - PASS
- `pytest -q tests/test_main_paywall_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_registration_router_coverage.py tests/vip/test_vip_diff_coverage.py`
  - PASS
- `pytest -q tests/test_pro_vip_route_dependency_guard.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_bola_contract_pack.py`
  - PASS
- `pytest -q tests/test_env_guards.py tests/test_app_public_surface.py tests/test_openapi_determinism.py tests/test_pro_premium_contract_parity.py tests/edges/test_premium_week_edges.py`
  - PASS
- `make openapi-check` - PASS
- `git diff --exit-code -- app/static/openapi.json frontend/src/api/openapi.json frontend/src/api/schema.ts`
  - PASS
- `make validate-changed` - PASS after commit; selected
  `tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py`
- `pre-commit run --all-files` - PASS
- `git diff --check` - PASS
- Pre-push hooks - PASS: changed-file mypy, pip-audit, backend tests, full
  Bandit, docker build test.

Full local `make verify` was intentionally not run per operator machine-budget
constraint for this narrow lane. This PR is not merge-ready until focused local
gates, current-head CI parity, post-open role review, Codex Security diff
scan/finding discovery, CodeRabbit/Sourcery/Cubic disposition, review-thread
mapping, and strict merge-readiness checks all support it.

## Post-Open Requirements

- [ ] Current-head CI parity reviewed.
- [ ] Post-open `qa-engineer-agent -> bug-hunter -> security-auditor` pass.
- [ ] Codex Security diff scan / finding discovery.
- [ ] `pulseplate-pr-review`.
- [ ] CodeRabbit/Sourcery/Cubic comments checked and dispositioned.
- [ ] Strict merge-readiness wrapper run with current-head evidence.
