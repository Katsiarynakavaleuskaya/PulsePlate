<!-- markdownlint-disable MD013 -->
# PulsePlate Button Action + Prompt Matrix (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress slice (Web + iOS), plus directly linked downstream CTA flows (setup/paywall/result actions)
**Status:** Canonical visual execution SoT for button-level behavior and prompt handoff

## 1) Purpose + SoT Links

This document is the button-level execution registry for visual/UX delivery in the `Home + Plate + Progress` stream.

Use it together with:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
- `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md`
- `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`
- `docs/sora/PULSEPLATE_SORA_BUTTON_VARIANTS_HPP.md`

### Anchor Stability Protocol

- `file:line` anchors are snapshot evidence for this matrix revision.
- Anchor intent is semantic ownership (button -> flow -> dependency), not immutable line numbers.
- Before PR merge for matrix updates, re-validate anchors and update drifted lines in-place.
- Validation command:

```bash
python scripts/ci/check_docs_phase1_gates.py \
  --files docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md
```

Evidence anchors for current implementation baseline:

- Web Home/Plate/Profile/Progress CTA surfaces: `frontend/src/pages/Home.tsx:34`, `frontend/src/pages/Plate.tsx:37`, `frontend/src/pages/Profile.tsx:25`, `frontend/src/features/progress/ProgressCharts.tsx:120`
- Web route/auth gating: `frontend/src/config/routes.ts:23`, `frontend/src/auth/RequireKey.tsx:13`, `frontend/src/components/PremiumGate.tsx:47`
- iOS Home/Plate/Progress CTA surfaces: `ios/PulsePlate/Views/HomeView.swift:57`, `ios/PulsePlate/Views/PlateView.swift:159`, `ios/PulsePlate/Views/ProgressView.swift:50`
- iOS feature gates and backend attachment: `ios/PulsePlate/Utilities/FeatureFlags.swift:28`, `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift:33`, `ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift:37`, `ios/PulsePlate/Services/ProDailyNutritionService.swift:38`

## 2) Brand/Visual Control Block

- **Mood lock:** minimal + cozy + intelligent + luxury-clean.
- **Palette lock:** Navy `#0F172A`, Blue `#339FFF`, Green `#20C997`, Heart Red `#FF5D5D` (accent-only).
- **Style lock:** flat forms, soft shadows, subtle gradients, readable silhouettes in small sizes.
- **Safety lock:** wellness-lifestyle framing only, never clinical/diagnostic.
- **Anti-drift lock:** no generic AI slop, no neon drift, no copycat style.

Reminder: button/icon prompts must stay wellness-safe and must not include medical promises.
(RU: промпты для кнопок/иконок должны оставаться wellness-safe и не содержать медицинских обещаний.)

## 3) Status Legend

| Status | Meaning |
| --- | --- |
| `Implemented` | Button/CTA behavior exists and is wired in runtime flow. |
| `Partial` | Exists, but behavior is placeholder/incomplete or lacks required production wiring. |
| `Missing` | Required behavior/design state is absent. |
| `Blocked by flag` | Runtime path exists but is intentionally hidden by feature/auth gate. |

## 4) Button Interaction Matrix

Pilot note: `Design Review Reference` stays tool-neutral, but it is provisional
for this bridge PR. Placeholder values such as `PP/... (TBD)` are allowed until
the first Storybook/Penpot review packet lands; final handoff rows must point to
a real Penpot page/frame, Storybook story/MDX path, or Figma node ID when
optional Code Connect work is explicitly in scope.

