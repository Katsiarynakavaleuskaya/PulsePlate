# PR-678 Audit — iOS onboarding (Value + Usage, P0-B)

**Date**: 7 February 2026
**PR**: 678 (GitHub PR number is source of truth)
**Type**: iOS runtime + localization

## Summary

Tighten first-launch onboarding to the minimal P0-B requirement:

- **2 screens**: **Value** + **Usage**
- **Gate before root UX** (before `RootTabs()`)
- **No networking / paywall / analytics**
- RU/EN/ES strings updated

## Audit questions (evidence-driven answers)

### 1) Where is the iOS root entry / “first screen” chosen?

- App entrypoint:
  - `ios/PulsePlate/PulsePlateApp.swift:3-9` (WindowGroup shows `WelcomeGateView()`)
- Gate view:
  - `ios/PulsePlate/Welcome/WelcomeGateView.swift:3-12`

### 2) Where is first-launch persistence stored?

- `@AppStorage("has_seen_welcome_v1")` in:
  - `ios/PulsePlate/Welcome/WelcomeGateView.swift:4-11`

### 3) Is there an existing onboarding flow?

Yes — `WelcomeFlowView` is the onboarding flow presented by `WelcomeGateView`:

- `ios/PulsePlate/Welcome/WelcomeFlowView.swift:10-64` (flow)
- Localization keys:
  - `ios/PulsePlate/Welcome/WelcomeFlowView.swift:66-97`

## Changes (file:line)

- Reduce welcome flow steps to **two** screens (Value + Usage):
  - `ios/PulsePlate/Welcome/WelcomeFlowView.swift:3-85`
- Update RU/EN/ES strings for `onboarding.welcome.screen1.*` and `screen2.*`:
  - `ios/PulsePlate/en.lproj/Localizable.strings:84-97`
  - `ios/PulsePlate/ru.lproj/Localizable.strings:100-113`
  - `ios/PulsePlate/es.lproj/Localizable.strings:100-113`

## Test plan (local)

- `pre-commit run --all-files`
- `make ios-test`

## Risks and mitigations

- **Risk**: Existing users who already have `has_seen_welcome_v1=true` will not see updated onboarding copy.
  - **Mitigation**: Minimal-risk choice for P0-B (no surprise re-onboarding). If we need to re-show onboarding later, do it via a versioned key (new ledger item + explicit product decision).
