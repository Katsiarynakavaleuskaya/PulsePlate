# iOS Backend Realization Roadmap (App-Visible Delivery Map)

**Last updated:** 6 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**Purpose:** Make backend progress **visibly real in the iOS app** via a deterministic, thin-client delivery plan.

> This document is **roadmap / planning**, not a policy. Hard rules remain in root `AGENTS.md` + `ios/AGENTS.md`.

---

## 0) Non-negotiables (policy anchors)

- **Thin client (iOS):** iOS renders backend fields; it does not compute BMI logic/thresholds.
  Anchor: `ios/AGENTS.md` (Thin Client Policy) + guard `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`.
- **One HTTP seam:** all runtime networking goes through `ios/PulsePlate/Networking/{APIClient,HTTPClient}`.
  Anchor: `docs/audit/PR_595_IOS_THIN_HTTP_ADAPTER_AUDIT.md`, `docs/audit/PR_598_IOS_BMI_THIN_CLIENT_DEDUP_AUDIT.md`.
- **Entry + navigation SoT:** `ios/PulsePlate/PulsePlateApp.swift` → gate → `RootTabs()`.
  Anchor: `docs/roadmap/IOS_ROADMAP.md`.
- **Scope discipline:** iOS-only PRs must not mix web/backend/analytics/deeplinks/Lottie unless explicitly planned.
  Anchor: `ios/AGENTS.md` (“PR-653 scope guard (P0 Welcome)”).

---

## 1) Current “App-visible” state (repo-truth)

### ✅ Welcome Gate (P0) — done

- **Status:** shipped (PR-653)
- **What you can see:** 4-screen welcome onboarding shown once per install.
- **Persistence key:** `has_seen_welcome_v1` (versioned)
- **Localization:** RU/EN/ES (`onboarding.welcome.*`)
- **Audit:** `docs/audit/PR_653_P0_WELCOME_ONBOARDING_4SCREENS_AUDIT.md`

---

## 2) Next P0 (Release-safety) — must land before scaling feature surface

### ✅ P0-A) Remove placeholder PRO key fallback (release-safe) — done

- **Backlog item:** `docs/roadmap/BACKLOG_LEDGER.md` (“iOS: Remove placeholder PRO key fallback…”)
- **Status:** shipped (PR-656)
- **Goal:** no implicit placeholder key (or similar) returned in any build configuration.
- **App-visible outcome:** missing-key state becomes explicit (clear UX, deterministic).
- **DoD (high level):**
  - No placeholder key string is returned by any provider.
  - Missing-key path is explicit, testable, and user-visible.

### ✅ P0-B) Guard: forbid placeholder API keys in iOS sources — done

- **Backlog item:** `docs/roadmap/BACKLOG_LEDGER.md` (“iOS: Guard test forbids placeholder API keys…”)
- **Status:** shipped (PR-657)
- **Goal:** CI fails if placeholder keys appear in `ios/PulsePlate/**`.
- **Implementation constraint:** avoid false positives (fixtures/mocks allowlist as needed).

---

## 3) “Backend → iOS” delivery map (make it visible)

This is the canonical mapping format for turning backend capability into a **ship-ready iOS surface**.

> **Rule of thumb:** each item below should be delivered as a **thin vertical slice**: API contract → iOS DTO decode/encode → SwiftUI screen → a11y + i18n → tests → TestFlight demo.

### 3.1 Free-tier core (must feel complete)

#### Slice F1) BMI calculate (canonical)

- **Backend:** `POST /api/v1/bmi/calculate` (exists; contract-driven)
- **iOS surfaces:** BMI calculator screen + results screen
- **Guards:** no BMI thresholds/logic locally (already enforced)
- **Evidence/audit:** `docs/audit/PR_598_IOS_BMI_THIN_CLIENT_DEDUP_AUDIT.md`
- **Visibility:** record a 20–30s screen capture “input → result → back”.

#### Slice F2) Error contract polish (422/403/5xx UX)

- **Goal:** user never sees “undefined”, raw JSON, or silent failures.
- **iOS outcome:** deterministic error banners/states (localized), retry path, offline messaging.

### 3.2 Pro/VIP surfaces (contract-first, gated by backend)

> iOS must not infer tier; it should render backend-provided tier/paywall hook data.

#### Slice P1) Key entry & tier UX (safe + explicit)

- **Goal:** clear “enter key / upgrade” flow (no placeholder logic).
- **Constraints:** no new networking paths; use existing `APIClient`.
- **App Store rule:** “Enter PRO key” is internal/TestFlight-only UX (debug tools / feature flag). Public release must use a copy-first paywall and StoreKit purchase flow (separate scope).
- **Visibility:** TestFlight build where user can:
  - open key entry
  - paste key
  - see success/failure states deterministically

#### Slice P2) Plate (PRO) — canonical daily nutrition endpoint alignment

- **Goal:** iOS Plate uses canonical `GET /api/v1/pro/nutrition/daily` (contract-first) with `X-API-Key` + required profile query params.
- **Forbidden:** treat `GET /api/nutrition/{date}` legacy alias as iOS source-of-truth (deprecated; guard/contract drift risk).
- **Tracking:** `docs/roadmap/BACKLOG_LEDGER.md` (P1: “iOS: Plate (PRO) align…”), plus P0 security item for alias guard enforcement.

#### Slice V1) Plan / Weekly plan reader (if backend supports)

- **Goal:** show the plan in a “trustworthy Apple-native” way (loading/error/empty states).
- **Note:** if backend endpoint contract is still changing, keep iOS implementation behind a debug-only toggle until stable.

---

## 4) “Visibility loop” (so you *see* progress daily)

### Daily (required for iOS work days)

- **Build:** TestFlight (or local simulator build) with the latest Welcome Gate + current slice.
- **Screenshots:** 6–10 screenshots:
  - Light/Dark
  - RU/EN (ES weekly spot-check)
  - Dynamic Type (one screenshot at larger text)
- **Video:** 20–30s capture of the main happy path.
- **Changelog:** 5 bullets posted in PR description or a daily note (“What changed in the app today”).

### Weekly (required)

- **Demo script:** 2-minute deterministic demo flow (no flaky backend dependencies).
- **Ledger sync:** any deferred work is written to `docs/roadmap/BACKLOG_LEDGER.md` with DoD.

---

## 5) How this connects to agent workflow

All iOS+frontend slices must follow:

- `docs/orchestration/workflow.md` (canonical orchestration)
- **iOS+frontend playbook:** `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`