| Platform | Screen | Button/CTA ID | UI Label | Trigger Type | Calls/Invokes | Next Link/Flow | Backend/API Dependency | Feature/Auth Gate | Exists Now | Missing | Implement Needed | QA Coverage | Design Review Reference | Sora Prompt Stub |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Web | Home | `web.home.open_setup` | Open setup | `Link` | `frontend/src/pages/Home.tsx:34` -> route `/setup` (`frontend/src/config/routes.ts:26`) | Nutrition Setup form (`frontend/src/pages/NutritionSetup/index.tsx:11`) | Downstream submit hits `/api/v1/premium/bmr`, `/api/v1/pro/nutrition/plate`, `/api/v1/pro/nutrition/targets` (`frontend/src/pages/NutritionSetup/hooks.ts:442`) | No route auth gate | Implemented | No explicit click-through route test | Add navigation/flow test (Home -> Setup -> submit) | Presence check: `frontend/src/pages/__tests__/Home.test.tsx:17` | `PP/Web/Home/QuickActions/OpenSetup/Button/Default (TBD)` | `stub://cta/primary/setup` |
| Web | Home | `web.home.open_plate` | Open plate | `Link` + guarded route | `frontend/src/pages/Home.tsx:37` + `RequireKey` (`frontend/src/auth/RequireKey.tsx:13`) | `/plate` if API key, else redirect `/enter-key` | No direct API on click; downstream Plate flow | `requiresAuth=true` on `/plate` (`frontend/src/config/routes.ts:28`) | Implemented | No Home-level lock visual/tooltip before redirect | Add optional disabled/locked variant in Home quick actions | No redirect assertion test for this button | `PP/Web/Home/QuickActions/OpenPlate/Button/Default (TBD)` | `stub://cta/secondary/open-plate` |
| Web | Home | `web.home.open_progress` | Open progress | `Link` + guarded route | `frontend/src/pages/Home.tsx:40` + `RequireKey` (`frontend/src/auth/RequireKey.tsx:13`) | `/progress` if API key, else `/enter-key` | No direct API on click; downstream charts export is local | `requiresAuth=true` on `/progress` (`frontend/src/config/routes.ts:29`) | Implemented | No CTA-specific guard UX hint | Add consistent pre-click guard hint for auth-required CTAs | No redirect assertion test for this button | `PP/Web/Home/QuickActions/OpenProgress/Button/Default (TBD)` | `stub://cta/secondary/open-progress` |
| Web | Home | `web.home.open_pro` | Open Pro | `Link` | `frontend/src/pages/Home.tsx:43` -> `/pro` (`frontend/src/config/routes.ts:31`) | Pro paywall page (`frontend/src/pages/Pro/ProPaywallPage.tsx:7`) | No API call on click; modal path in `BeforeAfter` | No route auth gate | Implemented | Purchase path intentionally disabled on `/pro` page (`purchaseDisabled`) | Keep as explicit "coming soon" until billing backend wiring is approved | No Home-specific click flow test | `PP/Web/Home/QuickActions/OpenPro/Button/Default (TBD)` | `stub://cta/secondary/open-pro` |
| Web | Plate | `web.plate.open_setup` | Open setup | `Link` inside gated content | `frontend/src/pages/Plate.tsx:37` inside `PremiumGate` (`frontend/src/pages/Plate.tsx:30`) | `/setup` | Same setup endpoints via downstream submit (`frontend/src/pages/NutritionSetup/hooks.ts:442`) | Hidden by `isPremium=false` inert preview (`frontend/src/components/PremiumGate.tsx:33`) | Implemented | Non-premium explanatory locked-state microcopy is minimal | Add richer locked-state explanation + visual spec | Link existence tested with mocked gate: `frontend/src/pages/__tests__/Plate.test.tsx:56` | `PP/Web/Plate/ProControls/OpenSetup/Button/Default (TBD)` | `stub://cta/primary/pro-open-setup` |
| Web | Plate | `web.plate.open_progress` | Open progress | `Link` inside gated content | `frontend/src/pages/Plate.tsx:40` inside `PremiumGate` | `/progress` | No direct API on click | Same premium-gate constraint | Implemented | No dedicated CTA route test | Add route test for premium and non-premium paths | No dedicated click-through test | `PP/Web/Plate/ProControls/OpenProgress/Button/Default (TBD)` | `stub://cta/secondary/pro-open-progress` |
| Web | Plate | `web.plate.premium_gate_cta` | `t("paywall.cta")` | `button` | `frontend/src/components/PremiumGate.tsx:47` (`setOpen(true)`) | Opens `BeforeAfter` modal (`frontend/src/components/PremiumGate.tsx:61`) | Analytics only in modal (`frontend/src/components/Paywall/BeforeAfter.tsx:64`) | Rendered only when `isPremium=false` | Implemented | Purchase action hook is empty in gate (`onPurchase`) | Wire monetization callback + success/failure states | Gate open test: `frontend/src/components/__tests__/PremiumGate.test.tsx:32` | `PP/Web/Plate/PremiumGate/UnlockCTA/Button/Default (TBD)` | `stub://cta/paywall-unlock` |
| Web | Progress | `web.progress.export_pdf` | Export PDF | `button` | `frontend/src/features/progress/ProgressCharts.tsx:120` -> `exportToPDF()` (`frontend/src/features/progress/ProgressCharts.tsx:64`) | Local file save `progress-report.pdf` | Local html2canvas + jsPDF import, no backend call | No gate | Implemented | No deterministic click test for success/failure branch | Add click test for `showError` path + fallback behavior | Presence only: `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:41` | `PP/Web/Progress/Header/ExportPDF/Button/Default (TBD)` | `stub://cta/utility/export-pdf` |
| iOS | Home | `ios.home.bmi_calculator` | BMI Calculator | `NavigationLink` | `ios/PulsePlate/Views/HomeView.swift:57` -> `BMICalculatorScreen()` | BMI flow screen | Downstream BMI API surface (`app/routers/bmi.py:198`) | No explicit flag | Implemented | No button-level nav test | Add deterministic nav smoke test | No dedicated UI test in `PulsePlateTests` | `PP/iOS/Home/QuickActions/BMI/Row/Default (TBD)` | `stub://icon-nav/bmi` |
| iOS | Home | `ios.home.profile_setup` | Profile Setup | `NavigationLink` | `ios/PulsePlate/Views/HomeView.swift:67` -> `ProfileView()` | Profile flow | Indirect dependency: profile data consumed by Plate service (`ios/PulsePlate/Models/NutritionData.swift:183`) | No explicit flag | Implemented | No nav + state test from Home | Add Home quick-action navigation tests | No dedicated UI test | `PP/iOS/Home/QuickActions/ProfileSetup/Row/Default (TBD)` | `stub://icon-nav/profile-setup` |
| iOS | Home | `ios.home.open_plate` | Open Plate | `NavigationLink` | `ios/PulsePlate/Views/HomeView.swift:77` -> `PlateViewPP()` | Plate screen with state machine | Canonical daily endpoint `/api/v1/pro/nutrition/daily` (`ios/PulsePlate/Services/ProDailyNutritionService.swift:38`) | Runtime pro-key/profile checks inside service (`ios/PulsePlate/Models/NutritionData.swift:175`) | Implemented | No Home-level click-through tests | Add integration test for Home -> Plate with missing key/profile states | Plate data mapping tests exist, not CTA-level: `ios/PulsePlateTests/PlateViewTests.swift:16` | `PP/iOS/Home/QuickActions/OpenPlate/Row/Default (TBD)` | `stub://icon-nav/open-plate` |
| iOS | Home | `ios.home.weekly_plan_reader` | Weekly Plan Reader | `NavigationLink` | `ios/PulsePlate/Views/HomeView.swift:96` -> `makeWeeklyPlanReaderScreen()` | Weekly plan reader screen | `/api/v1/pro/meal/weekly` via VM default path (`ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift:33`) | `FeatureFlags.weeklyPlanReaderEnabled` (`ios/PulsePlate/Utilities/FeatureFlags.swift:28`) | Blocked by flag | Release path disabled by default; share/VIP actions still TODO (`ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:22`) | Rollout flag strategy + complete VIP/share action wiring | VM auth/error tests: `ios/PulsePlateTests/WeeklyPlanReaderViewModelTests.swift:26` | `PP/iOS/Home/ProTools/WeeklyPlanReader/Row/Flagged (TBD)` | `stub://cta/pro-tool/weekly-plan` |
| iOS | Home | `ios.home.shopping_list_generator` | Shopping List Generator | `NavigationLink` | `ios/PulsePlate/Views/HomeView.swift:106` -> `makeShoppingListScreen()` | Shopping list screen | `/api/v1/pro/meal/shopping-list` via VM (`ios/PulsePlate/ViewModels/ShoppingListReaderViewModel.swift:37`) | Same flag gate as weekly plan (`ios/PulsePlate/Views/HomeView.swift:89`) | Blocked by flag | Backend `weekly_plan_id` path is still 501 (`app/routers/shopping_list_pro.py:68`) | Define production source-of-plan path + release criteria | No dedicated CTA-level tests | `PP/iOS/Home/ProTools/ShoppingList/Row/Flagged (TBD)` | `stub://cta/pro-tool/shopping-list` |
| iOS | Plate | `ios.plate.add_meal` | Add Meal | `button` | `ios/PulsePlate/Views/PlateView.swift:159` (`showMealEntry = true`) | Navigates to `MealEntryView` placeholder (`ios/PulsePlate/Views/PlateView.swift:136`) | No backend yet for add-meal action | No explicit gate | Partial | Destination screen is placeholder (`MealEntryView`) | Implement real add-meal flow + API contract | No dedicated button behavior test | `PP/iOS/Plate/BottomBar/AddMeal/Button/Default (TBD)` | `stub://cta/primary/add-meal` |
| iOS | Plate | `ios.plate.view_details` | View Details | `button` | `ios/PulsePlate/Views/PlateView.swift:164` (`showNutritionDetails = true`) | Navigates to `NutritionDetailsView` placeholder (`ios/PulsePlate/Views/PlateView.swift:139`) | No backend yet for details expansion | No explicit gate | Partial | Destination screen is placeholder (`NutritionDetailsView`) | Implement detailed nutrition drilldown screen | No dedicated button behavior test | `PP/iOS/Plate/BottomBar/ViewDetails/Button/Default (TBD)` | `stub://cta/secondary/view-details` |
| iOS | Plate | `ios.plate.issue_action_dynamic` | Retry / Open Profile / PRO Settings | `button` (dynamic label) | Dynamic action mapping in `PlateIssueView` (`ios/PulsePlate/Views/PlateView.swift:205`) + resolver (`ios/PulsePlate/Models/NutritionData.swift:108`) | Retry fetch / profile nav / pro setup nav | Depends on mapped `PlateLoadIssue` state (`ios/PulsePlate/Models/NutritionData.swift:43`) | Appears only in issue state | Implemented | No deterministic UI tests for action-to-outcome mapping | Add action mapping tests for each issue class | Indirect model tests only: `ios/PulsePlateTests/PlateViewTests.swift:45` | `PP/iOS/Plate/IssueState/PrimaryAction/Button/Stateful (TBD)` | `stub://cta/error-state/dynamic-issue-action` |
| iOS | Progress | `ios.progress.refresh` | Refresh | `button` | `ios/PulsePlate/Views/ProgressView.swift:50` (`fetchNutritionData`) | Reload same screen state | `/api/v1/pro/nutrition/daily` through `NutritionService.fetchNutritionData` (`ios/PulsePlate/Models/NutritionData.swift:168`) | Shown in no-data state | Implemented | No button-level state-machine tests | Add no-data -> loading -> success/error transition tests | No dedicated Progress CTA tests | `PP/iOS/Progress/EmptyState/Refresh/Button/Default (TBD)` | `stub://cta/loading-state/refresh` |
| iOS | Progress | `ios.progress.issue_action_dynamic` | Retry / Open profile / Open PRO setup | `button` (dynamic branch) | `ios/PulsePlate/Views/ProgressView.swift:182` switch on `issue.primaryAction` | Retry fetch or navigate to Profile/Debug tools | Depends on same issue classifier (`ios/PulsePlate/Models/NutritionData.swift:108`) | Appears only in issue state | Implemented | No deterministic UI tests for all three branches | Add branch-level tests for issue action rendering + nav | No dedicated button tests | `PP/iOS/Progress/IssueState/PrimaryAction/Button/Stateful (TBD)` | `stub://cta/error-state/dynamic-issue-action` |
| Web (linked flow) | Paywall Modal | `web.paywall.modal.cta` | `paywall-cta` / purchase label | `button` | `frontend/src/components/Paywall/BeforeAfter.tsx:136` -> analytics + `onPurchase` | Purchase attempt path (currently callback-only) | No billing backend in this path yet | Opened from gate or `/pro` page | Partial | Real purchase backend/client wiring absent | Integrate purchase flow + success/failure UI states | Click test: `frontend/src/components/Paywall/__tests__/BeforeAfter.test.tsx:69` | `PP/Web/Paywall/Modal/PurchaseCTA/Button/Default (TBD)` | `stub://cta/paywall-purchase` |
| Web (linked flow) | Paywall Modal | `web.paywall.modal.cancel` | Cancel | `button` | `frontend/src/components/Paywall/BeforeAfter.tsx:158` -> `onClose` | Close modal and return to previous context | No backend dependency | No gate once modal open | Implemented | No explicit dismiss analytics QA in matrix-level flow | Keep telemetry assertions in paywall integration tests | Cancel test: `frontend/src/components/Paywall/__tests__/BeforeAfter.test.tsx:82` | `PP/Web/Paywall/Modal/Cancel/Button/Default (TBD)` | `stub://cta/paywall-cancel` |
| Web (linked flow) | Nutrition Setup Form | `web.setup.submit_calculate` | Calculate plate | `button type=submit` | `frontend/src/pages/NutritionSetup/SetupForm.tsx:164` -> `submit()` (`frontend/src/pages/NutritionSetup/SetupForm.tsx:49`) | Form -> ResultView transition (`frontend/src/pages/NutritionSetup/index.tsx:27`) | Calls BMR/plate/targets via hooks in result (`frontend/src/pages/NutritionSetup/hooks.ts:442`) | No route auth gate; API auth handled by endpoint/headers | Implemented | No end-to-end submit test covering all three API calls | Add integration test with mocked API responses and auth errors | No direct SetupForm submit test in current suite | `PP/Web/Setup/Form/Calculate/Button/Default (TBD)` | `stub://cta/primary/calculate-plate` |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.retry` | Try again | `button` | `frontend/src/pages/NutritionSetup/ResultView.tsx:71` -> `setRetryKey` (`frontend/src/pages/NutritionSetup/ResultView.tsx:33`) | Re-fetch result data | Re-triggers same setup endpoints (`frontend/src/pages/NutritionSetup/hooks.ts:547`) | Appears on error state | Implemented | No contract test for all auth/error branches in retry mode | Add retry tests for 401/403 + generic failure mapping | Retry test exists: `frontend/src/pages/NutritionSetup/__tests__/ResultView.test.tsx:354` | `PP/Web/Setup/Result/Error/Retry/Button/Default (TBD)` | `stub://cta/error-state/retry` |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.edit` | Edit data / Edit form | `button` | `frontend/src/pages/NutritionSetup/ResultView.tsx:78` and header edit at `frontend/src/pages/NutritionSetup/ResultView.tsx:103` | Return to Setup form (`setValues(null)`) | No direct API call; local state transition | No gate | Implemented | Two edit entrypoints share behavior, no unified UX spec | Create one visual/state spec for both edit triggers | Edit action test: `frontend/src/pages/NutritionSetup/__tests__/ResultView.test.tsx:348` | `PP/Web/Setup/Result/Header/Edit/Button/Default (TBD)` | `stub://cta/secondary/edit-input` |

