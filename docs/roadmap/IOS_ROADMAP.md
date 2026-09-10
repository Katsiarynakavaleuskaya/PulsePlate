# iOS Roadmap (Repo-Truth)

**Last Updated**: 9 September 2026
**Owner**: @katsiaryna_kavaleuskaya
**Cadence**: Update only when reality changes (PRs that change entrypoints, networking, guards, or localization).

---

## AS-IS (repo facts)

### App entry + navigation

- Entry point: `ios/PulsePlate/PulsePlateApp.swift` → `WelcomeGateView()` → `RootTabs()`
- Section source of truth: `AppSection.productionSections` fixes the exact
  `Home / BMI / Today / Progress / Profile` order with stable identity and tags.
- Primary shell: `RootTabs` uses one `TabView(selection:)`; iOS 18 applies
  `sidebarAdaptable`, while iOS 17 keeps the default system tab presentation.
- Shell labels resolve through the app-selected
  `LocalizationManager.currentLanguage` for EN/RU/ES, independent of the device
  locale.
- Home and BMI keep `RootTabs` as their external `NavigationStack` owner.
  Today, Progress, and Profile remain direct tab children and keep their own
  existing stacks.
- Retained native sequences observe tab-away/tab-return and Weekly pop/re-entry
  on compact iPhone 26, iPad 26 sidebar, and iOS 17. Separate iPad half-width
  Today, one-third-width Russian AX5 Profile, and compact Home frames are also
  captured. The corrected Today afterframes are included in the bounded
  14-frame V1 kit accepted by the Product Owner as `GO` on 9 September 2026 at
  material head `f8f65b2bf5b42777681d4a3cce1cdbfe7f284088`. This acceptance
  does not claim geometry beyond the captured window conditions.
- Today presents its existing localized title through the self-owned stack's
  inline navigation bar. The subtitle, hero, and footer actions stay in their
  existing content and inset positions.
- Weekly Progress is not a top-level tab. It is a navigation-neutral child
  reachable exactly once from Progress. Progress owns its session HealthKit
  manager; recreated Weekly children observe that same reference. This retains
  request-completion state during the parent's lifetime, not per-type read
  permission or state across relaunch.
- Progress loading, empty, completion and action copy uses the app-selected
  EN/RU/ES localization manager; existing query and issue-envelope behavior stays
  unchanged.
- Progress locally resolves card material in Dark appearance while restoring the
  caller's appearance for content. Its Weekly link uses a full-width title row
  at accessibility sizes; chart data and scale stay unchanged with explicit
  readable axis styling.
- The same-PR owner-approved accessibility amendment uses existing Navy for
  primary PPButton labels and loading indicators over the unchanged blue fill.
  Secondary/ghost variants, tokens, assets, sizing and actions stay unchanged;
  the accepted 14-frame Human V1 kit covers this amendment. Current-head CI,
  canonical closeout, and merge remain pending.
- Existing `DebugToolsScreen` entry points in Profile and Today are compile-gated
  with `#if DEBUG`; the Today Release branch routes to Profile. Diagnostics are
  never part of the production tab inventory.
- Active Debug/Release plists explicitly select the packaged LaunchScreen,
  declare the accepted phone/tablet orientations and single-scene lifecycle,
  and retain the localized read-only HealthKit purpose fallback. All four source
  Info plists remain outside Copy Bundle Resources. Built-bundle and native
  viewport/interaction evidence are required in addition to source assertions.

Evidence:

- `ios/PulsePlate/Models/AppSection.swift:3-52`
- `ios/PulsePlate/Views/RootTabs.swift:4-58`
- `ios/PulsePlate/Views/PlateView.swift:203-204`
- `ios/PulsePlate/Views/ProgressView.swift:4`
- `ios/PulsePlate/Views/ProgressView.swift:285`
- `ios/PulsePlate/DesignSystem/PPButton.swift:98`
- `ios/PulsePlate/DesignSystem/PPButton.swift:138`
- `ios/PulsePlateTests/DesignSystemAccessibilityContractTests.swift:220`
- `ios/PulsePlate/Views/WeeklyProgressView.swift:4`
- `ios/PulsePlate/Views/ProfileView.swift:5`
- `ios/PulsePlate/Views/ProfileView.swift:101`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:25-49`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:121-156`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:173`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:233`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:252`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:413`
- `ios/PulsePlate/Info-Debug.plist:19`
- `ios/PulsePlate/Info-Release.plist:25`
- `ios/PulsePlate.xcodeproj/project.pbxproj:54`
- `ios/PulsePlate.xcodeproj/project.pbxproj:497`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:580`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:642`

