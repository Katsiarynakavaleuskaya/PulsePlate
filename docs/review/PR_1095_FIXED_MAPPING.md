# PR 1095 — Fixed in Commit Mapping

This artifact remains scoped to PR `#1095` only.

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#pullrequestreview-3925960504
Disposition: NOT-A-BUG
Evidence: rate-limit notice only; no child actionable threads were emitted by Sourcery for this review.
Reason: the Sourcery review is a rate-limit shell and does not request code or docs changes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#pullrequestreview-3925983179
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004607; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004609; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004611
Reason: this Codex review entry is a summary shell; the actionable child threads are dispositioned separately below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004607 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004609 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915004611 -> ca3b622f
Disposition: FIXED
Commit: ca3b622f
Evidence: app/routers/pro_payments.py:92; app/services/payments_activation.py:469; app/services/payments_activation.py:1066; app/models/subscriptions.py:43; alembic/versions/202603100001_add_subscription_activation_tables.py:26; tests/test_subscription_activation_api.py:343; tests/test_subscription_activation_api.py:752
Reason: the persisted runtime route now rejects legacy bodies with `422`, activation replays recover from uniqueness races, and both ORM + migration use `BIGINT` for auth-derived subject IDs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#pullrequestreview-3926001640
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022860; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022864; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022866; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022870; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022873; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022877
Reason: cubic identified these issues in the review summary shell; the actionable child threads are dispositioned separately below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022860 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022864 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022866 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022870 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022873 -> ca3b622f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915022877 -> ca3b622f
Disposition: FIXED
Commit: ca3b622f
Evidence: app/schemas/payments.py:233; app/routers/pro_payments.py:92; app/services/payments_activation.py:469; app/services/payments_activation.py:1066; app/services/payments_activation.py:1289; app/models/subscriptions.py:89; app/models/subscriptions.py:91; alembic/versions/202603100001_add_subscription_activation_tables.py:26; alembic/versions/202603100001_add_subscription_activation_tables.py:62; tests/test_subscription_activation_api.py:279; tests/test_subscription_activation_api.py:518; tests/test_subscription_activation_api.py:752; tests/test_payment_reconciliation_api.py:123
Reason: canonical payloads are normalized before hashing, runtime activation rejects legacy bodies, replay races are idempotent, audit keys are widened, manual rejected state reads back correctly, and persisted `user_id` columns now match int64 subject IDs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#pullrequestreview-3926040130
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056409; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056416; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056421; app/schemas/payments.py:248; docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-billing-activation-openapi-refinements
Reason: the actionable child threads are dispositioned separately below; the remaining payload re-validation is an intentional bounded re-parse from already normalized payload dicts, and the broader OpenAPI shape refinements are deferred to the dedicated backlog item.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056409 -> 6bee041d
Disposition: FIXED
Commit: 6bee041d
Evidence: app/services/payments_activation.py:146; app/services/payments_activation.py:1299; tests/test_payment_reconciliation_api.py:358; tests/test_payment_reconciliation_api.py:381; tests/test_subscription_activation_api.py:605; tests/test_pro_vip_route_dependency_guard.py:83
Reason: manual reconciliation now trusts persisted DB state instead of stale shadow-cache state, negative amounts fail closed, and the allowlist guard message uses the dependency name when available.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056416 -> 1d56aad9
Disposition: FIXED
Commit: 1d56aad9
Evidence: docs/review/PR_1095_FIXED_MAPPING.md:5; docs/review/PR_1095_FIXED_MAPPING.md:6
Reason: the discussion-pass checklist is now checked only after recording explicit dispositions.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1095#discussion_r2915056421 -> 32cb5ffe
Disposition: FIXED
Commit: 32cb5ffe
Evidence: docs/roadmap/BACKLOG_LEDGER.md:35; docs/roadmap/BACKLOG_LEDGER.md:64; docs/roadmap/BACKLOG_LEDGER.md:82; docs/roadmap/BACKLOG_LEDGER.md:195
Reason: the billing child ledger items now point deterministically to PR `#1095`, the entitlement follow-up is linked by canonical ledger id, and the deferred OpenAPI follow-up is recorded explicitly.

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