## 5) Prompt Stub Templates (for Sora Prompt Engineer)

These are templates, not final production prompts.

### 5.1 Icon Stub

```text
Template: ICON_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Navigation/support icon for CTA.
Style lock: flat, soft shadows, subtle gradients, palette locked (#0F172A #339FFF #20C997, #FF5D5D accent only).
Safety: wellness lifestyle, not medical.
Negative: no generic ai slop, no glossy 3d blobs, no neon, no copycat brand style.
Output: small-size readable icon (24/32 px), clear silhouette.
```

### 5.2 Primary CTA Stub

```text
Template: CTA_PRIMARY_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Primary action emphasis with calm trust tone.
Style lock: luxury-clean, high contrast, readable label.
Safety lock: no diagnostic claims, no cure framing.
Negative: no manipulative urgency, no fear tone.
Output: default/hover(or pressed)/focus-visible states.
```

### 5.3 Secondary CTA Stub

```text
Template: CTA_SECONDARY_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Supportive alternative action, lower visual weight than primary.
Style lock: same family as primary, reduced emphasis.
Safety + negative constraints: same as primary.
Output: default + interactive states with token-aligned contrast.
```

### 5.4 Disabled/Locked Stub

```text
Template: CTA_DISABLED_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Clearly non-interactive state with understandable affordance.
Style lock: muted but readable, not "hidden".
Safety: messaging remains respectful and non-shaming.
Negative: no "error red" unless truly error state.
Output: disabled visuals + optional lock affordance style.
```

