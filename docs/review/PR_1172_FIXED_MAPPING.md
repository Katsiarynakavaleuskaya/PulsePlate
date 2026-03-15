# PR 1172 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: c67514d3
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:636, ios/PulsePlate/Screens/PaywallScreen.swift:130, ios/PulsePlate/Models/StoreKitManager.swift:113, ios/PulsePlateTests/Models/StoreKitManagerCatalogTests.swift:52
Reason: Follow-up review fixes broaden the contract regex to accept mixed-case IDs, keep the retry button disabled while products load, remove duplicate membership helpers, and make the catalog-order regression assert against product IDs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949815836 -> c67514d3

Disposition: FIXED
Commit: c67514d3
Evidence: docs/review/PR_1172_FIXED_MAPPING.md:1
Reason: The canonical mapping artifact was reset from premature readiness to an honest in-progress state before the final required-check cycle completed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#discussion_r2936385445 -> c67514d3


Disposition: FIXED
Commit: 6a5adc7e
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:467
Reason: The hardcoded StoreKit ID guard now scans for any `com.pulseplate.premium.*` literal, including unknown IDs and mixed-case variants, instead of only checking the currently approved catalog IDs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#discussion_r2936388166 -> 6a5adc7e

Disposition: FIXED
Commit: 6a5adc7e
Evidence: ios/PulsePlateUITests/UISmokeTests.swift:17
Reason: UI smoke now launches the stable paywall preview scenario and still asserts that the app reaches the foreground, preserving a minimal launch-health signal without reintroducing flaky waits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#discussion_r2936389036 -> 6a5adc7e


Disposition: FIXED
Commit: f49207aa
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:549, ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:564, ios/PulsePlateUITests/UISmokeTests.swift:11, ios/PulsePlateUITests/UISmokeTests.swift:25
Reason: The latest bot review is closed by keeping doc↔code parity order/duplicate assertions explicit and replacing the flaky foreground wait with a bounded post-launch liveness check while still centralizing the UI smoke launch-contract strings.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949869237 -> f49207aa

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1172_FIXED_MAPPING.md:7
Reason: These earlier bot review-summary URLs either summarize inline findings that are already dispositioned above or do not add standalone unresolved defects beyond the mapped follow-up commits.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949820031
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949823990
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949825246
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949835705


Disposition: FIXED
Commit: c8d35512
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:655
Reason: The canonical contract parser now accepts mixed-case StoreKit product IDs, closing the guard blind spot where doc rows with uppercase characters could be skipped.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#discussion_r2936465170 -> c8d35512
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1172#pullrequestreview-3949926823 -> c8d35512

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
