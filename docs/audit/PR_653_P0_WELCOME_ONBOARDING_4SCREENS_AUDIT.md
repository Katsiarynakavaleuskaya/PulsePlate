## Audit Meta

- **PR**: PR-653
- **Branch**: `product/p0-welcome-onboarding-4screens-pr653`
- **Owner**: @katsiaryna_kavaleuskaya
- **Date**: 6 February 2026
- **Scope**: P0 product onboarding only (4-screen Welcome), **iOS only**
- **Non-goals**: web, backend changes, tier/guard changes, any new BMI logic on clients, new dependencies, visual redesign, analytics, deep links, Lottie

---

## Goal (canonical)

Introduce a **4-screen Welcome onboarding** that:

- shows **once** per install (deterministic persistence, **versioned key**),
- supports **RU/EN/ES localization** (repo already ships all 3),
- is implemented via **one gate decision point** on iOS:
  - iOS: app entry → gate → `RootTabs()`

---

## Current State (repo-grounded)

### iOS entrypoint

- App entry is `ios/PulsePlate/PulsePlateApp.swift` → `RootTabs()` inside `WindowGroup`.
- `RootTabs` is a `TabView` that owns the primary UI surface.
- iOS localization already includes `en.lproj`, `ru.lproj`, `es.lproj` `Localizable.strings`.

---

## Proposed Design (one path, deterministic)

### Persistence keys (versioned)

Use a single versioned key for both clients:

- **Key**: `has_seen_welcome_v1`
- **iOS storage**: `@AppStorage("has_seen_welcome_v1")` (UserDefaults)

**Why versioned**:

- Allows future content changes (`v2`) without ambiguous migrations.
- Avoids “stuck” behavior if copy/UI evolves and we need to reshow onboarding intentionally.

### Language policy (RU/EN/ES)

**Question**: does onboarding “in 2 languages” conflict with “3 languages planned”?

- **No**, as long as fallback works (web already falls back to `en`; iOS uses system/app localization fallback).
- **However**, shipping RU+EN only while ES exists in-app creates a **partially localized first-run experience** (low trust moment).

**P0 decision**: add Welcome copy keys for **RU/EN/ES** in the same PR.

### iOS gate (SwiftUI)

- Single decision point at app entry:
  - `PulsePlateApp` shows `WelcomeGateView()`
  - Gate decides:
    - `WelcomeFlowView` (4 screens) if `has_seen_welcome_v1 == false`
    - `RootTabs()` otherwise

**Hard constraint**: no changes to backend; no domain logic in iOS (thin client policy holds).

---

## Copy & Localization Keys (RU/EN/ES) — P0 set

### Key namespace (web + iOS)

To match existing structure (`onboarding.enterKey.*`), use:

- `onboarding.welcome.*` (web JSON + iOS `Localizable.strings`)

### Recommended key set

- `onboarding.welcome.screen1.title`
- `onboarding.welcome.screen1.body`
- `onboarding.welcome.screen2.title`
- `onboarding.welcome.screen2.body`
- `onboarding.welcome.screen3.title`
- `onboarding.welcome.screen3.body`
- `onboarding.welcome.screen4.title`
- `onboarding.welcome.screen4.body`
- `onboarding.welcome.cta.continue`
- `onboarding.welcome.cta.back`
- `onboarding.welcome.cta.start`
- `onboarding.welcome.stepA11y` (format: “Step %d of %d” / “Шаг %d из %d” / “Paso %d de %d”)

### Copy (EN)

- **S1 title**: PulsePlate — your nutrition on track
- **S1 body**: Set your goals once. We’ll keep your plan, plate, and progress in sync.
- **S2 title**: Private by default
- **S2 body**: Your inputs stay on your device unless you explicitly export or share.
- **S3 title**: Pick your setup
- **S3 body**: Choose language, units, and a goal. You can change this anytime.
- **S4 title**: Ready to start
- **S4 body**: Let’s build a simple plan you can follow today.
- **CTA**: Continue / Back / Get started
- **A11y step**: Step %d of %d

### Copy (RU)

- **S1 title**: PulsePlate — питание под контролем
- **S1 body**: Настрой цели один раз. План, тарелка и прогресс будут согласованы.
- **S2 title**: Приватность по умолчанию
- **S2 body**: Данные остаются на устройстве, пока вы сами не экспортируете или не поделитесь.
- **S3 title**: Выберите настройки
- **S3 body**: Язык, единицы и цель можно изменить в любой момент.
- **S4 title**: Можно начинать
- **S4 body**: Соберём простой план, который реально выполнить уже сегодня.
- **CTA**: Дальше / Назад / Начать
- **A11y step**: Шаг %d из %d

### Copy (ES)

- **S1 title**: PulsePlate — tu nutrición bajo control
- **S1 body**: Configura tus objetivos una vez. Mantendremos plan, plato y progreso sincronizados.
- **S2 title**: Privado por defecto
- **S2 body**: Tus datos quedan en tu dispositivo hasta que decidas exportar o compartir.
- **S3 title**: Elige tu configuración
- **S3 body**: Idioma, unidades y objetivo: puedes cambiarlo cuando quieras.
- **S4 title**: Listo para empezar
- **S4 body**: Hagamos un plan simple que puedas seguir hoy.
- **CTA**: Continuar / Atrás / Empezar
- **A11y step**: Paso %d de %d

**Notes (tone/claims)**:

- Avoid medical claims; keep “wellness / planning / tracking” language.
- Keep sentences short for small screens and better VoiceOver cadence.

---

## Audit Questions (expanded) + Answer (argued)

### Q1) Where is the decision “show EnterKey” handled today (iOS + web)?

