# iOS Prototype v2 Reconciliation

## Scope

This artifact reconciles `ios prototype v2` against the current PulsePlate
design-system and iOS runtime sources.

Design artifact:

- Figma file: `ios prototype v2`
- file key: `AhyS6u4dZXMRHVUDO3Cfn6`

Repo sources used:

- `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`
- `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md`
- `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md`
- `ios/PulsePlate/Views/HomeView.swift`
- `ios/PulsePlate/Screens/PaywallScreen.swift`
- `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift`
- `ios/PulsePlate/Screens/ShoppingListReaderScreen.swift`
- `ios/PulsePlate/Views/Components/MascotBubble.swift`
- `ios/PulsePlate/Views/PlateView.swift`
- `ios/PulsePlate/Views/ProgressView.swift`

## Screen Inventory

| Canonical screen ID | nodeId | Status |
| --- | --- | --- |
| `iOS_Onboarding_01_Welcome` | `25:2` | reconciled |
| `iOS_Paywall_Pro_VIP` | `17:2` | reconciled |
| `iOS_Onboarding_02_Value_Usage` | `20:2` | reconciled |
| `iOS_Home` | `11:2` | reconciled |
| `iOS_ShoppingList` | `18:2` | reconciled |
| `iOS_WeeklyPlan_Reader` | `15:2` | reconciled |
| `iOS_Profile` | `13:2` | reconciled |
| `iOS_BMI` | `24:2` | reconciled |
| `iOS_Plate` | `31:2` | reconciled |
| `iOS_Progress` | `29:2` | reconciled |

## Component-by-Component Gaps

### Aligned

- Palette is locked to the canonical navy / blue / green / red system (`docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:87-90`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:172-182`).
- Onboarding follows one-message-per-screen with one dominant CTA (`docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:129-130`, `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:196-198`).
- Home includes the full current iOS CTA matrix:
  - BMI Calculator
  - Profile Setup
  - Open Plate
  - Weekly Plan Reader
  - Shopping List
  (`ios/PulsePlate/Views/HomeView.swift:55-134`, `docs/design/PULSEPLATE_BUTTON_ACTION_PROMPT_MATRIX.md:81-85`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:931-939`)
- Paywall keeps PRO and VIP on one comparison surface instead of inventing a
  separate VIP home CTA (`ios/PulsePlate/Screens/PaywallScreen.swift:13-23`, `ios/PulsePlate/Screens/PaywallScreen.swift:57-71`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:717-725`).
- FitChef is present as a supporting brand layer and not the main focal object (`ios/PulsePlate/Views/Components/MascotBubble.swift:31-46`, `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md:129-130`).

### Reconciled by v2

- Raw iOS prototype duplicated scroll snapshots are replaced by one stable frame
  per screen (`docs/figma/ios_prototype_v2/README.md:17-22`, `docs/figma/ios_prototype_v2/README.md:30-39`).
- Shopping List and diet-menu presence are now represented as explicit iOS
  surfaces, not only implicit navigation rows (`ios/PulsePlate/Views/HomeView.swift:93-134`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:935-939`).
- Weekly Plan now reflects VIP follow-up actions in the same surface where the
  runtime view already exposes disabled VIP CTAs (`ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:118-130`, `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:142-176`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:1028-1034`).
- Shopping List now exists as a clean category-based surface instead of being
  implied only by a gated home row (`ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:50-93`).
- BMI now has a design-reference surface that preserves the runtime sequence:
  input -> result -> optional soft paywall hook (`ios/PulsePlate/Screens/BMICalculatorScreen.swift:46-85`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:954-969`).
- Onboarding now uses the localized iOS value/usage copy as the content spine
  instead of prototype-only copy that drifted away from runtime strings.
- On March 12, 2026 the BMI + onboarding slice was re-captured again into
  nodes `24:2`, `20:2`, and `25:2` to lock the current calmer brand copy and
  stronger form anatomy into the canonical handoff map.
