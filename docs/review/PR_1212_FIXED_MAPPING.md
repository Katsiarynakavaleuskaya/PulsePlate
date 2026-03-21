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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986196948 -> 4c8eaa0d
Disposition: FIXED
Commit: 4c8eaa0d
Evidence: app/routers/pro_payments.py:79; app/routers/pro_payments.py:116; tests/test_pro_payments_openapi_contract.py:36

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969761922 -> 4c8eaa0d
Disposition: FIXED
Commit: 4c8eaa0d
Evidence: app/routers/pro_payments.py:79; app/routers/pro_payments.py:116; tests/test_subscription_activation_api.py:1124

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969769493 -> 4c8eaa0d
Disposition: FIXED
Commit: 4c8eaa0d
Evidence: app/routers/pro_payments.py:79; app/routers/pro_payments.py:116; app/routers/pro_payments.py:155; tests/test_pro_payments_openapi_contract.py:36

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969769497 -> 4c8eaa0d
Disposition: FIXED
Commit: 4c8eaa0d
Evidence: app/routers/pro_payments.py:150; app/routers/pro_payments.py:155

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969769501
Disposition: NOT-A-BUG
Evidence: app/middleware/api_tiers.py:209; app/middleware/api_tiers.py:212; app/middleware/api_tiers.py:217; tests/test_api_tiers.py:349; tests/test_api_tiers.py:390
Reason: The non-manual-source test returns at the source guard before created_at is read, and the malformed-activated_at test fails at activated_at normalization before created_at is consulted, so both tests already isolate the intended branches.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986203435
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1212_FIXED_MAPPING.md:62; docs/review/PR_1212_FIXED_MAPPING.md:74
Reason: This review is a wrapper packet for child comments with mixed dispositions; its actionable items are fully covered by the FIXED entries for discussion_r2969769493/discussion_r2969769497 and the NOT-A-BUG entry for discussion_r2969769501 above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986218989
Disposition: NOT-A-BUG
Evidence: tests/test_subscription_activation_api.py:289; tests/test_subscription_activation_api.py:301; tests/test_subscription_activation_api.py:323; tests/test_subscription_activation_api.py:343
Reason: CodeRabbit identified a test-only boilerplate nit. The four helpers intentionally keep their session lifecycle explicit at the mutation site so each audit/update/delete transaction boundary remains obvious inside the fixture layer; extracting another helper would add indirection without changing runtime behavior or contract coverage.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#discussion_r2969788219 -> ca24c050
Disposition: FIXED
Commit: ca24c050
Evidence: app/routers/pro_payments.py:115; app/routers/pro_payments.py:117; tests/test_subscription_activation_api.py:1124; tests/test_subscription_activation_api.py:1127

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1212#pullrequestreview-3986220190
Disposition: NOT-A-BUG
Evidence: app/routers/pro_payments.py:115; tests/test_subscription_activation_api.py:1124
Reason: This cubic wrapper review duplicates the single actionable child thread discussion_r2969788219; the underlying envelope mismatch is fixed in commit `ca24c050` and recorded directly above.

## Merge Readiness

- Status: ready for review / not ready to merge.
- Current packet commits:
  - `ca24c050` — `fix(payments): restore 400 error envelope`
  - `4c8eaa0d` — `fix(payments): align activation error contract`
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
  - `make openapi`
  - `pytest -q tests/test_subscription_activation_api.py tests/test_pro_payments_openapi_contract.py tests/test_api_tiers.py`
  - `pre-commit run --hook-stage push mypy --files app/services/payments_activation.py`
