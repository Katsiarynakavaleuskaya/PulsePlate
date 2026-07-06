# PR 2084 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2084

Branch: `codex/extract-legacy-premium-nutrition-routes`

## Summary

This PR moves six legacy premium nutrition POST route registrations from
`legacy_app.py` into `app/routers/legacy_premium_nutrition.py`, with canonical
registration from `app/main.py` through `ensure_route_family_registered(...)`.
It preserves existing behavior, including the historical public route shape of
`/premium_bmr`, and does not move weekly premium aliases.

## Discussion Thread Pass

- [x] Discussion-thread pass completed at PR open
- [x] Fixed in commit mapping created for PR number allocation
- No GitHub review threads existed when this artifact was created.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 2ba707ffc0c0e9e96b3735540be11d90a218603c
Evidence: `app/routers/legacy_premium_nutrition.py:23`,
`app/main.py:452`, `app/main.py:1073`, `legacy_app.py:2977`,
`scripts/ci/check_legacy_growth_guard.py:94`,
`tests/test_legacy_premium_nutrition_registration_bootstrap.py:153`,
`tests/test_legacy_growth_guard.py:49`,
`docs/contracts/PRODUCT_TIER_MAP.md:90`

No review-thread URLs were mapped at PR open because no review threads existed.

## Role-Agent Evidence

- Lane packet: `artifacts/orchestration/task_packets/e4440b5e4f4c.json`
- Pre-open role order completed:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> bug-hunter`.
- Post-open role chain is pending and must update this artifact if actionable
  findings appear.

## Premortem Evidence

- Artifact:
  `artifacts/orchestration/premortem/extract-legacy-premium-nutrition-routes-premortem.md`
- Result: all findings closed by code, tests, or contract documentation in the
  current diff.

## Experiment Runner Evidence

- Packet:
  `artifacts/orchestration/experiments/extract-legacy-premium-nutrition-routes-oracle-packet-net1.json`
- Artifact:
  `artifacts/orchestration/experiments/results/extract-legacy-premium-nutrition-routes-oracle-result-net1.json`
- Experiment id: `exp-323cca1b0764`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer:
  `2ba707ffc0c0e9e96b3735540be11d90a218603c`
- Oracle commands passed:
  - `pytest -q tests/test_legacy_premium_nutrition_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_premium_contract_parity.py tests/test_premium_bmr_api.py tests/test_premium_targets_422_edge_cases_simple.py tests/test_premium_targets_es_snapshots.py tests/test_route_family_bootstrap.py tests/test_pro_contracts_bootstrap.py tests/security/test_api_authz_contract_static.py tests/security/test_api_auth_tier_contract_pack.py`
  - `python scripts/ci/check_legacy_growth_guard.py`

Infra caveat: the first zero-network local attempt recorded `status=rejected`
because this macOS development host did not provide `unshare` for the
network-disabled sandbox. The accepted `network_budget=1` artifact kept local
oracle commands and does not grant product runtime, provider, client,
dependency installer, or public API authority.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --mode analyze --path ...` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `pytest -q tests/test_legacy_premium_nutrition_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_premium_contract_parity.py tests/test_premium_bmr_api.py tests/test_premium_targets_422_edge_cases_simple.py tests/test_premium_targets_es_snapshots.py tests/test_route_family_bootstrap.py tests/test_pro_contracts_bootstrap.py tests/security/test_api_authz_contract_static.py tests/security/test_api_auth_tier_contract_pack.py` - PASS.
- `pytest -q tests/test_plate_targets_integration.py tests/test_enhanced_plate_api.py tests/test_premium_targets_i18n_es.py tests/test_targeted_coverage.py tests/test_app_lines_3304_3315.py tests/test_app_plate_helpers.py tests/test_app_plate_fiber_fallback.py tests/test_app_branching_and_errors.py tests/test_legacy_app_diff_coverage.py::test_premium_bmr_resolve_wrapper_prefers_patched_app tests/test_legacy_app_diff_coverage.py::test_premium_bmr_resolve_wrapper_uses_pkg_candidates tests/test_legacy_app_diff_coverage.py::test_premium_bmr_legacy_executes_wrapper_resolution tests/test_legacy_app_diff_coverage.py::test_premium_bmr_legacy_hits_globals_fallback_path` - PASS.
- `python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `make openapi-check` with repo `DEV_PYTHON`/`VENV_PYTHON` - PASS.
- `pytest -q tests/test_openapi_namespace_guards.py tests/test_openapi_determinism.py` - PASS.
- `make validate-changed` - PASS after commit; selected
  `tests/test_legacy_growth_guard.py` and
  `tests/test_legacy_premium_nutrition_registration_bootstrap.py`.
- `pre-commit run --all-files` - PASS before push.
- Push hook - PASS, including pre-push pytest, full-repo Bandit, dependency
  audit, and Docker build test.
- `git diff --check` - PASS.

## Merge Readiness

Not claimed here. Requires current-head CI after the latest governance/body
commit, strict merge-readiness gate, post-open role chain completion, Codex
Security diff scan/finding discovery when available, `pulseplate-pr-review`,
bot review dispositions, and resolved review threads.
