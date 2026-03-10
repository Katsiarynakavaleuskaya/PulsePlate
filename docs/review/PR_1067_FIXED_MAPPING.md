# PR 1067 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909721042 -> 0909148a
Disposition: FIXED
Evidence: ios/PulsePlate/en.lproj/Localizable.strings:62; ios/PulsePlate/ru.lproj/Localizable.strings:76; ios/PulsePlate/es.lproj/Localizable.strings:76
Reason: debug/internal missing-key copy now points to the actual UI path (`PRO Settings -> Debug Tools -> Keychain`) and keeps test-only recovery explicit instead of referencing Xcode environment variables.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727064 -> 0909148a
Disposition: FIXED
Evidence: docs/MOBILE_API_MIGRATION_GUIDE.md:135; docs/MOBILE_API_MIGRATION_GUIDE.md:156; docs/MOBILE_API_MIGRATION_GUIDE.md:478; docs/MOBILE_API_MIGRATION_GUIDE.md:520
Reason: the migration guide now uses the canonical `APIClient` / `DefaultWeeklyPlanService` seam for weekly-plan transport and consistently describes test/dev key handling through explicit injected providers only.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727068 -> 0909148a
Disposition: FIXED
Evidence: docs/roadmap/BACKLOG_LEDGER.md:253; docs/roadmap/BACKLOG_LEDGER.md:255
Reason: the ledger now uses future-tense wording for PR #1067 so the item stays truthful while still in progress.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727078 -> 768bed2b
Disposition: FIXED
Evidence: docs/roadmap/IOS_ROADMAP.md:20; docs/roadmap/IOS_ROADMAP.md:57
Reason: the roadmap now states that PRO runtime already reads from Keychain and narrows the future item to onboarding/UX plus VIP-only storage work.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727082 -> 0909148a
Disposition: FIXED
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:193; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:247; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:494; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:520; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:546; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:589
Reason: the repo-wide guard scan now lets `secretEnvFallbackHits(...)` build alias-aware regexes per file, so aliased `ProcessInfo.processInfo.environment` lookups are caught in the same path used against app sources.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910158437 -> 3daf8aa2
Disposition: FIXED
Evidence: docs/roadmap/BACKLOG_LEDGER.md:3891
Reason: the completed PR-667 ledger item now keeps the historical DoD phrasing neutral by referring to the app's secure key provider instead of implying PR #1067's stronger Keychain-only runtime invariant was already merged.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910158468 -> 0909148a
Disposition: FIXED
Evidence: docs/roadmap/BACKLOG_LEDGER.md:253; docs/roadmap/BACKLOG_LEDGER.md:255
Reason: the iOS Keychain conformance item keeps `PR #1067` in `In progress` state and now uses future-tense wording for the remaining runtime requirement.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910158474 -> 0909148a
Disposition: FIXED
Evidence: ios/PulsePlate/en.lproj/Localizable.strings:62; ios/PulsePlate/ru.lproj/Localizable.strings:76; ios/PulsePlate/es.lproj/Localizable.strings:76
Reason: the debug remediation copy now points to the real UI path (`PRO Settings -> Debug Tools -> Keychain`) and uses grammatically correct injected-provider wording.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910234533 -> 503c6a18
Disposition: FIXED
Evidence: docs/MOBILE_API_MIGRATION_GUIDE.md:74; docs/MOBILE_API_MIGRATION_GUIDE.md:77; docs/MOBILE_API_MIGRATION_GUIDE.md:80; docs/MOBILE_API_MIGRATION_GUIDE.md:148
Reason: the migration guide now keeps the canonical PRO weekly-plan endpoint on `/api/v1/pro/meal/weekly` and explicitly demotes `/api/v1/premium/plan/week-flexible` to a deprecated hidden alias.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910234537 -> 503c6a18
Disposition: FIXED
Evidence: docs/roadmap/BACKLOG_LEDGER.md:25; docs/roadmap/BACKLOG_LEDGER.md:249
Reason: the reopened mobile-secret conformance item was moved back under `Open Items` / `P1`, so the ledger no longer contradicts its own `In progress` status.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910234542 -> 503c6a18
Disposition: FIXED
Evidence: ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:263; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:539; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:573; ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift:607
Reason: the env-fallback architectural guard now catches access-controlled aliases without explicit type annotations and matches `self.env[...]` secret lookups via the repo-wide scan path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910329581 -> b2535fee
Disposition: FIXED
Evidence: docs/MOBILE_API_MIGRATION_GUIDE.md:292; docs/MOBILE_API_MIGRATION_GUIDE.md:468
Reason: the production Keychain sample now uses `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`, matching the checklist requirement and the intended runtime accessibility policy.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#pullrequestreview-3920850927
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2910329581; docs/MOBILE_API_MIGRATION_GUIDE.md:292; docs/MOBILE_API_MIGRATION_GUIDE.md:468
Reason: this CodeRabbit review entry is the summary shell for the single child comment dispositioned immediately above; the underlying checklist/sample mismatch was fixed in `b2535fee`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#pullrequestreview-3920196887
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727064; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727068; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727078; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1067#discussion_r2909727082
Reason: this CodeRabbit review entry is the summary shell for the actionable child comments dispositioned separately above.

## Merge Readiness
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