### Networking SoT (thin client)

- Transport: `ios/PulsePlate/Networking/{APIClient,HTTPClient,APIError}.swift` (protocol: `APIClient.swift:4`)
- Base URL: `ios/PulsePlate/Services/AppConfig.swift` (`BASE_URL` Info.plist → env → fallback)
- PRO key runtime: `ios/PulsePlate/Services/ProKeyProvider.swift:3` (reads from Keychain only at runtime)
- Profile query params: `ios/PulsePlate/Services/ProfileProvider.swift:42-49` (`ProfileProviding` protocol)
- Guards:
  - `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift` (no BMI logic/thresholds in app sources)

### Localization (supported)

- iOS locales exist: `ios/PulsePlate/{en,ru,es}.lproj/Localizable.strings`

---

## What changed recently

- PR-653 (merged): iOS P0 Welcome gate (versioned key `has_seen_welcome_v1`) + RU/EN/ES welcome copy.
- PR-667 (merged): Plate (PRO) uses canonical `GET /api/v1/pro/nutrition/daily` (deterministic query + `X-API-Key`).
  Evidence: `ios/PulsePlate/Services/ProDailyNutritionService.swift:36-57`, `ios/PulsePlate/Services/ProDailyNutritionService.swift:94-105`,
  `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:6-21`, `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift:23-65`,
  `app/routers/pro.py:369-373`, `app/routers/pro.py:400-422`.
- IOS-REL-2 (active, not merged): [PR #2376](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2376)
  carries the consumer-first adaptive navigation shell on
  `codex/ios-adaptive-navigation-shell`; tracking:
  [`ledger-p1-ios-release-design-train-navigation-shell`](BACKLOG_LEDGER.md#ledger-p1-ios-release-design-train-navigation-shell).
  Product Owner approved Candidate A and delegated same-PR recovery and merge
  after the required gates. The branch now inherits the merged V5 asset
  prerequisite [#2380](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2380)
  and Release/AppIcon prerequisite
  [#2381](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2381).
  It preserves V5 presentation while correcting Weekly manager lifetime and
  Progress state localization, and repairs the effective launch/orientation and
  plist-resource metadata exposed by the real Release probe. The RubyZip
  prerequisite [#2347](https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2347)
  is merged at `e5d162168a866b64f1750f396e6034643f210cca` and inherited by this
  branch. Current-head security checks remain separate required evidence;
  another owner handles Trivy policy maintenance and general main health.
  The Product Owner accepted the bounded 14-frame SwiftUI V1 kit as `GO` on
  9 September 2026 at material head `f8f65b2bf5b42777681d4a3cce1cdbfe7f284088`;
  terminal current-head CI, canonical closeout, and merge remain pending.

---

## Completed P0 actions

- ✅ Remove placeholder PRO key fallback and make key handling release-safe (PR-656).
- ✅ Add a guard/test that fails CI if placeholder keys like `test_pro_key` appear in app sources (PR-657).

All P0 items are shipped. Remaining work is P1 (see below and `BACKLOG_LEDGER.md`).

## P1 Next Actions

- [x] Expose BMI from the primary shell. Shipped via PR-671; the current
  IOS-REL-2 code preserves BMI as the `.bmi` member of the fixed `AppSection`
  inventory and routes it from `RootTabs`.
  Evidence: `ios/PulsePlate/Models/AppSection.swift:3-16` and
  `ios/PulsePlate/Views/RootTabs.swift:18-51`.
- [x] Complete IOS-REL-2 real SwiftUI V1 review and Product Owner `GO` for the
  bounded 14-frame kit at `f8f65b2bf5b42777681d4a3cce1cdbfe7f284088`.
- [ ] Complete IOS-REL-2 exact-head CI, canonical closeout, and
  human-authorized merge; see the
  [canonical ledger item](BACKLOG_LEDGER.md#ledger-p1-ios-release-design-train-navigation-shell).
- [ ] Start IOS-REL-3 FREE BMI only after IOS-REL-2 merges, post-merge exact-main
  health is terminal, and a fresh ownership/overlap census is complete.
- [ ] Mount WeeklyPlanReader behind feature flag (PRO demo slice).

---

## P1 / Future (tracked in BACKLOG_LEDGER)

- Onboarding/UX for Keychain-backed PRO flows and VIP-only key storage.
- Receipt validation / IAP orchestration (separate scope; requires backend contract).
- Deep-link allowlist rules (only after onboarding gates exist on the target platform).
