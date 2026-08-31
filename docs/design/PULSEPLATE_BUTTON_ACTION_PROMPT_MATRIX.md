<!-- markdownlint-disable MD013 -->
# PulsePlate Button Action + Prompt Matrix (H+P+Pr)

**Date:** February 18, 2026
**Scope:** Home + Plate + Progress slice (Web + iOS), plus directly linked downstream CTA flows (setup/Apple-product information/result actions)
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

- Web Home/Plate/Profile/Progress CTA surfaces: `frontend/src/pages/Home.tsx:487`, `frontend/src/pages/Plate.tsx:37`, `frontend/src/pages/Profile.tsx:25`, `frontend/src/features/progress/ProgressCharts.tsx:120`
- Web route/auth gating: `frontend/src/config/routes.ts:23`, `frontend/src/auth/RequireKey.tsx:13`, `frontend/src/components/PremiumGate.tsx:53`
- iOS Home/Plate/Progress CTA surfaces: `ios/PulsePlate/Views/HomeView.swift:98`, `ios/PulsePlate/Views/Home/HomeExperience.swift:195`, `ios/PulsePlate/Views/PlateView.swift:159`, `ios/PulsePlate/Views/ProgressView.swift:50`
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
for this bridge PR under
`docs/architecture/ADR_PENPOT_STORYBOOK_BRIDGE_FALLBACK_SEAM_2026-03-07.md` and
`docs/roadmap/BACKLOG_LEDGER.md` → `Penpot + Storybook fallback bridge for
design handoff`. Placeholder values such as `PP/... (TBD)` are allowed until
the first Storybook/Penpot review packet lands; this exception retires when the
ADR exit criteria are met and active handoff rows point to a real Penpot
page/frame, Storybook story/MDX path, or Figma node ID when optional Code
Connect work is explicitly in scope.

