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

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- Scope: PR3 billing activation/persistence closeout only. This lane removes shadow runtime dependence on `_ACTIVATIONS`, keeps persisted truth on `subscriptions` plus `subscription_activation_audit`, and explicitly excludes entitlement routing, frontend/web entitlement changes, migrations, App Store modernization, and broad legacy cleanup.
