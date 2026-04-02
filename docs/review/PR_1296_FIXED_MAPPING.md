# PR 1296 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#pullrequestreview-4048195361 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:122, docs/roadmap/BACKLOG_LEDGER.md:2495
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#discussion_r3025739121 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:122, docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:127
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#discussion_r3025739127 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2495, docs/roadmap/BACKLOG_LEDGER.md:2498
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#discussion_r3025739130 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2495, commit 281559f6 removes `docs/security/CVE-2026-4046-glibc.md` from this billing branch
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#pullrequestreview-4048203965
Disposition: NOT-A-BUG
Evidence: tests/test_payment_reconciliation_api.py:97, tests/test_ios_receipt_verification_api.py:62
Reason: The remaining Sourcery note is a test-only refactor suggestion, not a correctness defect. The helpers are narrowly scoped, each owns a different persistence assertion, and keeping them local avoids introducing extra shared test indirection in this billing closeout lane.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#pullrequestreview-4048206342 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:122, docs/roadmap/BACKLOG_LEDGER.md:2495
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#discussion_r3025751105 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:122, docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:127
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#discussion_r3025751108 -> 281559f6
Disposition: FIXED
Commit: 281559f6
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2495, docs/roadmap/BACKLOG_LEDGER.md:2498
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1296#pullrequestreview-4048252600 -> 302960b8
Disposition: FIXED
Commit: 302960b8
Evidence: docs/roadmap/BACKLOG_LEDGER.md:2502

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- Scope: PR3 billing activation/persistence closeout only. This lane removes shadow runtime dependence on `_ACTIVATIONS`, keeps persisted truth on `subscriptions` plus `subscription_activation_audit`, and explicitly excludes entitlement routing, frontend/web entitlement changes, migrations, App Store modernization, and broad legacy cleanup.