| Platform | Screen | Button/CTA ID | UI Label | Trigger Type | Calls/Invokes | Next Link/Flow | Backend/API Dependency | Feature/Auth Gate | Exists Now | Missing | Implement Needed | QA Coverage | Design Review Reference | Sora Prompt Stub |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Web | Home | `web.home.open_setup` | Open setup | `Link` | `frontend/src/components/cta/HomeOpenSetupCta.tsx:11` -> route `/setup` (`frontend/src/config/routes.ts:26`) | Nutrition Setup form (`frontend/src/pages/NutritionSetup/index.tsx:11`) | Downstream submit hits canonical BMR (`frontend/src/pages/NutritionSetup/hooks.ts:408`), plate (`frontend/src/pages/NutritionSetup/hooks.ts:423`), and targets (`frontend/src/pages/NutritionSetup/hooks.ts:539`) | No route auth gate | Implemented | No full Home -> Setup -> submit browser proof yet | Add the broader browser flow after staging deployment; focused hook and Storybook fixtures cover canonical BMR now | Route handoff test: `frontend/src/pages/__tests__/Home.test.tsx:130`; BMR hook test: `frontend/src/pages/NutritionSetup/__tests__/hooks.test.tsx`; packet: `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_HOME_OPEN_SETUP.md` | `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_HOME_OPEN_SETUP.md` | `stub://cta/primary/setup` |
| Web | Home | `web.home.open_plate` | Open plate | `Link` + guarded route | `frontend/src/pages/Home.tsx:37` + `RequireKey` (`frontend/src/auth/RequireKey.tsx:13`) | `/plate` if secure session is active, else redirect `/enter-key` | No direct API on click; downstream Plate flow | `requiresAuth=true` on `/plate` (`frontend/src/config/routes.ts:28`) | Implemented | No Home-level lock visual/tooltip before redirect | Add optional disabled/locked variant in Home quick actions | Redirect + authenticated route tests: `frontend/src/pages/__tests__/Home.test.tsx:141`, `frontend/src/pages/__tests__/Home.test.tsx:154` | `PP/Web/Home/QuickActions/OpenPlate/Button/Default (TBD)` | `stub://cta/secondary/open-plate` |
| Web | Home | `web.home.open_progress` | Open progress | `Link` + guarded route | `frontend/src/pages/Home.tsx:40` + `RequireKey` (`frontend/src/auth/RequireKey.tsx:13`) | `/progress` if secure session is active, else `/enter-key` | No direct API on click; downstream charts export is local | `requiresAuth=true` on `/progress` (`frontend/src/config/routes.ts:29`) | Implemented | No CTA-specific guard UX hint | Add consistent pre-click guard hint for auth-required CTAs | Redirect + authenticated route tests: `frontend/src/pages/__tests__/Home.test.tsx:141`, `frontend/src/pages/__tests__/Home.test.tsx:154` | `PP/Web/Home/QuickActions/OpenProgress/Button/Default (TBD)` | `stub://cta/secondary/open-progress` |
| Web | Home | `web.home.open_pro` | Learn about PulsePlate for Apple devices | `Link` | Guided Planning → Next action at `frontend/src/pages/Home.tsx:487` -> `/marketing` | Open the information-only Apple product handoff at the public marketing page | No API call, payment helper, entitlement action, or acquisition telemetry | No route auth gate | Implemented | None inside the information-only handoff | Keep the destination informational; a paid Web action requires separate exact admission | Route, destination, and no-`/pro` acquisition-event test: `frontend/src/pages/__tests__/Home.test.tsx` | `PP/Web/Home/GuidedPlanning/AppleProductInfo/Button/Default (TBD)` | `stub://cta/information/apple-product` |
| Web | Home | `web.home.fitchef_show_next_step` | Show my next step | `button` | `SupportChoiceCard` accepts the explicit radio choice and calls `requestFitChefSupportHandoff` once | Renders the latest validated backend-owned product-area pointer inline; opens no route | `POST /api/v1/pro/fitchef/recommend` through shared `api()` cookie-session adapter | Unknown auth blocks submit; backend remains PRO/VIP entitlement authority | Implemented in E1-05B (merge-bound) | Production measurement transport is intentionally absent | Keep pointer inline and non-interactive; any later navigation requires a separate contract | Adapter/component tests: `frontend/src/api/__tests__/fitchefSupportHandoff.test.ts`, `frontend/src/features/fitchef/__tests__/SupportChoiceCard.test.tsx` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` | `stub://cta/primary/fitchef-show-next-step` |
| Web | Home | `web.home.fitchef_confirm_pointer` | I understand this next step | `button` | Acknowledges the current latest validated pointer once in local component state | Inline confirmed state only; nothing opens or runs | No API call | Available only after a validated descriptor | Implemented in E1-05B (merge-bound) | Confirmation has no production transport or product-value authority | Preserve acknowledgement-only semantics; never treat as plan approval | Component confirmation/idempotency tests: `frontend/src/features/fitchef/__tests__/SupportChoiceCard.test.tsx` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` | `stub://cta/secondary/fitchef-confirm-pointer` |
| Web | Home | `web.home.fitchef_dismiss_pointer` | Not now | `button` | Aborts any current request and resets local support-choice state | Remains on `/app`; no navigation, storage, setting, or plan mutation | No API call beyond aborting an already-started request | No additional gate | Implemented in E1-05B (merge-bound) | None inside the bounded dismiss behavior | Keep dismiss explicit, calm, and reversible by selecting again | Abort/dismiss/local-event tests: `frontend/src/features/fitchef/__tests__/SupportChoiceCard.test.tsx` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` | `stub://cta/secondary/fitchef-dismiss-pointer` |
| Web | Plate | `web.plate.open_setup` | Open setup | `Link` inside gated content | `frontend/src/pages/Plate.tsx:37` inside `PremiumGate` (`frontend/src/pages/Plate.tsx:30`) | `/setup` | Same canonical BMR (`frontend/src/pages/NutritionSetup/hooks.ts:408`), plate (`frontend/src/pages/NutritionSetup/hooks.ts:423`), and targets (`frontend/src/pages/NutritionSetup/hooks.ts:539`) calls via downstream submit | Hidden by `isPremium=false` inert preview (`frontend/src/components/PremiumGate.tsx:33`) | Implemented | Non-premium explanatory locked-state microcopy is minimal | Add richer locked-state explanation + visual spec | Premium route + non-premium lock tests: `frontend/src/pages/__tests__/Plate.test.tsx:95`, `frontend/src/pages/__tests__/Plate.test.tsx:148` | `PP/Web/Plate/ProControls/OpenSetup/Button/Default (TBD)` | `stub://cta/primary/pro-open-setup` |
| Web | Plate | `web.plate.open_progress` | Open progress | `Link` inside gated content | `frontend/src/pages/Plate.tsx:40` inside `PremiumGate` | `/progress` | No direct API on click | Same premium-gate constraint | Implemented | Shared premium route and locked-preview coverage live in the combined Plate CTA tests | Split into a dedicated open-progress test only if single-CTA granularity becomes a review requirement | Premium route + non-premium lock tests: `frontend/src/pages/__tests__/Plate.test.tsx:95`, `frontend/src/pages/__tests__/Plate.test.tsx:148` | `PP/Web/Plate/ProControls/OpenProgress/Button/Default (TBD)` | `stub://cta/secondary/pro-open-progress` |
| Web | Plate | `web.plate.premium_gate_cta` | Learn about PulsePlate for Apple devices | `button` | `frontend/src/components/PremiumGate.tsx:53` (`setOpen(true)`) | Open the information-only Apple product handoff in the shared `AppleProductInfoDialog` (`frontend/src/components/PremiumGate.tsx:64`) | No API, payment, entitlement, or acquisition telemetry dependency | Rendered only when `isPremium=false` | Implemented | None inside the bounded information action | Preserve `/bmi`, `/marketing`, and dismissal only; future Web payment needs separate exact admission | Dialog, keyboard, focus-return, localization, and no-acquisition tests: `frontend/src/components/__tests__/PremiumGate.test.tsx` | `PP/Web/Plate/PremiumGate/AppleProductInfo/Button/Default (TBD)` | `stub://cta/information/apple-product` |
| Web | Progress | `web.progress.export_pdf` | Export PDF | `button` | `frontend/src/components/cta/ProgressExportPdfButton.tsx:12` -> `exportToPDF()` (`frontend/src/features/progress/ProgressCharts.tsx:79`) | Local file save `progress-report.pdf` | Local html2canvas + jsPDF import, no backend call | No gate | Implemented | Penpot frame reference still pending | Add explicit Penpot board/frame once Progress header review board exists | Success/error tests: `frontend/src/features/progress/__tests__/ProgressCharts.test.tsx:91`; packet: `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_PROGRESS_EXPORT_PDF.md` | `docs/design/PENPOT_CTA_REVIEW_PACKET_WEB_PROGRESS_EXPORT_PDF.md` | `stub://cta/utility/export-pdf` |
| iOS | Home | `ios.home.bmi_calculator` | Check BMI | `NavigationLink` | `HomeAction.checkBMI` in `ios/PulsePlate/Views/Home/HomeExperience.swift:202` -> lazy destination `BMICalculatorScreen()` at `ios/PulsePlate/Views/HomeView.swift:101` | BMI flow screen | Downstream BMI API is owned by the destination | Available in FREE, paid-incomplete, and unavailable projections; entitlement is not inferred locally | Implemented in Consumer-first Home | None in the bounded projection | Preserve backend-owned calculation and lazy construction | State/action/lazy/localization/render coverage: `ios/PulsePlateTests/HomeExperienceTests.swift` | Existing design reference unchanged | Existing prompt reference unchanged |
| iOS | Home | `ios.home.profile_setup` | Profile / Complete profile | `NavigationLink` | `HomeAction.profile` or `.completeProfile` -> `ProfileView()` at `ios/PulsePlate/Views/HomeView.swift:103` | Profile flow | No API call on Home render | Local profile data means readiness for backend validation only; it never establishes entitlement or backend-confirmed profile truth | Implemented in Consumer-first Home | None in the bounded projection | Refresh readiness on Home reappearance without a new profile framework | State/action/lazy/localization/render coverage: `ios/PulsePlateTests/HomeExperienceTests.swift` | Existing design reference unchanged | Existing prompt reference unchanged |
| iOS | Home | `ios.home.open_plate` | Today's plate | `NavigationLink` | Paid-ready primary `HomeAction.todayPlate` -> `PlateViewPP()` at `ios/PulsePlate/Views/HomeView.swift:105` | Existing Plate screen | Destination owns canonical daily transport | Visible only for `.unlocked` plus normalized `active`/`restored` backend snapshot and locally complete required profile inputs | Implemented in Consumer-first Home | None in the Home projection | Keep downstream nutrition/service authority unchanged | Closed state/action matrix: `ios/PulsePlateTests/HomeExperienceTests.swift` | Existing design reference unchanged | Existing prompt reference unchanged |
| iOS | Home | `ios.home.open_progress` | Progress | `NavigationLink` | `HomeAction.progress` -> `ProgressViewPP()` at `ios/PulsePlate/Views/HomeView.swift:107` | Existing Progress screen | Destination owns its transport | Available as a secondary action in FREE and paid-incomplete states; not used as entitlement evidence | Implemented in Consumer-first Home | None in the bounded projection | Keep navigation lazy and state-independent | Closed state/action matrix: `ios/PulsePlateTests/HomeExperienceTests.swift` | No design-authoring change | No prompt-authoring change |
| iOS | Home | `ios.home.fitchef_coach` | FitChef Coach | `NavigationLink` | Exactly one paid-ready `HomeAction.fitChefCoach` selects the lazy destination at `ios/PulsePlate/Views/HomeView.swift:109`; the concrete `FitChefCoachView` is built at `ios/PulsePlate/Views/HomeView.swift:120` | Unified Coach Hub | Child flows retain networking, consent, descriptor, and outcome ownership | Paid-ready only; `planningDirection` always present, `aiGuidance` controlled only inside the Hub by `FeatureFlags.aiInsightEnabled` | Implemented in Consumer-first Home | No separate AI/support/recommend/outcome Home action | Preserve one entry and lazy child factories | Home oracle plus Hub/child ownership tests: `ios/PulsePlateTests/HomeExperienceTests.swift`, `ios/PulsePlateTests/FitChefCoachViewTests.swift`, `ios/PulsePlateTests/FitChefSupportChoiceRuntimeTests.swift` | No external design write | No prompt-authoring change |
| iOS | Home | `ios.home.weekly_plan_reader` | Week | `NavigationLink` | Paid-ready conditional `HomeAction.week` -> `makeWeeklyPlanReaderScreen()` at `ios/PulsePlate/Views/HomeView.swift:111` | Existing weekly plan reader | Destination owns `/api/v1/pro/meal/weekly` | Existing `FeatureFlags.weeklyPlanReaderEnabled`; flag limits post-admission capability and never creates paid state | Controlled rollout | Release source-of-plan work remains in `ledger-p1-ios-v3-pro-tools-rollout-alignment` | Do not change the flag default in this carrier | Home matrix plus existing Weekly VM tests | Existing design reference unchanged | Existing prompt reference unchanged |
| iOS | Home | `ios.home.shopping_list_generator` | Shopping list | `NavigationLink` | Paid-ready conditional `HomeAction.shoppingList` -> `makeShoppingListScreen()` at `ios/PulsePlate/Views/HomeView.swift:113` | Existing shopping-list screen | Destination owns `/api/v1/pro/meal/shopping-list` | Same existing weekly-planning flag; it limits capability only after paid admission | Controlled rollout | Canonical source-of-plan remains unresolved and tracked in `ledger-p1-ios-v3-pro-tools-rollout-alignment` | Keep RELEASE `nil` bootstrap and backend/501 remediation out of this carrier | Home matrix plus existing Shopping VM tests | Existing design reference unchanged | Existing prompt reference unchanged |
| iOS | Home | `ios.home.retry_entitlement` | Try again | `button` | Unavailable primary calls only `SubscriptionManager.refreshEntitlement(trigger: .manualRetry)` at `ios/PulsePlate/Views/HomeView.swift:91` | Remains on Home while manager refreshes | Existing SubscriptionManager owns transport and freshness | Only the fail-closed unavailable projection; generic copy exposes no raw diagnostic | Implemented in Consumer-first Home | None | Preserve explicit manual retry only | Home source boundary plus `SubscriptionManagerTests` | No design-authoring change | No prompt-authoring change |
| iOS | Plate | `ios.plate.add_meal` | Add Meal | `button` | `ios/PulsePlate/Views/PlateView.swift:159` (`showMealEntry = true`) | Navigates to `MealEntryView` placeholder (`ios/PulsePlate/Views/PlateView.swift:136`) | No backend yet for add-meal action | No explicit gate | Partial | Destination screen is placeholder (`MealEntryView`) | Implement real add-meal flow + API contract | No dedicated button behavior test | `PP/iOS/Plate/BottomBar/AddMeal/Button/Default (TBD)` | `stub://cta/primary/add-meal` |
| iOS | Plate | `ios.plate.view_details` | View Details | `button` | `ios/PulsePlate/Views/PlateView.swift:164` (`showNutritionDetails = true`) | Navigates to `NutritionDetailsView` placeholder (`ios/PulsePlate/Views/PlateView.swift:139`) | No backend yet for details expansion | No explicit gate | Partial | Destination screen is placeholder (`NutritionDetailsView`) | Implement detailed nutrition drilldown screen | No dedicated button behavior test | `PP/iOS/Plate/BottomBar/ViewDetails/Button/Default (TBD)` | `stub://cta/secondary/view-details` |
| iOS | Plate | `ios.plate.issue_action_dynamic` | Retry / Open Profile / PRO Settings | `button` (dynamic label) | Dynamic action mapping in `PlateIssueView` (`ios/PulsePlate/Views/PlateView.swift:205`) + resolver (`ios/PulsePlate/Models/NutritionData.swift:108`) | Retry fetch / profile nav / pro setup nav | Depends on mapped `PlateLoadIssue` state (`ios/PulsePlate/Models/NutritionData.swift:43`) | Appears only in issue state | Implemented | No deterministic UI tests for action-to-outcome mapping | Add action mapping tests for each issue class | Indirect model tests only: `ios/PulsePlateTests/PlateViewTests.swift:45` | `PP/iOS/Plate/IssueState/PrimaryAction/Button/Stateful (TBD)` | `stub://cta/error-state/dynamic-issue-action` |
| iOS | Progress | `ios.progress.refresh` | Refresh | `button` | `ios/PulsePlate/Views/ProgressView.swift:50` (`fetchNutritionData`) | Reload same screen state | `/api/v1/pro/nutrition/daily` through `NutritionService.fetchNutritionData` (`ios/PulsePlate/Models/NutritionData.swift:168`) | Shown in no-data state | Implemented | No button-level state-machine tests | Add no-data -> loading -> success/error transition tests | No dedicated Progress CTA tests | `PP/iOS/Progress/EmptyState/Refresh/Button/Default (TBD)` | `stub://cta/loading-state/refresh` |
| iOS | Progress | `ios.progress.issue_action_dynamic` | Retry / Open profile / Open PRO setup | `button` (dynamic branch) | `ios/PulsePlate/Views/ProgressView.swift:182` switch on `issue.primaryAction` | Retry fetch or navigate to Profile/Debug tools | Depends on same issue classifier (`ios/PulsePlate/Models/NutritionData.swift:108`) | Appears only in issue state | Implemented | No deterministic UI tests for all three branches | Add branch-level tests for issue action rendering + nav | No dedicated button tests | `PP/iOS/Progress/IssueState/PrimaryAction/Button/Stateful (TBD)` | `stub://cta/error-state/dynamic-issue-action` |
| Web (linked flow) | Apple Product Information | `web.apple_product_info.free_bmi` | Try the free BMI calculator | `Link` | `frontend/src/components/AppleProductInfoDialog.tsx:50` -> `/bmi` | Public free BMI calculator | No API call on navigation and no payment/entitlement effect | Available on direct `/pro` information page and the shared information dialog | Implemented | None | Keep the free BMI action visually primary and internal | Dialog/localization/accessibility tests: `frontend/src/components/__tests__/PremiumGate.test.tsx`; direct-card route tests: `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx` | `PP/Web/AppleProductInfo/FreeBMI/Button/Default (TBD)` | `stub://cta/primary/free-bmi` |
| Web (linked flow) | Apple Product Information | `web.apple_product_info.marketing` | Learn about PulsePlate for Apple devices | `Link` | `frontend/src/components/AppleProductInfoDialog.tsx:57` -> `/marketing` | Public marketing information page | No API call on navigation and no payment/entitlement effect | Available on direct `/pro` information page and the shared information dialog | Implemented | None | Keep the action secondary and informational; do not substitute an unverified Store URL | Dialog/route tests: `frontend/src/components/__tests__/PremiumGate.test.tsx`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx`; Storybook parity: `frontend/src/stories/__tests__/storybookParity.test.ts` | `PP/Web/AppleProductInfo/Marketing/Button/Default (TBD)` | `stub://cta/secondary/apple-product-info` |
| Web (linked flow) | Apple Product Information | `web.apple_product_info.dismiss` | Not now / localized equivalent | `button` | `frontend/src/components/AppleProductInfoDialog.tsx:67` -> `onClose` | Closes the information dialog and restores opener focus in the owning gate | No backend dependency and no acquisition telemetry | Dialog presentation only; direct `/pro` page has no dismiss control | Implemented | None | Preserve Escape, top close, explicit dismiss, and focus return | Focus-trap, every dismissal path, and opener-focus-return tests: `frontend/src/components/__tests__/PremiumGate.test.tsx` | `PP/Web/AppleProductInfo/Dialog/Dismiss/Button/Default (TBD)` | `stub://cta/secondary/dismiss` |
| Web (linked flow) | Nutrition Setup Form | `web.setup.submit_calculate` | Calculate plate | `button type=submit` | `frontend/src/pages/NutritionSetup/SetupForm.tsx:164` -> `submit()` (`frontend/src/pages/NutritionSetup/SetupForm.tsx:49`) | Form -> ResultView transition (`frontend/src/pages/NutritionSetup/index.tsx:27`) | Calls canonical BMR (`frontend/src/pages/NutritionSetup/hooks.ts:408`), plate (`frontend/src/pages/NutritionSetup/hooks.ts:423`), and targets (`frontend/src/pages/NutritionSetup/hooks.ts:539`) from the result hooks | No route auth gate; API auth handled by endpoint/headers | Implemented | No end-to-end submit test covering all three API calls | Add integration test with mocked API responses and auth errors | No direct SetupForm submit test in current suite | `PP/Web/Setup/Form/Calculate/Button/Default (TBD)` | `stub://cta/primary/calculate-plate` |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.retry` | Try again | `button` | `frontend/src/pages/NutritionSetup/ResultView.tsx:71` -> `setRetryKey` (`frontend/src/pages/NutritionSetup/ResultView.tsx:33`) | Re-fetch result data | Re-triggers canonical BMR (`frontend/src/pages/NutritionSetup/hooks.ts:408`), plate (`frontend/src/pages/NutritionSetup/hooks.ts:423`), and targets (`frontend/src/pages/NutritionSetup/hooks.ts:539`) | Appears on error state | Implemented | No contract test for all auth/error branches in retry mode | Add retry tests for 401/403 + generic failure mapping | Retry test exists: `frontend/src/pages/NutritionSetup/__tests__/ResultView.test.tsx:354` | `PP/Web/Setup/Result/Error/Retry/Button/Default (TBD)` | `stub://cta/error-state/retry` |
| Web (linked flow) | Nutrition Setup Result | `web.setup.result.edit` | Edit data / Edit form | `button` | `frontend/src/pages/NutritionSetup/ResultView.tsx:78` and header edit at `frontend/src/pages/NutritionSetup/ResultView.tsx:103` | Return to Setup form (`setValues(null)`) | No direct API call; local state transition | No gate | Implemented | Two edit entrypoints share behavior, no unified UX spec | Create one visual/state spec for both edit triggers | Edit action test: `frontend/src/pages/NutritionSetup/__tests__/ResultView.test.tsx:348` | `PP/Web/Setup/Result/Header/Edit/Button/Default (TBD)` | `stub://cta/secondary/edit-input` |

