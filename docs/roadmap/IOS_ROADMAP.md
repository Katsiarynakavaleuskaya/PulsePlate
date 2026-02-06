# iOS Roadmap (Repo-Truth)

**Last Updated**: 6 February 2026
**Owner**: @katsiaryna_kavaleuskaya
**Cadence**: Update only when reality changes (PRs that change entrypoints, networking, guards, or localization).

---

## AS-IS (repo facts)

### App entry + navigation

- Entry point: `ios/PulsePlate/PulsePlateApp.swift` → `RootTabs()`
- Primary navigation: `ios/PulsePlate/Views/RootTabs.swift` (TabView)

> Note: PR-652 proposes a first-run Welcome gate before `RootTabs`. Keep that change in PR-652 scope only.

### Networking SoT (thin client)

- Transport: `ios/PulsePlate/Networking/{APIClient,HTTPClient,APIError}.swift`
- Base URL: `ios/PulsePlate/Services/AppConfig.swift` (`BASE_URL` Info.plist → env → fallback)
- Guards:
  - `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift` (no BMI logic/thresholds in app sources)

### Localization (supported)

- iOS locales exist: `ios/PulsePlate/{en,ru,es}.lproj/Localizable.strings`

---

## What changed recently

- PR-652 (pending): iOS P0 Welcome gate (versioned key `has_seen_welcome_v1`) + RU/EN/ES welcome copy.

---

## P0 Next Actions (real follow-ups only)

- Remove placeholder PRO key fallback and make key handling release-safe (tracked in `BACKLOG_LEDGER.md`).
- Add a guard/test that fails CI if placeholder keys like `test_pro_key` appear in app sources (tracked in `BACKLOG_LEDGER.md`).

---

## P1 / Future (tracked in BACKLOG_LEDGER)

- Keychain-backed PRO/VIP key storage and UX flows for entering/upgrading keys.
- Receipt validation / IAP orchestration (separate scope; requires backend contract).
- Deep-link allowlist rules (only after onboarding gates exist on the target platform).
