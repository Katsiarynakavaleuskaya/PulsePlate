# iOS Roadmap (Repo-Truth)

**Last Updated**: 3 September 2026
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
- Tab-away/tab-return retention across adaptive presentation and window-size
  changes remains a required real SwiftUI V1 acceptance check; it is not yet
  claimed as proven.
- Weekly Progress is not a top-level tab. It is a navigation-neutral child
  reachable exactly once from Progress.
- `DebugToolsScreen` is available only inside the compile-gated DEBUG Profile
  section; it is never part of the production tab inventory.

Evidence:

- `ios/PulsePlate/Models/AppSection.swift:3-52`
- `ios/PulsePlate/Views/RootTabs.swift:4-58`
- `ios/PulsePlate/Views/PlateView.swift:203-204`
- `ios/PulsePlate/Views/ProgressView.swift:10-33`
- `ios/PulsePlate/Views/ProgressView.swift:209-245`
- `ios/PulsePlate/Views/WeeklyProgressView.swift:24-94`
- `ios/PulsePlate/Views/ProfileView.swift:25-26`
- `ios/PulsePlate/Views/ProfileView.swift:68-104`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:25-49`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:121-156`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:173-294`
- `ios/PulsePlateTests/AppNavigationShellTests.swift:310-465`
- `ios/PulsePlate.xcodeproj/project.pbxproj:496`

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
  Product Owner approved Candidate A. Real SwiftUI V1 review and human `GO`,
  terminal current-head CI, closeout, merge authorization, and merge remain
  pending.

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
- [ ] Complete IOS-REL-2 real SwiftUI V1 review, exact-head CI, closeout, and
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