### 5.5 Loading Stub

```text
Template: CTA_LOADING_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Show in-progress state without anxiety.
Style lock: subtle motion, reduced-motion safe.
Safety: no flashing/jitter, no panic cues.
Negative: no dramatic animation loops.
Output: loading spinner/progress variant + text legibility.
```

### 5.6 Error Stub

```text
Template: CTA_ERROR_STUB_V1
Target: {platform}/{screen}/{button_id}
Intent: Recovery action state (retry/edit/help) with calm clarity.
Style lock: clear hierarchy, readable error context.
Safety lock: no medical implication, no fear framing.
Negative: no blame language, no body-shaming, no copycat visual tone.
Output: retry and secondary action pair with accessible contrast.
```

## 6) Visual Variant Mapping (Button ID -> Variant/Prompt/Placement)

Behavior ownership remains in Section 4. This section maps each CTA ID to visual variant and prompt base IDs.

| Button/CTA ID | Recommended Variant | Placement Zone | Sora Prompt ID Base | Visual SoT Reference |
| --- | --- | --- | --- | --- |
| `web.home.open_setup` | `V1` | `W_HOME_QA_GRID` | `SORA_BTN_web_home_open_setup_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.home.open_plate` | `V3` | `W_HOME_QA_GRID` | `SORA_BTN_web_home_open_plate_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.home.open_progress` | `V3` | `W_HOME_QA_GRID` | `SORA_BTN_web_home_open_progress_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.home.open_pro` | `V2` | `W_HOME_QA_GRID` | `SORA_BTN_web_home_open_pro_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.plate.open_setup` | `V1` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_open_setup_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.plate.open_progress` | `V3` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_open_progress_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.plate.premium_gate_cta` | `V2` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_premium_gate_cta_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.progress.export_pdf` | `V3` | `W_PROGRESS_HEADER_UTIL` | `SORA_BTN_web_progress_export_pdf_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.home.bmi_calculator` | `V1` | `I_HOME_QUICK_ACTIONS` | `SORA_BTN_ios_home_bmi_calculator_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.home.profile_setup` | `V1` | `I_HOME_QUICK_ACTIONS` | `SORA_BTN_ios_home_profile_setup_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.home.open_plate` | `V1` | `I_HOME_QUICK_ACTIONS` | `SORA_BTN_ios_home_open_plate_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.home.weekly_plan_reader` | `V3` | `I_HOME_PRO_TOOLS` | `SORA_BTN_ios_home_weekly_plan_reader_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.home.shopping_list_generator` | `V3` | `I_HOME_PRO_TOOLS` | `SORA_BTN_ios_home_shopping_list_generator_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.plate.add_meal` | `V1` | `I_PLATE_BOTTOMBAR_PRIMARY` | `SORA_BTN_ios_plate_add_meal_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.plate.view_details` | `V3` | `I_PLATE_BOTTOMBAR_PRIMARY` | `SORA_BTN_ios_plate_view_details_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.plate.issue_action_dynamic` | `V1` | `I_PLATE_ISSUE_RECOVERY` | `SORA_BTN_ios_plate_issue_action_dynamic_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.progress.refresh` | `V1` | `I_PROGRESS_EMPTY_RECOVERY` | `SORA_BTN_ios_progress_refresh_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `ios.progress.issue_action_dynamic` | `V1` | `I_PROGRESS_ISSUE_RECOVERY` | `SORA_BTN_ios_progress_issue_action_dynamic_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.paywall.modal.cta` | `V2` | `W_PAYWALL_MODAL_FOOTER` | `SORA_BTN_web_paywall_modal_cta_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.paywall.modal.cancel` | `V3` | `W_PAYWALL_MODAL_FOOTER` | `SORA_BTN_web_paywall_modal_cancel_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.submit_calculate` | `V1` | `W_SETUP_FORM_FOOTER` | `SORA_BTN_web_setup_submit_calculate_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.result.retry` | `V1` | `W_SETUP_RESULT_ACTIONS` | `SORA_BTN_web_setup_result_retry_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.result.edit` | `V3` | `W_SETUP_RESULT_ACTIONS` | `SORA_BTN_web_setup_result_edit_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |

## 7) Execution Queue (Priority)

| Priority | Item | Why | Target PR | Owner |
| --- | --- | --- | --- | --- |
| `P0` | Replace iOS Plate placeholders behind `Add Meal` and `View Details` (`ios/PulsePlate/Views/PlateView.swift:136`) | Core CTA routes end in placeholder screens; blocks production-level UX continuity | Next iOS follow-up after current backend/security stream | iOS + Design |
| `P0` | Add deterministic CTA behavior tests for iOS Home/Plate/Progress primary actions (`ios/PulsePlate/Views/HomeView.swift:57`, `ios/PulsePlate/Views/ProgressView.swift:50`, `ios/PulsePlateTests/PlateViewTests.swift:7`) | CTA actions are defined in runtime views, while current tests are mostly render/data mapping checks rather than button-tap outcome assertions | Same follow-up PR as above | iOS QA |
| `P1` | Wire real purchase path for `PremiumGate` / paywall modal (`frontend/src/components/PremiumGate.tsx:67`) | CTA exists but monetization action is callback-only | Web monetization PR | Frontend + Product |
| `P1` | Add Web click-through integration tests for Home/Plate auth-gated CTAs (`frontend/src/pages/__tests__/Home.test.tsx:17`, `frontend/src/pages/__tests__/Plate.test.tsx:56`, `frontend/src/auth/RequireKey.tsx:13`) | Presence tests exist, but route-guard redirect and full CTA navigation outcomes are not asserted end-to-end | Web parity test hardening PR | Frontend QA |
| `P2` | Backfill `Design Review Reference` for all matrix rows using `PP/<Platform>/<Screen>/<Component>/<State>` naming and repo-native review links (`docs/roadmap/BACKLOG_LEDGER.md:1634`, `docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md:199`) | Needed for tool-neutral design-to-code traceability and faster handoff review | Design handoff follow-up | Design + FE + iOS |
| `P2` | Normalize row-level prompt files from matrix IDs into a dedicated prompt pack (current baseline: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:245`) | Prompt templates exist in a centralized playbook, but row-level prompt-ID files are not materialized yet for deterministic ops | Sora prompt pack follow-up | Sora Prompt Engineer |

## 8) Security + Safety Notes for Prompt Column

- Do not place secrets, API keys, internal URLs, or proprietary credentials in prompt text.
- Keep all prompt stubs wellness-safe: no medical diagnosis/cure claims.
- Keep anti-copycat guardrails active for every prompt family.
- Any generated visual used in product/social must pass:
  - `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`
  - `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md`

Reminder: the prompt column is for templates and quality control, not for sensitive data.
(RU: колонка prompt предназначена для шаблонов и контроля качества, а не для хранения чувствительных данных.)
<!-- markdownlint-enable MD013 -->
