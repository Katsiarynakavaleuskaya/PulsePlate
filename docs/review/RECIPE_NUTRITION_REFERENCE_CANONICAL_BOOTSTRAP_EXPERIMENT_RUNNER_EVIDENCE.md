# Recipe/Nutrition Reference Canonical Bootstrap Experiment Runner Evidence

Target branch:
`codex/move-recipe-nutrition-reference-registration-to-canonical-bootstrap`

Raw Experiment Runner JSON artifacts remain local and gitignored:

- Packet:
  `artifacts/orchestration/experiments/recipe-nutrition-reference-oracle-v2.json`
- Result:
  `artifacts/orchestration/experiments/results/recipe-nutrition-reference-oracle-result-v2.json`

## Result

- Experiment id: `exp-4fe6753a1339`
- Runner mode: `oracle_only_governance_reviewer`
- Status: `accepted`
- Failure class: `None`
- Mutated paths: `[]`
- Shared tree untouched: `true`
- Contribution kind: `oracle_review`
- Co-author required: `true`

The accepted oracle result applied the current branch diff for:

- `app/main.py`
- `app/routers/nutrition_recommendations.py`
- `app/routers/recipes.py`
- `docs/architecture/backend_routing_map.md`
- `legacy_app.py`
- `scripts/ci/check_legacy_growth_guard.py`
- `tests/test_legacy_growth_guard.py`
- `tests/test_recipe_nutrition_reference_registration_bootstrap.py`

## Oracle Commands

1. `python -m pytest -q tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`
   - Result: PASS
   - Evidence summary: pytest completed with returncode `0`.
2. `python scripts/ci/check_legacy_growth_guard.py`
   - Result: PASS
   - Evidence summary: `legacy compatibility seam guard passed`.

## Infra Caveat

The first zero-network local attempt wrote:

- Result:
  `artifacts/orchestration/experiments/results/artifacts/orchestration/experiments/results/exp-recipe-nutrition-reference-zero-network-result.json`
- Status: `rejected`
- Failure class: `infra_flake`
- Runner error: network-disabled sandbox requires `unshare` on PATH.

The accepted `network_budget=1` artifact keeps the same local oracle intent and
does not grant product runtime, provider, client, or public API authority. It
only avoids an unavailable OS-level network sandbox on this development host.

## Attribution

The Experiment Runner oracle-only evidence shaped validation and PR evidence for
this route-ownership migration. The implementation commit must include:

```text
Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
```