### Paid-ready iOS FitChef capability reachability

The iOS FitChef capability reuses the Human Product Owner-selected Candidate X
composition and existing `PPCard`, `PPButton`, and token primitives. The
Consumer-first Home is its one production reachability owner, but it adds no
new design-execution identity or shared visual rule in this matrix:

- selecting daily or weekly is local-only; Confirm sends the selected need once
  to `POST /api/v1/pro/fitchef/recommend` through `APIClient`, while pre-result
  Not now and screen dismissal send no outcome
- the exact backend target is rendered as plain non-interactive text; it never
  opens a route, invokes a target, executes an action, or mutates a plan
- the first result-stage Thanks or Not now gesture maps internally to the
  matching closed outcome and sends it to the backend intake; pending and
  failure states make no persistence-success claim, and retry is manual
- `recorded` and `replayed` describe only the exact backend receipt; neither
  state proves understanding, consent, entitlement, navigation, execution, or
  product value
- the web FitChef rows above remain unchanged and retain historical
  `transport=none`; the complete FREE web BMI questionnaire, results,
  information, bounded chat, marketing/demonstration, and iOS handoff posture
  is not narrowed by this iOS-first outcome decision

The canonical Consumer-first Home now constructs `FitChefSupportFlowScreen`
exactly once, and only as the lazy planning-direction child of one paid-ready
FitChef Coach entry. Home exposes no direct support, recommend, outcome, or AI
action. The existing AI flag controls only the Hub capability inventory, while
the existing weekly-planning flag controls only the post-admission Week and
Shopping actions; neither flag establishes entitlement. ER-IOS-4 is a
compatibility alias for this same Home carrier, not a second implementation or
design-authoring lane. No tab, router, deep link, staging, App Store,
credential-provisioning, billing, activation, external-design, or prompt
authority is added here.

