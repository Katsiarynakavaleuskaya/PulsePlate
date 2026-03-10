# iOS Roadmap (Repo-Truth)

**Last Updated**: 7 February 2026
**Owner**: @katsiaryna_kavaleuskaya
**Cadence**: Update only when reality changes (PRs that change entrypoints, networking, guards, or localization).

---

## AS-IS (repo facts)

### App entry + navigation

- Entry point: `ios/PulsePlate/PulsePlateApp.swift` → `WelcomeGateView()` → `RootTabs()`
- Primary navigation: `ios/PulsePlate/Views/RootTabs.swift` (TabView)

### Networking SoT (thin client)

- Transport: `ios/PulsePlate/Networking/{APIClient,HTTPClient,APIError}.swift` (protocol: `APIClient.swift:4`)
- Base URL: `ios/PulsePlate/Services/AppConfig.swift` (`BASE_URL` Info.plist → env → fallback)
- PRO key: `ios/PulsePlate/Services/ProKeyProvider.swift:3` (Keychain-only runtime source)
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

---

## Completed P0 actions

- ✅ Remove placeholder PRO key fallback and make key handling release-safe (PR-656).
- ✅ Add a guard/test that fails CI if placeholder keys like `test_pro_key` appear in app sources (PR-657).

All P0 items are shipped. Remaining work is P1 (see below and `BACKLOG_LEDGER.md`).

## P1 Next Actions

- [ ] Expose BMI screen from Home / RootTabs (Free MVP UX). Evidence: `ios/PulsePlate/Screens/BMICalculatorScreen.swift:3`, `ios/PulsePlate/Views/RootTabs.swift:3-5` (not yet wired).
- [ ] Mount WeeklyPlanReader behind feature flag (PRO demo slice).

---

## P1 / Future (tracked in BACKLOG_LEDGER)

- Keychain-backed PRO/VIP key storage and UX flows for entering/upgrading keys.
- Receipt validation / IAP orchestration (separate scope; requires backend contract).
- Deep-link allowlist rules (only after onboarding gates exist on the target platform).
