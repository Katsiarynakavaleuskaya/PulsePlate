# PR 2073 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073

Branch: `codex/move-recipe-nutrition-reference-registration-to-canonical-bootstrap`

## Summary

This PR moves recipe and FREE nutrition-reference route registration ownership
from `legacy_app.py` to canonical `app/main.py` bootstrap while preserving
runtime behavior, source route visibility, final public OpenAPI filtering,
auth/tier posture, nutrition formula behavior, recipe-store behavior, and
generated client artifacts.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [x] Fixed mapping artifact created after GitHub assigned PR number `#2073`.
- [x] Pre-edit role order completed: `agent-coordinator -> backend-engineer -> qa-engineer-agent -> bug-hunter -> security-auditor -> architecture-specialist`.
- [x] Post-open role chain completed: `qa-engineer-agent -> bug-hunter -> security-auditor`.
- [x] Post-open bug-hunter findings fixed and re-reviewed.
- [x] Codex Security diff scan / finding discovery completed for latest security-relevant head 55b527d22325ca655e66e8507edea6c15b48bb56; later changes only record scan evidence.
- [x] `pulseplate-pr-review` completed; advisory large-diff note dispositioned below.
- [x] Codex review actionable comments checked and dispositioned below.
- [x] CodeRabbit actionable review comments checked and dispositioned below.
- [x] Sourcery actionable review comments checked and dispositioned below.
- [x] Cubic actionable review comments checked; generated summary only.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 8d50f28c1
Evidence: docs/review/RECIPE_NUTRITION_REFERENCE_CANONICAL_BOOTSTRAP_EXPERIMENT_RUNNER_EVIDENCE.md:46 records the rejected zero-network attempt without the duplicated artifact path, and tests/test_recipe_nutrition_reference_registration_bootstrap.py:183 asserts JSON Content-Type before response.json().
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523323769 -> 8d50f28c1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523323772 -> 8d50f28c1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#pullrequestreview-4629721797 -> 8d50f28c1

Disposition: FIXED
Commit: 111cc0f77e2ee1b849c92555e85422bb74b39a2e
Evidence: docs/review/PR_2073_FIXED_MAPPING.md now checks the required Discussion-thread pass item and removed the duplicate unchecked security-auditor row.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#pullrequestreview-4629760831 -> 111cc0f77e2ee1b849c92555e85422bb74b39a2e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#pullrequestreview-4629802649 -> 111cc0f77e2ee1b849c92555e85422bb74b39a2e

Disposition: FIXED
Commit: c6b6fe41bf45317e607cf9e017ecb662c33aef8a
Evidence: app/main.py:1208 registers recipe/nutrition-reference routes before the nutrition-state alias family, and tests/test_recipe_nutrition_reference_registration_bootstrap.py:187 asserts no dynamic /api/v1/nutrition route can precede GET /api/v1/nutrition/recommendations.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523395325 -> c6b6fe41bf45317e607cf9e017ecb662c33aef8a

Disposition: NOT-A-BUG
Evidence: git show -s --format=%B ac08b4b6f4e241c18b62e24dbc90db027e78d985 includes the canonical Experiment Runner co-author trailer, and the Phase2 gate inspects origin/main..HEAD for that trailer.
Reason: The Codex review targeted superseded commit d412942d75db55ec3cbc6c1e296a54f95433f0da; current branch history carries the required trailer on the implementation commit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523327703

Disposition: NOT-A-BUG
Evidence: docs/review/PR_2073_FIXED_MAPPING.md now has one checked post-open security-auditor row, and validate_mapping_artifact_text reports no artifact errors.
Reason: The Codex review targeted superseded commit 3a888230a8 before the pushed mapping-format commits; current head no longer contains the duplicate unchecked row.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523395324

Disposition: NOT-A-BUG
Evidence: python scripts/ci/check_pr_body_phase2_gates.py --pr-number 2073 --body "$(gh pr view 2073 --json body --jq .body)" --commit-range origin/main..HEAD --experiment-runner-evidence-mode required passed with the current canonical artifact and PR body mirror.
Reason: The Codex review targeted superseded commit 3a888230a8; current ## Fixed in Commit Mapping contains only parser-valid URL disposition blocks, with role-pass notes moved outside the canonical mapping section.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523395328

Disposition: NOT-A-BUG
Evidence: git log origin/main..HEAD contains ac08b4b6f4e241c18b62e24dbc90db027e78d985 with Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>; later commits are fix/governance follow-ups, not additional material Experiment Runner contributions.
Reason: The Codex review cited synthetic reviewed commit 7e387ce3981c743b656812d3cc76e3a885a4fd18, which is not present in the local branch object database; the repo rule requires the trailer on the material runner-shaped implementation commit, not every synthetic review context or docs-only follow-up.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523410266