### Stable compatibility identifiers are not action authority

The complete matrix contains 30 unique current identities. The Figma, Sora, and
Code Connect design-execution subset contains the 24 identities left after
excluding the separately governed FitChef SupportChoice controls
`web.home.fitchef_show_next_step`, `web.home.fitchef_confirm_pointer`, and
`web.home.fitchef_dismiss_pointer`, plus the repo-runtime-only Consumer-first
Home identities `ios.home.open_progress`, `ios.home.fitchef_coach`, and
`ios.home.retry_entitlement`. These six exclusions do not authorize external
design execution or remove any existing design-registry identity.

`web.home.open_pro` and `web.plate.premium_gate_cta` remain stable compatibility
metadata so existing design references do not fork. Their substrings grant no
purchase, upgrade, checkout, entitlement, acquisition-telemetry, Store-destination,
UI-label, prompt, or route authority. Historical values for those fields are invalid;
only the information-only label, intent, variant, node, stub, and destination in the
current rows are authoritative.

Exact Web information state set: `default`, `hover`, `pressed`, `focus-visible`, `disabled`.

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
Output: default/hover/pressed/focus-visible states.
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
| `web.home.open_pro` | `V3` | `W_HOME_GUIDED_PLANNING_ACTIONS` | `SORA_BTN_web_home_open_pro_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.home.fitchef_show_next_step` | `V1` | `W_HOME_FITCHEF_SUPPORT` | `SORA_BTN_web_home_fitchef_show_next_step_<variant>_<state>_V1` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` |
| `web.home.fitchef_confirm_pointer` | `V3` | `W_HOME_FITCHEF_SUPPORT` | `SORA_BTN_web_home_fitchef_confirm_pointer_<variant>_<state>_V1` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` |
| `web.home.fitchef_dismiss_pointer` | `V3` | `W_HOME_FITCHEF_SUPPORT` | `SORA_BTN_web_home_fitchef_dismiss_pointer_<variant>_<state>_V1` | `frontend/src/features/fitchef/SupportChoiceCard.stories.tsx` |
| `web.plate.open_setup` | `V1` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_open_setup_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.plate.open_progress` | `V3` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_open_progress_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.plate.premium_gate_cta` | `V3` | `W_PLATE_GATE_ACTIONS` | `SORA_BTN_web_plate_premium_gate_cta_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
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
| `web.apple_product_info.free_bmi` | `V1` | `W_APPLE_PRODUCT_INFO_ACTIONS` | `SORA_BTN_web_apple_product_info_free_bmi_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.apple_product_info.marketing` | `V3` | `W_APPLE_PRODUCT_INFO_ACTIONS` | `SORA_BTN_web_apple_product_info_marketing_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.apple_product_info.dismiss` | `V3` | `W_APPLE_PRODUCT_INFO_ACTIONS` | `SORA_BTN_web_apple_product_info_dismiss_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.submit_calculate` | `V1` | `W_SETUP_FORM_FOOTER` | `SORA_BTN_web_setup_submit_calculate_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.result.retry` | `V1` | `W_SETUP_RESULT_ACTIONS` | `SORA_BTN_web_setup_result_retry_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |
| `web.setup.result.edit` | `V3` | `W_SETUP_RESULT_ACTIONS` | `SORA_BTN_web_setup_result_edit_<variant>_<state>_V1` | `docs/design/PULSEPLATE_BUTTON_VISUAL_SYSTEM_TRENDS_AND_FORECAST.md` |

