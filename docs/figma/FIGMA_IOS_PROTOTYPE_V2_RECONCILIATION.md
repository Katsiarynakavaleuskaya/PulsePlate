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

## Screen Inventory

| Canonical screen ID | nodeId | Status |
| --- | --- | --- |
| `iOS_Onboarding_01_Welcome` | `1:2` | reconciled |
| `iOS_Paywall_Pro_VIP` | `2:2` | reconciled |
| `iOS_Onboarding_02_Value_Usage` | `3:2` | reconciled |
| `iOS_Home` | `4:2` | reconciled |
| `iOS_ShoppingList` | `5:2` | reconciled |
| `iOS_WeeklyPlan_Reader` | `6:2` | reconciled |
| `iOS_Profile` | `7:2` | reconciled |
| `iOS_BMI` | `8:2` | reconciled |

## Component-by-Component Gaps

### Aligned

- Palette is locked to the canonical navy / blue / green / red system.
- Onboarding follows one-message-per-screen with one dominant CTA.
- Home includes the full current iOS CTA matrix:
  - BMI Calculator
  - Profile Setup
  - Open Plate
  - Weekly Plan Reader
  - Shopping List
- Paywall keeps PRO and VIP on one comparison surface instead of inventing a
  separate VIP home CTA.
- FitChef is present as a supporting brand layer and not the main focal object.

### Reconciled by v2

- Raw iOS prototype duplicated scroll snapshots are replaced by one stable frame
  per screen.
- Shopping List and diet-menu presence are now represented as explicit iOS
  surfaces, not only implicit navigation rows.
- Weekly Plan now reflects VIP follow-up actions in the same surface where the
  runtime view already exposes disabled VIP CTAs.
- Shopping List now exists as a clean category-based surface instead of being
  implied only by a gated home row.
- BMI now has a design-reference surface that preserves the runtime sequence:
  input -> result -> optional soft paywall hook.
- Profile now exists as a calm PRO-setup surface rather than remaining only a
  technical form implementation.

### Remaining Gaps

- Captured frame names remain MCP-generated `Main Content (...)`; canonical
  naming is preserved through the recorded `screen ID -> nodeId` map.
- Home still uses a `PRO active` chip in the prototype instead of a more native
  status summary treatment from final implementation components.
- Paywall is structurally aligned with runtime intent but still not StoreKit-card
  accurate.
- Weekly Plan and Shopping List in v2 are design-reference screens, not direct
  mirrors of current runtime list/table anatomy.
- BMI and Profile still simplify some runtime detail states to keep the design
  reference focused on the main UX path.

## Decision Log

- Use repo SoT over raw imported Figma whenever there is a mismatch.
- Prefer implementation-safe structure over visual fidelity to flawed source
  captures.
- Keep VIP entry inside paywall and weekly-plan follow-up surfaces.
- Do not introduce a standalone `VIP` shortcut on `Home`.

## Next Promotion Path

1. Reconcile `Weekly Plan` and `Shopping List` further against runtime empty/error states.
2. Add `Plate` and `Progress` parity if the next slice expands beyond the current iOS funnel.
3. If Code Connect becomes available, map the reconciled frames rather than the
   raw prototype file.
