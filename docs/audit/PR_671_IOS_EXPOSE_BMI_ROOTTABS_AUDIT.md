# PR-671 Audit — iOS: Expose BMI screen in RootTabs

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

- `ios/PulsePlate/Views/RootTabs.swift:4-26`

Raw excerpt:

```text
TabView {
  HomeView().tabItem { Label("Home", systemImage: "house") }
  BMICalculatorScreen().tabItem { Label("BMI", systemImage: bmiTabSymbol) }
  PlateViewPP().tabItem { Label("Plate", systemImage: "fork.knife") }
  ProgressViewPP().tabItem { Label("Progress", systemImage: "chart.line.uptrend.xyaxis") }
  WeeklyProgressView().tabItem { Label("Неделя", systemImage: "calendar") }
  ProfileView().tabItem { Label("Profile", systemImage: "person") }
}
```

### BMICalculatorScreen exists and is now wired from RootTabs (added in this PR)

- `ios/PulsePlate/Screens/BMICalculatorScreen.swift:3-132`
- `ios/PulsePlate/Views/RootTabs.swift:11-16`

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

- `ios/PulsePlate/Views/RootTabs.swift:11-16`

Localization exists broadly via `NSLocalizedString(...)` and `LocalizedStringKey(...)`:

```bash
rg -n "NSLocalizedString\\(" ios/PulsePlate -S --max-count 50
```

Raw stdout (truncated):

```text
ios/PulsePlate/Models/ShoppingList/ShoppingListAdapter.swift:39:            format: NSLocalizedString("shopping_list_total_items_fmt", comment: "Total items format"),
ios/PulsePlate/Models/ShoppingList/ShoppingListAdapter.swift:60:        let header = NSLocalizedString("shopping_list_title", comment: "Shopping List title")
ios/PulsePlate/Models/ShoppingList/ShoppingListAdapter.swift:62:            String(format: NSLocalizedString("shopping_list_source_fmt", comment: "Source format"), dto.meta.source)
ios/PulsePlate/Models/NutritionData.swift:55:    NSLocalizedString(key, comment: "")
ios/PulsePlate/Welcome/WelcomeFlowView.swift:95:        let template = NSLocalizedString("onboarding.welcome.stepA11y", comment: "")
ios/PulsePlate/Models/LocalizationManager.swift:25:        return NSLocalizedString(key, bundle: bundle, comment: "")
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:21:            .navigationTitle(NSLocalizedString("shopping_list_title", comment: ""))
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:35:                NSLocalizedString("shopping_list_empty_title", comment: ""),
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:37:                description: Text(NSLocalizedString("shopping_list_empty_description", comment: ""))
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:42:                Text(NSLocalizedString("shopping_list_error_title", comment: ""))
ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:78:                    Section(header: Text(NSLocalizedString("shopping_list_warnings_title", comment: ""))) {
```

Exit code: 0

```bash
rg -n "LocalizedStringKey" ios/PulsePlate -S --max-count 50
```

Raw stdout (truncated):

```text
ios/PulsePlate/Views/Components/PlateRing.swift:39:        Text(LocalizedStringKey("progress.complete"))
ios/PulsePlate/Views/Components/PlateRing.swift:52:    .accessibilityLabel(LocalizedStringKey("progress.label"))
ios/PulsePlate/Views/Components/ValidationErrorsView.swift:19:            Text(LocalizedStringKey("Error"))
ios/PulsePlate/Welcome/WelcomeFlowView.swift:68:    private var screenTitleKey: LocalizedStringKey {
ios/PulsePlate/Welcome/WelcomeFlowView.swift:77:    private var screenBodyKey: LocalizedStringKey {
ios/PulsePlate/Welcome/WelcomeFlowView.swift:86:    private var primaryCtaKey: LocalizedStringKey {
ios/PulsePlate/Welcome/WelcomeFlowView.swift:90:    private var backKey: LocalizedStringKey {
ios/PulsePlate/Views/Components/LottieAnimationView.swift:102:    var textKey: LocalizedStringKey
ios/PulsePlate/Views/Components/AnimatedFitChef.swift:50:    var textKey: LocalizedStringKey
ios/PulsePlate/Views/Components/VideoPlayerView.swift:132:    var textKey: LocalizedStringKey
ios/PulsePlate/Views/Components/MascotBubble.swift:6:  var textKey: LocalizedStringKey
```

Exit code: 0

No dedicated tab-label keys were observed in `en.lproj/Localizable.strings`:

- `ios/PulsePlate/en.lproj/Localizable.strings` exists (and `ru/es` equivalents)

```bash
rg -n "tab\\.|home_tab|plate_tab|progress_tab|week_tab|profile_tab|bmi_tab" ios/PulsePlate/en.lproj/Localizable.strings -S
```

Raw stdout:

```text
# (no output)
```

Exit code: 1

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