- **Web**: `frontend/src/App.tsx` wraps routes with `<RequireKey>` based on `requiresAuth` from `config/routes.ts`. `/enter-key` itself is an explicit route.
- **iOS**: there is no `EnterKey` concept in SwiftUI routing surfaced at app entry (entry goes straight to `RootTabs()`).

**Implication**: our Welcome must not hijack or rewrite web auth gating; it must sit **before** routes but respect `/enter-key`.

### Q2) Is there already an onboarding persistence key?

- **Web**: `EnterKey` stores API key via auth (`auth.setApiKey(trimmed, true)`), but this is **not** a “welcome seen” flag.
- **iOS**: no onboarding flag at app entry today (direct `RootTabs()`).

**Decision**: introduce a new dedicated, versioned key `has_seen_welcome_v1`.

### Q3) Are there deep-links/routes that must bypass Welcome?

Known explicit route that must remain reachable even if welcome not yet seen:

- **Web**: `/enter-key` (existing onboarding for API key and VIP/admin access).

Potential candidates (only if required by product workflows):

- `/bmi` (if shared externally as “open BMI calculator”)
- Any future `/?lang=...` query is safe; language selection is already query-driven (`frontend/src/i18n/index.ts`).

**P0 stance**: keep allowlist minimal (`/enter-key`, `/welcome`). Add more only with evidence.

### Q4) How do we prevent redirect loops / “tab bar disappearing” regressions on web?

- Must ensure `/welcome` has `hideTabBar: true` and is allowlisted.
- The guard must be a no-op when already at `/welcome`.
- Keep the tab bar visibility logic intact: it derives from `routes.find(route.path === location.pathname)`.

### Q5) What happens when storage is unavailable (private mode, blocked localStorage)?

Web storage can throw in hardened browser modes.

- **Requirement**: welcome should still be usable (user can proceed) even if persistence fails.
- **Policy**: “best-effort persistence”:
  - try/catch for `localStorage` reads/writes
  - if write fails, continue session without crashing; welcome may reappear next reload (acceptable P0).

### Q6) Accessibility / HIG (P0, no redesign)

**iOS**:

- Dynamic Type: avoid hard-coded fixed heights; use system typography.
- VoiceOver: each screen needs:
  - single clear heading (accessibility trait: header),
  - primary CTA with explicit label (“Continue”, “Get started”).

**Web**:

- Provide semantic headings (`h1`), focus management on route change (ensure focus is not trapped).
- Buttons must have visible labels; avoid icon-only controls.

### Q7) Analytics/telemetry (should we add now?)

**Default**: out of scope for this P0 PR unless analytics is already a project invariant.

If analytics exists already and adding 2 events is trivial (no new deps):

- `welcome_viewed_{screen_index}`
- `welcome_completed`

Otherwise: defer (avoid scope creep).

### Q8) Can Welcome break tier gating / security guarantees?

No, if we keep constraints:

- No backend calls added.
- No client-side “premium logic” introduced.
- `EnterKey` remains reachable and `RequireKey` logic remains unchanged.

### Q9) Rollback / hotfix strategy

Rollback is safe because:

- Gate is purely client-side.
- Removing the gate returns to prior behavior:
  - iOS → `RootTabs()` as entry
  - web → render routes as today

We must keep `has_seen_welcome_v1` as a harmless leftover key if rollback happens.

### Q10) Tests: what is the minimum deterministic coverage?

- **Web** (preferred): unit test of the guard decision:
  - given `has_seen_welcome_v1` missing and path not allowlisted → redirects to `/welcome`
  - given key present → no redirect
  - given path `/enter-key` → no redirect
- **iOS** (P0 minimum): unit test for gate state machine (no UI snapshot required):
  - default is “show welcome”
  - after completion flag set → show `RootTabs`

---

## Evidence (commands to run; paste raw lines + exit codes)

> Note: follow repo policy — evidence should include the exact command, 1–3 raw output lines, and exit code.

### iOS evidence

- Gate wiring:
  - `rg -n "has_seen_welcome_v1|WelcomeGateView|WelcomeFlowView|onboarding\\.welcome" ios/PulsePlate`
- Tests:
  - `make ios-test` (or project-canonical xcodebuild command)

### Verified (local evidence)

- **Command**: `rg -n "has_seen_welcome_v1|WelcomeGateView|WelcomeFlowView|onboarding\\.welcome" ios/PulsePlate`
  - **Output (raw)**:
    - `ios/PulsePlate/ru.lproj/Localizable.strings:56:"onboarding.welcome.screen1.title" = "PulsePlate — питание под контролем";`
    - `ios/PulsePlate/Welcome/WelcomeGateView.swift:4:    @AppStorage("has_seen_welcome_v1") private var hasSeenWelcome: Bool = false`
    - `ios/PulsePlate/PulsePlateApp.swift:7:            WelcomeGateView()`
  - **Exit code**: `0`

- **Command**: `make ios-test`
  - **Output (raw)**:
    - `** TEST SUCCEEDED **`
    - `✅ iOS тесты пройдены`
  - **Exit code**: `0`

---

## Smoke checklist (manual, deterministic)

### iOS (fresh install)

- Launch → Welcome screen 1 appears (localized by device/app language)
- Complete flow → lands in tabs (`RootTabs`)
- Kill app → relaunch → tabs appear (welcome does not reappear)

---

## Risks + Mitigations (P0)

- **Risk: partial localization first-run** → **Mitigation**: ship RU/EN/ES welcome copy in same PR.

---

## Decision Log

- **D1**: Use a **single, versioned key** `has_seen_welcome_v1` across clients for deterministic behavior.
- **D2**: Welcome is localized for **RU/EN/ES** (repo already ships all 3; avoid partial first-run).
- **D3**: No backend changes; onboarding is purely iOS client UX and persistence.