Disposition: NOT-A-BUG
Evidence: GH_TOKEN="$(gh auth token)" python scripts/orchestration/check_review_threads_disposition.py --pr-number 2073 --require-auth passed on the actual branch head, and git log origin/main..HEAD contains the mapped FIXED proof commits 8d50f28c1, 111cc0f77e2ee1b849c92555e85422bb74b39a2e, and c6b6fe41bf45317e607cf9e017ecb662c33aef8a.
Reason: The Codex review cited synthetic reviewed commit 7e387ce3981c743b656812d3cc76e3a885a4fd18 instead of the actual PR branch history. The repo disposition guard is authoritative for resolvable proof SHAs and commit-after-comment validation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523410269

Disposition: NOT-A-BUG
Evidence: git cat-file -e b3eec6be948d67df33a6b1cf082a4d76172f088d^{commit} fails locally while git log origin/main..HEAD contains ac08b4b6f4e241c18b62e24dbc90db027e78d985 with Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>.
Reason: The Codex review cited synthetic reviewed commit b3eec6be948d67df33a6b1cf082a4d76172f088d, which is not present in the actual PR branch object database. The material Experiment Runner contribution remains the implementation commit ac08b4b6f4e241c18b62e24dbc90db027e78d985; later commits are fix/governance follow-ups.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523434325

Disposition: FIXED
Commit: f843dddd18b6a76ef5e08d73a0b7342512c24e10
Evidence: scripts/ci/check_legacy_growth_guard.py:257 recognizes getattr(app, "include_router") call actions, scripts/ci/check_legacy_growth_guard.py:656 treats indirect include_router calls as router-registration calls, and tests/test_legacy_growth_guard.py:1199 covers the recipes router bypass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523434326 -> f843dddd18b6a76ef5e08d73a0b7342512c24e10

Disposition: FIXED
Commit: 41c09ce035c63cde9eb0591af4efa5ddc64123ca
Evidence: scripts/ci/check_legacy_growth_guard.py:697 resolves getattr method-name aliases through collected static string bindings, and tests/test_legacy_growth_guard.py:1215 covers the bound method-name recipes router bypass.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523515621 -> 41c09ce035c63cde9eb0591af4efa5ddc64123ca

Disposition: NOT-A-BUG
Evidence: git cat-file -e c036554829af5c11d4703d088647daa3964ba195^{commit} fails locally while git log origin/main..HEAD contains ac08b4b6f4e241c18b62e24dbc90db027e78d985 with Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>.
Reason: The Codex review cited synthetic reviewed commit c036554829af5c11d4703d088647daa3964ba195, which is not present in the actual PR branch object database. The required trailer is present on the real material Experiment Runner commit, not on synthetic review-context SHAs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#discussion_r3523451234

Disposition: NOT-A-BUG
Evidence: tests/test_recipe_nutrition_reference_registration_bootstrap.py exercises app.main bootstrap ownership directly, and tests/test_legacy_growth_guard.py pins guard message output for intentional reintroduction regressions.
Reason: Sourcery raised maintainability considerations, not a correctness/security defect; adding a public test helper or guard-message builder would widen this legacy-removal PR beyond route ownership migration.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2073#pullrequestreview-4629716524

## Review Comment Dispositions

### Post-Open Bug-Hunter Route-Order Finding

Disposition: FIXED
Commit: 8d50f28c1
Evidence: app/bootstrap/route_family.py rejects existing static-family registrations whose FastAPI route order differs from source route order; tests/test_main_paywall_bootstrap.py covers generic order drift, and tests/test_recipe_nutrition_reference_registration_bootstrap.py covers `/api/v1/recipes/search` before `/api/v1/recipes/{recipe_id}`.
Reason: Prevents a complete preexisting family from passing membership checks while shadowing `/api/v1/recipes/search` through `/{recipe_id}`.

### Post-Open Bug-Hunter Experiment Evidence Finding

Disposition: FIXED
Commit: 8d50f28c1
Evidence: docs/review/RECIPE_NUTRITION_REFERENCE_CANONICAL_BOOTSTRAP_EXPERIMENT_RUNNER_EVIDENCE.md records the rejected zero-network attempt as an unpromoted infra caveat without presenting a duplicated artifact path as review evidence.
Reason: Keeps Experiment Runner evidence locatable and avoids promoting a rejected local infra-flake artifact.

### Post-Open Bug-Hunter JSON Assertion Finding

Disposition: FIXED
Commit: 8d50f28c1
Evidence: tests/test_recipe_nutrition_reference_registration_bootstrap.py asserts the JSON Content-Type before parsing the recipe search response.
Reason: Aligns the new bootstrap test with tests/AGENTS.md JSON response assertion policy.

### PulsePlate PR Review Large-Diff Note

