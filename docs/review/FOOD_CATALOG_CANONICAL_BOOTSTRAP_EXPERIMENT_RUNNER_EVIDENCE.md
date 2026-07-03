# Food/Catalog Canonical Bootstrap Experiment Runner Evidence

Branch: `codex/move-food-catalog-registration-to-canonical-bootstrap`

Mode: `oracle_only_governance_reviewer`

## Zero-Network Attempt

- Experiment ID: `exp-7b394904754b`
- Result artifact:
  `artifacts/orchestration/experiments/results/exp-7b394904754b-rerun.json`
- Status: `rejected`
- Failure class: `infra_flake`
- Runner error: `Network-disabled sandbox requires unshare on PATH`
- Oracle commands executed: `0`

Disposition: local infrastructure blocker. This macOS host does not provide
Linux `unshare`, so the zero-network sandbox could not execute any oracle
command.

## Review-Required Fallback

- Experiment ID: `exp-e539da8b2f47`
- Packet:
  `artifacts/orchestration/experiments/exp-food-catalog-registration-macos-oracle.json`
- Result artifact:
  `artifacts/orchestration/experiments/results/exp-food-catalog-registration-oracle-review-result.json`
- Status: `accepted`
- Failure class: `null`
- Runner mode: `oracle_only_governance_reviewer`
- Network budget: `1`
- Shared tree untouched: `true`
- Contribution kind: `oracle_review`
- Co-author required: `true`
- Evidence commit: `e91828e2e607727ca7e85d133ea6ef77ad91d0f1`
- Evidence commit trailer:
  `Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>`

The accepted fallback used the same oracle-only governance intent and an
explicit nonzero network budget to avoid the local `unshare` blocker. It is
review-required evidence and does not replace local gates, current-head CI,
post-open role passes, Codex Security, `pulseplate-pr-review`, or
merge-readiness checks.

Any squash or landing commit that carries this oracle-shaped evidence must
preserve the same co-author trailer.

## Oracle Commands

All fallback oracle commands returned `0`:

- `python -m pytest -q tests/test_food_catalog_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/test_metrics.py::test_metrics_include_food_catalog_route_templates`
- `python scripts/ci/check_legacy_growth_guard.py`

## Decision

Use `exp-e539da8b2f47` as the pre-open Experiment Runner oracle-only evidence
for this PR, with the local zero-network infrastructure limitation disclosed.
