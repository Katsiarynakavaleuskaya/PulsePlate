# PR 1171 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlate/Models/StoreKitManager.swift:47, ios/PulsePlate/Services/SubscriptionManager.swift:183
Reason: Receipt loading now runs asynchronously off the main actor and all purchase/restore call sites await the receipt read before verification.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935409911 -> ba14bde0

Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlate/Screens/PaywallScreen.swift:19, ios/PulsePlate/Screens/PaywallScreen.swift:113, ios/PulsePlate/Screens/PaywallScreen.swift:132
Reason: The paywall now shows entitlement data without a local paid-truth helper, keeps actions disabled during `.pendingApproval`, and uses a high-level `Error` status label so the detailed error text appears only once.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935409913 -> ba14bde0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419750 -> ba14bde0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419752 -> ba14bde0

Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlate/Services/SubscriptionManager.swift:250, ios/PulsePlate/Services/SubscriptionManager.swift:281, ios/PulsePlateTests/Services/SubscriptionManagerTests.swift:215
Reason: Stale activation-pointer handling now treats HTTP 403 the same way as missing/not-found activation pointers, and the regression tests seed a real pointer before asserting the foreground refresh skip path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935415474 -> ba14bde0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935418800 -> ba14bde0

Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlate/Models/Payments/SubscriptionBillingDTOs.swift:43, ios/PulsePlate/Models/Payments/SubscriptionBillingDTOs.swift:84
Reason: Billing response DTOs now define explicit coding keys for fields such as `product_id` and `activation_id`, preventing snake_case decode drift under the shared HTTP decoder.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935418796 -> ba14bde0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935418799 -> ba14bde0

Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlate/PulsePlateApp.swift:17
Reason: App-store screenshot scenarios now skip subscription bootstrap and foreground refresh so deterministic screenshot runs do not hit StoreKit or backend billing flows.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419748 -> ba14bde0

Disposition: FIXED
Commit: ba14bde0
Evidence: ios/PulsePlateTests/Services/SubscriptionBillingServiceTests.swift:124
Reason: The XCTest-only `@unchecked Sendable` helper now carries an explicit safety justification comment.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419755 -> ba14bde0

Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Services/ActivationPointerStore.swift:3, docs/roadmap/BACKLOG_LEDGER.md:994
Reason: PR-4 intentionally persists only a non-sensitive `activation_id` refresh pointer in `UserDefaults`; Keychain storage conformance is tracked separately under the dedicated mobile follow-up and is out of scope for this orchestration PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419751

Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Services/SubscriptionManager.swift:130, ios/PulsePlate/Services/SubscriptionManager.swift:250
Reason: PR-4 explicitly forbids automatic receipt replay on launch/foreground. When no activation pointer exists, bootstrap loads the catalog only and leaves recovery to explicit `purchase()` or `restore()` flows.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419753

Disposition: FIXED
Commit: 7b4f5613
Evidence: docs/review/PR_1171_FIXED_MAPPING.md:1
Reason: Merge-readiness checkboxes are reset to the real in-progress state until required checks, review threads, and the final wait window are actually complete.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935419746 -> 7b4f5613

Disposition: FIXED
Commit: f3e7cc35
Evidence: ios/PulsePlateTests/Services/SubscriptionBillingServiceTests.swift:124
Reason: The `@unchecked Sendable` test helper now uses `NSLock` to synchronize mutable captured state, so the Sendable justification matches the implementation instead of claiming immutability.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935453482 -> f3e7cc35

Disposition: FIXED
Commit: f3e7cc35
Evidence: ios/PulsePlate/Screens/PaywallScreen.swift:19
Reason: The entitlement badge is now shown only when the subscription flow is actually `.unlocked`, so inactive or pending entitlement snapshots are not rendered as active access.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935453489 -> f3e7cc35

Disposition: FIXED
Commit: f3e7cc35
Evidence: ios/PulsePlate/Services/SubscriptionManager.swift:304, ios/PulsePlate/Services/SubscriptionManager.swift:474, ios/PulsePlateTests/Services/SubscriptionManagerTests.swift:99
Reason: Activation request building now trims blank `verification.productID` values before fallback, and the regression test proves we fall back to the StoreKit transaction product when the backend sends whitespace.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935455610 -> f3e7cc35

Disposition: FIXED
Commit: f3e7cc35
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:379, ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:414
Reason: Thin-client guard tests now fail when a guarded file is missing and use token-bound matching for forbidden flags, closing both the silent-skip and false-positive gaps.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935455618 -> f3e7cc35
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#discussion_r2935455624 -> f3e7cc35

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1171_FIXED_MAPPING.md:7
Reason: These bot review-level URLs aggregate inline findings that are already dispositioned above; after mapping the underlying inline comments, the review summary URLs do not represent additional standalone unresolved defects.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#pullrequestreview-3948956384
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#pullrequestreview-3948964977
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#pullrequestreview-3948965665
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#pullrequestreview-3948991651
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1171#pullrequestreview-3948993625

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
