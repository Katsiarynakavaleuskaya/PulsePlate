# PR 1296 — Fixed in Commit Mapping

## Discussion Thread Pass
- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

## Fixed in Commit Mapping
- Pending post-open review activity

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- Scope: PR3 billing activation/persistence closeout only. This lane removes shadow runtime dependence on `_ACTIVATIONS`, keeps persisted truth on `subscriptions` plus `subscription_activation_audit`, and explicitly excludes entitlement routing, frontend/web entitlement changes, migrations, App Store modernization, and broad legacy cleanup.
