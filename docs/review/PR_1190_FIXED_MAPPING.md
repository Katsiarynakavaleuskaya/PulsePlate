# PR 1190 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: ac657e87
Evidence: `ios/PulsePlate/Services/SubscriptionManager.swift:186`, `ios/PulsePlate/Services/SubscriptionManager.swift:223`, `ios/PulsePlate/Services/SubscriptionManager.swift:301`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1190#pullrequestreview-3973435214 -> ac657e87

Disposition: FIXED
Commit: 90149308
Evidence: `ios/PulsePlate/Models/Payments/SubscriptionBillingDTOs.swift:53`, `ios/PulsePlate/Models/Payments/SubscriptionBillingDTOs.swift:160`, `ios/PulsePlateTests/Services/SubscriptionBillingServiceTests.swift:120`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1190#pullrequestreview-3973474094 -> 90149308

## Merge Readiness

- Status: ready for review; waiting for current-head CI completion and next review wave to confirm no new actionables
- Local validation:
  - `pre-commit run --all-files`
  - `make verify`
  - targeted `xcodebuild` subset for `SubscriptionBillingServiceTests` and `SubscriptionManagerTests`
- Current scope rule: runtime-only iOS thin-client handoff with minimal docs sync
