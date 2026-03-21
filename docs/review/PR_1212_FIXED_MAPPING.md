# PR 1212 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986105610 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:754; tests/test_payment_reconciliation_api.py:120; tests/test_subscription_activation_api.py:2061

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969663895 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:754; app/services/payments_activation.py:1573; tests/test_subscription_activation_api.py:2061

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969663896 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: tests/test_payment_reconciliation_api.py:120; tests/test_payment_reconciliation_api.py:131; tests/test_payment_reconciliation_api.py:163

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986107620 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:285; app/services/payments_activation.py:1431; tests/test_subscription_activation_api.py:1224; tests/test_subscription_activation_api.py:1230

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969666590 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:754; app/services/payments_activation.py:1573; tests/test_subscription_activation_api.py:2061

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969666594 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:285; app/services/payments_activation.py:1431; tests/test_subscription_activation_api.py:1224; tests/test_subscription_activation_api.py:1230

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986108289 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:754; app/services/payments_activation.py:1573; tests/test_subscription_activation_api.py:2061

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969667429 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/services/payments_activation.py:754; app/services/payments_activation.py:1573; tests/test_subscription_activation_api.py:2061

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986113104 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/middleware/api_tiers.py:199; app/middleware/api_tiers.py:215; tests/test_api_tiers_db_lookup.py:253

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969672124 -> 231839ce
Disposition: FIXED
Commit: 231839ce
Evidence: app/middleware/api_tiers.py:199; app/middleware/api_tiers.py:215; tests/test_api_tiers_db_lookup.py:253

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969672127 -> 0b53fed5
Disposition: FIXED
Commit: 0b53fed5
Evidence: docs/review/PR_1212_FIXED_MAPPING.md:5

## Merge Readiness

- Status: ready for review / not ready to merge.
- Current packet commits:
  - `231839ce` — `fix(payments): close pr 1212 runtime blockers`
  - `05df5f15` — `chore(pre-commit): apply hook fixes`
  - `d85e7f1d` — `docs(roadmap): sync Batch B close-out after PR #1207`
  - `bf3c05a2` — `fix(payments): persist bounded manual activation expiry`
  - `4efff5c9` — `fix(authz): preserve legacy manual compat in entitlement routing`
  - `26a697b6` — `test(payments): cover activation envelopes and compat guards`
  - `e6708d9f` — `docs(api): sync backend billing truth contract`
  - `69b18ee1` — `fix(payments): narrow ios activation status typing`
  - `04e2cdaf` — `fix(payments): satisfy push-hook billing typing`
  - `3870d514` — `fix(payments): restore canonical manual reconcile path`
- Current scope discipline:
  - activation persistence semantics, backend entitlement routing truth, deterministic Apple upstream envelopes, generated OpenAPI/types sync, roadmap/index sync, and billing regression tests only
  - no App Store offers / ASC protected envs
  - no screenshot or assets rollout
  - no semantic App Store validators
  - no new iOS/client billing redesign
  - no Batch C/D/E scope
- Required before merge:
  - record every actionable review disposition in this artifact
  - resolve review threads only after disposition evidence exists
  - confirm current-head required checks are green with no pending required jobs
  - confirm no actionable bot comments remain
  - re-run `pre-commit run --all-files`
  - re-run `make verify`
- PR-local validation executed on this lane:
  - `python3 scripts/orchestration/check_preflight.py`
  - `python3 scripts/orchestration/check_agent_consistency.py`
  - `pre-commit run --all-files`
  - `make verify`
  - `pytest -q tests/test_subscription_activation_api.py tests/test_pro_payments_openapi_contract.py`
  - `pre-commit run --hook-stage push mypy --files app/services/payments_activation.py`
