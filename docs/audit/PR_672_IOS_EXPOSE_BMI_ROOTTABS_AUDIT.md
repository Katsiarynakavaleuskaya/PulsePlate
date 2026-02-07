# PR-672 Audit — iOS: Expose BMI screen in RootTabs

**Date**: 7 February 2026
**Branch**: `feat/ios-expose-bmi-root-tabs-pr-672`
**Type**: iOS runtime + audit doc

---

## Scope

- Expose the existing BMI screen as a first-class entrypoint from `RootTabs` (TabView).
- No BMI math / thresholds / categorization logic is added on iOS (thin client policy).

## Non-scope

- No backend changes.
- No refactors or “drive-by” cleanups outside RootTabs + BMI entry wiring.
- No new domain logic or interpretation on the client.

---

## Evidence (repo-truth)

### RootTabs exists and defines TabView items

- `ios/PulsePlate/Views/RootTabs.swift:3-20`

Raw excerpt:

```text
TabView {
  HomeView().tabItem { Label("Home", systemImage: "house") }
  PlateViewPP().tabItem { Label("Plate", systemImage: "fork.knife") }
  ProgressViewPP().tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }
  WeeklyProgressView().tabItem { Label("Неделя", systemImage: "calendar") }
  ProfileView().tabItem { Label("Profile", systemImage: "person") }
}
```

### BMICalculatorScreen exists but is not wired from RootTabs (currently “dangling”)

- `ios/PulsePlate/Screens/BMICalculatorScreen.swift:3-133`
- No references from RootTabs before this PR: `ios/PulsePlate/Views/RootTabs.swift:3-20`

### iOS BMI adapter exists and is thin (transport-only)

- `ios/PulsePlate/Services/BMIService.swift:3-35`
  - Calls canonical endpoint: `path: "/api/v1/bmi/calculate"` (`:30-34`)
  - Explicitly forbids BMI logic (doc comment): `:14-18`

### Existing tests cover BMI transport/service (but not RootTabs)

There are multiple unit tests asserting the canonical BMI path and DTO behavior:

- `ios/PulsePlateTests/BMI/BMIServiceTests.swift:6-146`
- `ios/PulsePlateTests/Services/BMIServiceThinAdapterTests.swift:4-151`
- `ios/PulsePlateTests/Networking/APIClientTests.swift:25-94`

And there are **no existing tests** referencing RootTabs/TabView/tabItem:

```bash
rg -n "RootTabs|TabView|tabItem|UITabBar|NavigationStack" ios/PulsePlateTests ios/PulsePlateUITests -S
```

Raw stdout:

```text
# (no output)
```

Exit code: 1

### i18n pattern for tab labels

`RootTabs` currently uses hardcoded `Label("...")` strings (not Localizable keys):

- `ios/PulsePlate/Views/RootTabs.swift:6-10`

Localization exists broadly via `NSLocalizedString(...)` and `LocalizedStringKey(...)`, but no tab-label keys
were found in this pass:

- `ios/PulsePlate/en.lproj/Localizable.strings` exists (and `ru/es` equivalents)

---

## Decision

- Implement BMI exposure as a **new Tab** in `RootTabs` (TabView-level entrypoint), matching the ledger wording
  “Expose BMI screen from Home / RootTabs”.

---

## Implementation plan (one path)

1. Update `ios/PulsePlate/Views/RootTabs.swift`
   - Add a new `.tabItem` for BMI
   - Content: `BMICalculatorScreen()`
   - Label + icon: follow existing RootTabs pattern (hardcoded label + SF Symbol)

2. Keep `ios/PulsePlate/Screens/BMICalculatorScreen.swift` unchanged unless a minimal navigation wrapper is needed.

3. Tests
   - No existing RootTabs UI/unit test harness found; do not introduce new test frameworks in this PR.
   - Rely on existing BMI service/transport tests + `make ios-test`.

---

## Pre-push checklist

```bash
pre-commit run --all-files
make ios-test
git diff --name-only origin/main...HEAD
```
