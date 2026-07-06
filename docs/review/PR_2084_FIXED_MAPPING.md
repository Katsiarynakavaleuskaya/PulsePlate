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
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `docs/contracts/API_CANONICAL_MAP.md:64`, `docs/contracts/API_CANONICAL_MAP.md:69`, `docs/contracts/API_CANONICAL_MAP.md:81`, `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md:19`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:194`, `tests/test_legacy_premium_nutrition_registration_bootstrap.py:211`
Reason: CodeRabbit requested deprecation/alias metadata for BMR, root targets, and gaps as if equivalent canonical PRO replacements existed. The current contract says to keep legacy routes legacy-compatible when no canonical target is documented; public OpenAPI still hides these paths, and source metadata is intentionally preserved by regression tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2084#pullrequestreview-4635219654

Disposition: NOT-A-BUG
Evidence: `tests/test_route_family_bootstrap.py:236`, `tests/test_route_family_bootstrap.py:270`, `tests/test_route_family_bootstrap.py:308`, `tests/test_route_family_bootstrap.py:346`, `tests/test_route_family_bootstrap.py:377`, `tests/test_route_family_bootstrap.py:404`
Reason: CodeRabbit suggested parametrizing the wrapper delegation tests as an optional maintainability nit. These tests intentionally keep each moved legacy premium wrapper explicit because the route contracts use different request DTOs, delegate targets, and public compatibility shapes; parametrizing them would add normalization indirection without reducing the production risk covered by the current tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2084#pullrequestreview-4636095985

## Implementation Evidence

Disposition: FIXED
Commit: 2ba707ffc0c0e9e96b3735540be11d90a218603c
Evidence: `app/routers/legacy_premium_nutrition.py:23`,
`app/main.py:455`, `app/main.py:1076`, `legacy_app.py:2980`,
`scripts/ci/check_legacy_growth_guard.py:94`,
`tests/test_legacy_premium_nutrition_registration_bootstrap.py:153`,
`tests/test_legacy_growth_guard.py:49`,
`docs/contracts/PRODUCT_TIER_MAP.md:90`

Disposition: FIXED
Commit: f542b38dee6be7908e89369e4abbe7be30ccd3a7
Evidence: `app/main.py:1340`, `app/main.py:1345`
Reason: Current-head CI found that the new legacy premium family changed the
first missing-API-key dependency failure from the existing plan-export family.
The follow-up commit preserves the prior bootstrap failure ordering while
keeping the new legacy premium family fail-closed.

Disposition: FIXED
Commit: 299af9e32b01ae76162a3dbd4a0c3b67331053ef
Evidence: `tests/test_legacy_premium_nutrition_registration_bootstrap.py:196`,
`tests/test_legacy_premium_nutrition_registration_bootstrap.py:212`,
`tests/test_legacy_premium_nutrition_registration_bootstrap.py:253`,
`tests/test_legacy_premium_nutrition_registration_bootstrap.py:339`
Reason: Codecov and CI diff coverage reported uncovered new legacy premium
wrapper and fail-closed lines. This follow-up commit adds direct delegation
coverage for all six moved wrappers plus the missing API key dependency branch
in the focused bootstrap suite.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2084#issuecomment-4892601123 -> 299af9e32b01ae76162a3dbd4a0c3b67331053ef

Disposition: FIXED
Commit: fd7c742ece3e01cbc90782b165a87ca33efa7a34
Evidence: `tests/test_route_family_bootstrap.py:236`,
`tests/test_route_family_bootstrap.py:270`,
`tests/test_route_family_bootstrap.py:308`,
`tests/test_route_family_bootstrap.py:346`,
`tests/test_route_family_bootstrap.py:377`,
`tests/test_route_family_bootstrap.py:404`,
`tests/test_route_family_bootstrap.py:438`
Reason: Current-head CI showed that `test-pr (3.13)` coverage artifacts are
generated from the selected `route_contract_safety` suite, which did not include
`tests/test_legacy_premium_nutrition_registration_bootstrap.py`. This follow-up
commit mirrors the wrapper/fail-closed coverage inside
`tests/test_route_family_bootstrap.py`, a suite already selected by the current
CI risk profile, without changing runtime behavior.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28791482277/job/85374712649 -> fd7c742ece3e01cbc90782b165a87ca33efa7a34

No review-thread URLs were mapped at PR open because no review threads existed.

## Role-Agent Evidence

- Lane packet: `artifacts/orchestration/task_packets/e4440b5e4f4c.json`
- Pre-open role order completed:
  `agent-coordinator -> qa-engineer-agent -> security-auditor -> bug-hunter`.
- Post-open role chain completed:
  `qa-engineer-agent -> bug-hunter -> security-auditor`.
- `pulseplate-pr-review` dry-run completed with one advisory large-diff note
  only; this was closed by split rationale plus targeted deterministic gates.

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
- `pytest -q tests/test_main_paywall_bootstrap.py::test_plan_export_route_registration_rejects_missing_api_key_dependency_symbol tests/test_main_paywall_bootstrap.py::test_plan_export_route_registration_rejects_missing_api_key_dependency tests/test_main_paywall_bootstrap.py::test_shoplist_export_route_registration_rejects_missing_api_key_dependency_symbol tests/test_main_paywall_bootstrap.py::test_shoplist_export_route_registration_rejects_missing_api_key_dependency tests/test_main_paywall_bootstrap.py::test_restaurant_moderation_route_registration_rejects_missing_api_key_dependency_symbol tests/test_legacy_premium_nutrition_registration_bootstrap.py` - PASS after `f542b38dee6be7908e89369e4abbe7be30ccd3a7`.
- `pre-commit run --all-files` - PASS before push.
- `pre-commit run --all-files` - PASS after `f542b38dee6be7908e89369e4abbe7be30ccd3a7`.
- Push hook - PASS, including pre-push pytest, full-repo Bandit, dependency
  audit, and Docker build test.
- `git diff --check` - PASS.
- Codex Security diff scan:
  `5ba56b71-1605-4562-8b6f-32b2083cc875` against
  `1eedc0baffe05c08c02b27a554f65e7f12636508..f542b38dee6be7908e89369e4abbe7be30ccd3a7`
  - PASS, 0 findings. Report:
  `/private/var/folders/bw/12x002vn67v2bvjpbhbtm8480000gn/T/codex-security-scans-9J0U2w/extract-legacy-premium-nutrition-routes/f542b38dee6be7908e89369e4abbe7be30ccd3a7_20260706T114311Z_27j279ov/report.md`.
- `python3 scripts/orchestration/pr_review_context.py --pr 2084 --output /tmp/pulseplate_pr_2084_review_context.json` - PASS.
- `python3 scripts/orchestration/pr_review_report.py --context /tmp/pulseplate_pr_2084_review_context.json --format markdown` - PASS.
- `python3 -m pytest tests/test_pr_review_report.py tests/test_pr_review_context.py -q` - PASS.
- `coverage run -m pytest -q tests/test_legacy_premium_nutrition_registration_bootstrap.py`
  plus `diff-cover /tmp/pr2084_coverage.xml --compare-branch origin/main --fail-under 97 ...`
  - PASS after `299af9e32b01ae76162a3dbd4a0c3b67331053ef`; diff coverage
  `app/main.py (100%)`, `app/routers/legacy_premium_nutrition.py (100%)`,
  total changed lines `49`, missing `0`, coverage `100%`.
- `coverage run -m pytest -q tests/test_route_family_bootstrap.py` plus
  `diff-cover /tmp/pr2084_route_family_coverage.xml --compare-branch origin/main --fail-under 97 ...`
  - PASS after `fd7c742ece3e01cbc90782b165a87ca33efa7a34`; diff coverage
  `app/main.py (100%)`, `app/routers/legacy_premium_nutrition.py (100%)`,
  total changed lines `49`, missing `0`, coverage `100%`.
- `pytest -q tests/test_route_family_bootstrap.py tests/test_legacy_premium_nutrition_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_pro_premium_contract_parity.py`
  - PASS after `fd7c742ece3e01cbc90782b165a87ca33efa7a34`.
- `make validate-changed` - PASS after
  `299af9e32b01ae76162a3dbd4a0c3b67331053ef`; selected
  `tests/test_legacy_growth_guard.py` and
  `tests/test_legacy_premium_nutrition_registration_bootstrap.py`.
- `pre-commit run --all-files` - PASS after
  `299af9e32b01ae76162a3dbd4a0c3b67331053ef`; first run reformatted the
  changed bootstrap test with Black, second run passed all hooks.

## Merge Readiness

Not claimed here. Requires current-head GitHub CI after the latest pushed
commit, strict merge-readiness gate, bot review dispositions, and resolved
review threads.