Disposition: NOT-A-BUG
Evidence: pulseplate-pr-review reported only a large-diff planning note; focused recipe/nutrition behavior tests, bootstrap/guard/OpenAPI/auth-tier tests, check_legacy_growth_guard.py, targeted mypy, make openapi-check, pre-commit run --all-files, make validate-changed, pre-push hooks, role passes, and Codex Security all covered the changed surfaces.
Reason: The threshold is review-planning evidence, not a code/security defect. The PR owns one bounded legacy-removal slice plus the directly required shared route-order guard.

## Experiment Runner Evidence

- Artifact: `artifacts/orchestration/experiments/results/recipe-nutrition-reference-oracle-result-v2.json`
- Experiment id: `exp-4fe6753a1339`
- Mode: `oracle_only_governance_reviewer`
- Result: `accepted`
- Contribution kind: `oracle_review`
- `coauthor_required=true`
- Commit carrying required trailer: `ac08b4b6f4e241c18b62e24dbc90db027e78d985`

Infra caveat: the first zero-network local attempt recorded `status=rejected`,
`failure_class=infra_flake` because this development host does not provide
`unshare` for the network-disabled sandbox. The accepted `network_budget=1`
artifact kept the same local oracle commands and does not grant product
runtime, provider, client, or public API authority.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/3467351ee456.json`
- Starter: `scripts/orchestration/start_pr_lane.sh`
- Post-open packet: `artifacts/orchestration/task_packets/f5cb9acbe485.json`

## Validation Evidence

- `python scripts/orchestration/check_preflight.py` - PASS, with existing private-index env warning only.
- `python scripts/orchestration/check_agent_consistency.py` - PASS.
- `python -m pytest -q tests/test_recipes_api.py tests/test_recipe_preview.py tests/test_nutrition_recommendations_api.py` - PASS.
- `python -m pytest -q tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_legacy_growth_guard.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py` - PASS.
- `python -m pytest -q tests/test_legacy_growth_guard.py::test_legacy_growth_guard_rejects_recipe_nutrition_reference_router_reintroduction` - PASS after the indirect include_router regression fix.
- `python -m pytest -q tests/test_legacy_growth_guard.py` - PASS after the indirect include_router regression fix.
- `python -m pytest -q tests/test_recipe_nutrition_reference_registration_bootstrap.py tests/test_openapi_namespace_guards.py tests/security/test_api_auth_tier_contract_pack.py tests/security/test_api_authz_contract_static.py` - PASS after the indirect include_router regression fix.
- `python -m pytest -q tests/test_legacy_growth_guard.py::test_legacy_growth_guard_rejects_recipe_nutrition_reference_router_reintroduction tests/test_legacy_growth_guard.py` - PASS after the bound getattr method-name regression fix.
- `python -m pytest -q tests/test_nutrition_recommendations_api.py::TestFreeRecommendationsSuccess::test_recommendations_success tests/test_recipe_nutrition_reference_registration_bootstrap.py::test_nutrition_recommendations_route_cannot_be_shadowed_by_dynamic_v1_alias` - PASS.
- `python scripts/ci/check_legacy_growth_guard.py` - PASS.
- `python -m mypy app/bootstrap/route_family.py app/main.py app/routers/recipes.py app/routers/nutrition_recommendations.py scripts/ci/check_legacy_growth_guard.py` - PASS.
- `python -m mypy scripts/ci/check_legacy_growth_guard.py` - PASS after the bound getattr method-name regression fix.
- `DEV_PYTHON=.venv/bin/python make openapi-check` - PASS.
- `git diff --exit-code -- frontend/src/api/openapi.json frontend/src/api/schema.ts` - PASS.
- `pre-commit run --all-files` - PASS after hook formatting was committed and affected tests rerun.
- `make validate-changed` - PASS on latest implementation head; selected tests/test_legacy_growth_guard.py, tests/test_main_paywall_bootstrap.py, and tests/test_recipe_nutrition_reference_registration_bootstrap.py.
- Pre-push hooks - PASS on pushed heads: mypy where applicable, pip-audit, backend pytest pre-push, full-repo Bandit, and docker build test where applicable.
- Codex Security diff scan 08025660-053e-4a39-bb72-73277fe7c22f completed with 0 findings and 6/6 coverage rows closed for 8fdcd0ac1668f612de4dca90846fd994967e60df..191a2a317a42b6b7cc255e0011affedfe74e4435.
- Current-head Codex Security scan e82db3b8-d682-4072-b013-ac81071d0663 completed for 8fdcd0ac1668f612de4dca90846fd994967e60df..55b527d22325ca655e66e8507edea6c15b48bb56 with 0 findings and complete coverage.
- `pulseplate-pr-review` completed; one advisory large-diff note dispositioned as NOT-A-BUG above.

## Merge Readiness

Not claimed here. Requires current-head CI after the latest mapping/body commit,
strict merge-readiness gate, and resolved review threads.