- BMI now uses field/picker anatomy closer to the actual `BMICalculatorScreen`
  instead of generic editable quick rows, and the optional hook mirrors the
  backend default title/body/CTA contract (`ios/PulsePlate/Screens/BMICalculatorScreen.swift:46-85`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:954-969`).
- Profile now exists as a calm PRO-setup surface rather than remaining only a
  technical form implementation (`ios/PulsePlate/Views/ProfileView.swift:19-80`, `docs/figma/PULSEPLATE_FIGMA_DESIGN_SPECIFICATION.md:1041-1049`).
- Home no longer relies on the temporary `PRO active` chip; it now uses a
  readiness-summary treatment closer to the runtime status-card pattern (`ios/PulsePlate/Views/HomeView.swift:37-53`).
- Paywall now keeps the PRO / VIP comparison but expresses plan selection in a
  calmer StoreKit-list anatomy instead of marketing-heavy tier blocks (`ios/PulsePlate/Screens/PaywallScreen.swift:13-23`, `ios/PulsePlate/Screens/PaywallScreen.swift:32-71`).
- Profile now uses a neutral `sex` default and separate `height` / `weight`
  rows so the design reference better matches the actual form fields (`ios/PulsePlate/Views/ProfileView.swift:21-34`).
- Weekly Plan now reflects the runtime day navigator and plan-metrics layer (`ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:85-125`).
- Shopping List now reflects runtime footer / warning anatomy more directly (`ios/PulsePlate/Screens/ShoppingListReaderScreen.swift:77-93`).
- Plate now mirrors the runtime main-state anatomy with a visual split,
  embedded segment detail, visible `Add Meal` / `View Details` CTAs, and a
  mascot support layer without creating separate destination screens (`ios/PulsePlate/Views/PlateView.swift:54-211`).
- Progress now mirrors the runtime completion summary, chart, and daily segment
  list while keeping a single runtime-selected recovery CTA inside the same
  main surface (`ios/PulsePlate/Views/ProgressView.swift:130-242`).
- On March 12, 2026 the Plate slice was re-captured twice to replace
  gradient-heavy primitives that MCP flattened poorly; canonical handoff now
  points to `31:2`, not the earlier exploratory nodes `26:2` or `30:2`.

### Remaining Gaps

- Captured frame names remain MCP-generated `Main Content (...)`; canonical
  naming is preserved through the recorded `screen ID -> nodeId` map.
- Paywall is closer to runtime intent but still keeps a richer comparison layer
  than the current minimal SwiftUI `List`.
- Weekly Plan and Shopping List remain design-reference screens rather than
  exact runtime state machines for `idle/loading/empty/error`.
- BMI and Profile still simplify some runtime detail states to keep the design
  reference focused on the main UX path.
- Onboarding still compresses the real app into two calm screens and does not
  model later branching states beyond the primary continuation path.
- Plate and Progress intentionally model only the main daily loop state; they
  do not yet break out loading / empty / issue / destination screens into
  separate handoff frames.

## Decision Log

- Use repo SoT over raw imported Figma whenever there is a mismatch.
- Prefer implementation-safe structure over visual fidelity to flawed source
  captures.
- Keep VIP entry inside paywall and weekly-plan follow-up surfaces.
- Do not introduce a standalone `VIP` shortcut on `Home`.
- Keep the March 11, 2026 MCP session log as blocker-era evidence; future Code
  Connect activation runs must create a new dated session log instead of
  mutating the original baseline.

## Next Promotion Path

1. If a future MCP refresh changes top-level frame IDs again, re-capture `BMI`
   and `Onboarding` and refresh the canonical `screen ID -> nodeId` map.
2. Reconcile `Weekly Plan` and `Shopping List` further against runtime empty/error states.
3. If Code Connect becomes available, use
   `docs/figma/FIGMA_IOS_PROTOTYPE_V2_CODE_CONNECT_READINESS.md` and map the
   reconciled frames rather than the raw prototype file, while linking the new
   activation session log back to
   `docs/runbooks/sessions/FIGMA_MCP_SESSION_2026-03-11_ios-prototype-check.md`.
4. Keep the `screen ID -> nodeId` map current whenever a new MCP capture
   refresh changes top-level frame IDs.