## 7) Execution Queue (Priority)

| Priority | Item | Why | Target PR | Owner |
| --- | --- | --- | --- | --- |
| `P0` | Replace iOS Plate placeholders behind `Add Meal` and `View Details` (`ios/PulsePlate/Views/PlateView.swift:136`) | Core CTA routes end in placeholder screens; blocks production-level UX continuity | Next iOS follow-up after current backend/security stream | iOS + Design |
| `P0` | Add deterministic CTA behavior tests for iOS Home/Plate/Progress primary actions (`ios/PulsePlate/Views/HomeView.swift:57`, `ios/PulsePlate/Views/ProgressView.swift:50`, `ios/PulsePlateTests/PlateViewTests.swift:7`) | CTA actions are defined in runtime views, while current tests are mostly render/data mapping checks rather than button-tap outcome assertions | Same follow-up PR as above | iOS QA |
| `P1` | Add Web click-through integration tests for Home/Plate auth-gated CTAs (`frontend/src/pages/__tests__/Home.test.tsx:17`, `frontend/src/pages/__tests__/Plate.test.tsx:56`, `frontend/src/auth/RequireKey.tsx:13`) | Presence tests exist, but route-guard redirect and full CTA navigation outcomes are not asserted end-to-end | Web parity test hardening PR | Frontend QA |
| `P2` | Backfill `Design Review Reference` for all matrix rows using `PP/<Platform>/<Screen>/<Component>/<State>` naming and repo-native review links (`docs/design/PENPOT_STORYBOOK_BRIDGE.md:76`, `docs/figma/FIGMA_IMPLEMENTATION_RUNBOOK.md:209`) | Needed for tool-neutral design-to-code traceability and faster handoff review | Design handoff follow-up | Design + FE + iOS |
| `P2` | Normalize row-level prompt files from matrix IDs into a dedicated prompt pack (current baseline: `docs/sora/PULSEPLATE_SORA_PROMPT_ENGINEERING_PLAYBOOK.md:245`) | Prompt templates exist in a centralized playbook, but row-level prompt-ID files are not materialized yet for deterministic ops | Sora prompt pack follow-up | Sora Prompt Engineer |

No execution-queue row authorizes a public Web purchase, subscription, upgrade, trial,
restore, or entitlement-acquisition action. A future paid Web channel requires a separate
exact human GO, server-authoritative billing and entitlement architecture, and a new reviewed
carrier before this matrix may add a payment control or Store destination.

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
