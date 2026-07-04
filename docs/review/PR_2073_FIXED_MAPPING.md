# PR 2073 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073

Branch: `codex/move-recipe-nutrition-reference-registration-to-canonical-bootstrap`

## Summary

This PR moves recipe and FREE nutrition-reference route registration ownership
from `legacy_app.py` to canonical `app/main.py` bootstrap while preserving
runtime behavior, source route visibility, final public OpenAPI filtering,
auth/tier posture, nutrition formula behavior, recipe-store behavior, and
generated client artifacts.

## Scope

- Add static route specs for `recipes_router` and
  `nutrition_recommendations_router`.
- Register both routers through canonical route-family bootstrap in
  `app/main.py`.
- Remove only those two router imports/includes from `legacy_app.py`.
- Tighten legacy-growth guard allowlists and regression tests.
- Update backend routing map and attach premortem / Experiment Runner evidence.

## Out Of Scope

BOLA/authz expansion, BMI/users/restaurants ownership, premium nutrition
handlers, middleware/lifespan behavior, recipe-store changes, nutrition formula
changes, OpenAPI/client contract changes, frontend/iOS/macOS changes, and full
local `make verify`.

## Lane Start Provenance

- Base branch: `main`
- Branch:
  `codex/move-recipe-nutrition-reference-registration-to-canonical-bootstrap`
- Pre-open packet: `artifacts/orchestration/task_packets/3467351ee456.json`
- Post-open review packet:
  `artifacts/orchestration/task_packets/f5cb9acbe485.json`
- Pre-edit role order executed:
  `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`
- Packet creation was treated as routing/provenance only. Role passes were
  executed explicitly before implementation.

## Discussion Thread Pass

- [x] Fixed in commit mapping artifact created after GitHub assigned PR number
  `#2073`.
- [x] Post-open `qa-engineer-agent` pass completed.
- [x] Post-open `bug-hunter` pass completed; three P2 findings fixed in
  `8d50f28c1`.
- [x] Post-open `security-auditor` pass completed.
- [x] Codex Security diff scan / finding discovery completed for
  `191a2a317a42b6b7cc255e0011affedfe74e4435`.
- [x] `pulseplate-pr-review` completed for
  `191a2a317a42b6b7cc255e0011affedfe74e4435`; one advisory large-diff planning
  note dispositioned below.
- [ ] CodeRabbit actionable review comments checked and dispositioned.
- [ ] Sourcery actionable review comments checked and dispositioned.
- [ ] Cubic actionable review comments checked and dispositioned.
- [x] Discussion-thread pass completed.

## Fixed in Commit Mapping

No GitHub review threads or actionable bot comments existed when this artifact
was created. The post-open `bug-hunter` role pass found three P2 actionables;
they are dispositioned below.

Disposition: FIXED
Commit: 8d50f28c1
Evidence: `app/bootstrap/route_family.py` now rejects existing static-family
registrations whose FastAPI route order differs from source route order;
`tests/test_main_paywall_bootstrap.py` covers generic order drift, and
`tests/test_recipe_nutrition_reference_registration_bootstrap.py` covers
`/api/v1/recipes/search` before `/api/v1/recipes/{recipe_id}`.
Reason: Prevents a complete preexisting family from passing membership checks
while shadowing `/api/v1/recipes/search` through `/{recipe_id}`.

Disposition: FIXED
Commit: 8d50f28c1
Evidence:
`docs/review/RECIPE_NUTRITION_REFERENCE_CANONICAL_BOOTSTRAP_EXPERIMENT_RUNNER_EVIDENCE.md`
now records the rejected zero-network attempt as an unpromoted infra caveat
without presenting a duplicated artifact path as review evidence.
Reason: Keeps Experiment Runner evidence locatable and avoids promoting a
rejected local infra-flake artifact.

Disposition: FIXED
Commit: 8d50f28c1
Evidence: `tests/test_recipe_nutrition_reference_registration_bootstrap.py`
asserts the JSON `Content-Type` before parsing the recipe search response.
Reason: Aligns the new bootstrap test with `tests/AGENTS.md` JSON response
assertion policy.

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` dry-run report found one advisory
large-diff planning note because the diff exceeded the 800-line review-risk
threshold; scope remains a bounded route-registration migration plus the
bug-hunter route-order guard fix, and focused gates covered the changed
surfaces: recipes/nutrition behavior tests, bootstrap/guard/OpenAPI/auth-tier
tests, `check_legacy_growth_guard.py`, targeted mypy, `make openapi-check`,
`pre-commit run --all-files`, `make validate-changed`, and pre-push hooks.
Reason: The threshold is review-planning evidence, not a code/security defect.
The PR was intentionally kept to one legacy-removal family plus the directly
required shared route-order guard.

## Review Comment Dispositions

No GitHub review comments have been dispositioned yet.

### Advisory PulsePlate PR Review Note

Disposition: NOT-A-BUG
Evidence: `pulseplate-pr-review` reported only the large-diff planning note
described in `Fixed in Commit Mapping`; no deterministic correctness,
security, architecture, QA, wellness, release, or governance code finding was
reported.
Reason: The PR owns one bounded legacy-removal slice and the targeted
bug-hunter fix required to keep that slice fail-closed.

## Experiment Runner Evidence

- Artifact:
  `artifacts/orchestration/experiments/results/recipe-nutrition-reference-oracle-result-v2.json`
- Experiment id: `exp-4fe6753a1339`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer:
  `ac08b4b6f4e241c18b62e24dbc90db027e78d985`

Infra caveat: the first zero-network local attempt recorded
`status=rejected`, `failure_class=infra_flake` because this development host
does not provide `unshare` for the network-disabled sandbox. The accepted
`network_budget=1` artifact kept the same local oracle commands and does not
grant product runtime, provider, client, or public API authority.

## Validation Evidence

- `python scripts/orchestration/check_preflight.py` - PASS, with existing
  private-index env warning only.
- `python scripts/orchestration/check_agent_consistency.py` - PASS.
- `python -m pytest -q tests/test_recipes_api.py tests/test_recipe_preview.py tests/test_nutrition_recommendations_api.py` - PASS.
- `python -m pytest -q tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py` - PASS.
- `python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `python -m mypy app/main.py app/routers/recipes.py app/routers/nutrition_recommendations.py scripts/ci/check_legacy_growth_guard.py` - PASS.
- `DEV_PYTHON=.venv/bin/python make openapi-check` - PASS.
- `git diff --exit-code -- frontend/src/api/openapi.json frontend/src/api/schema.ts` - PASS.
- `pre-commit run --all-files` - PASS after Black formatted the new bootstrap
  test and the affected tests were rerun.
- `make validate-changed` - PASS after commit; selected
  `tests/test_legacy_growth_guard.py` and
  `tests/test_recipe_nutrition_reference_registration_bootstrap.py`.
- Pre-push hooks - PASS: mypy changed files, pip-audit, backend pytest
  pre-push, full-repo Bandit, docker build test.
- Bug-hunter fix validation:
  `python -m pytest -q tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_main_paywall_bootstrap.py::test_route_family_rejects_existing_route_order_drift`
  - PASS.
- Bug-hunter focused bundle:
  `python -m pytest -q tests/test_recipes_api.py tests/test_recipe_preview.py tests/test_nutrition_recommendations_api.py tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_main_paywall_bootstrap.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py`
  - PASS.
- Bug-hunter fix `python scripts/ci/check_legacy_growth_guard.py` - PASS.
- Bug-hunter fix `DEV_PYTHON=.venv/bin/python make openapi-check` - PASS.
- Bug-hunter fix `pre-commit run --all-files` - PASS after Black formatted
  `app/bootstrap/route_family.py` and affected tests were rerun.
- Codex Security diff scan:
  scan `08025660-053e-4a39-bb72-73277fe7c22f` completed with 0 findings and
  6/6 coverage rows closed for
  `8fdcd0ac1668f612de4dca90846fd994967e60df..191a2a317a42b6b7cc255e0011affedfe74e4435`.
- `pulseplate-pr-review`:
  `/tmp/pr2073_pulseplate_pr_review.md` completed; one advisory large-diff note
  dispositioned as NOT-A-BUG above.

## Merge Readiness

Not claimed here. Requires current-head CI after the latest mapping/body commit,
post-open role chain, Codex Security / review-bot pass, discussion-thread
disposition, strict merge-readiness gate, and resolved review threads.
