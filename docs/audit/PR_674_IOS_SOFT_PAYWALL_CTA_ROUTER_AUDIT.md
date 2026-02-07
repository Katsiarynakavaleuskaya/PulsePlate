# PR-674 Audit — iOS: Wire soft paywall CTA → paywall router

**Date**: 7 February 2026
**PR**: #674
**Branch**: `feat/ios-soft-paywall-cta-router-pr-674`
**Type**: iOS runtime + audit doc

## Summary

This PR wires the existing **soft paywall** CTA (rendered after BMI calculation) to a **real paywall navigation handler** and a minimal paywall screen.

**Goal:** remove the current no-op CTA handler and route users to an actual paywall flow.
**Non-goal:** change product logic, pricing, offers, or subscription business rules.

## Repo-truth (before)

### 1) Soft paywall hook is rendered, but CTA is a no-op

- DTO contract field exists: `soft_paywall` and `SoftPaywallHookDTO` (client renders it only when present).
  - Evidence: `ios/PulsePlate/Models/BMI/BMICalculateResponseDTO.swift:12-43`
  - Evidence: `ios/PulsePlate/Models/BMI/SoftPaywallHookDTO.swift:6-58`

- UI renders the hook inside `BMICalculatorScreen`, but the CTA closure was empty (no navigation).
  - Evidence: `ios/PulsePlate/Screens/BMICalculatorScreen.swift:60-90`

### 2) Backlog item exists (P1) explicitly for wiring CTA → router

- Evidence: `docs/roadmap/BACKLOG_LEDGER.md:869-879`

## Canonical contract (backend-owned)

- Soft paywall hook contract: `docs/contracts/soft_paywall.md`
  - Purpose: text-only hook; client must render and navigate only (no BMI logic).
  - Evidence: `docs/contracts/soft_paywall.md:1-156`

## Implementation (this PR)

### 1) Add a paywall router (navigation handler)

- `PaywallRouter` manages paywall presentation state and keeps last routing context (source/target).
- It contains **no subscription logic**; it is purely a navigation handler.
- Evidence: `ios/PulsePlate/Routing/PaywallRouter.swift:1-28`

### 2) Add a minimal paywall screen backed by StoreKit

- `PaywallScreen` uses existing `StoreKitManager` to list products, purchase, and restore.
- Evidence: `ios/PulsePlate/Screens/PaywallScreen.swift:1-66`
- Evidence: `ios/PulsePlate/Models/StoreKitManager.swift:6-73`

### 3) Wire soft paywall CTA → router and present paywall

- `BMICalculatorScreen` now calls `paywallRouter.presentPaywall(source:target:)` from the CTA handler and presents `PaywallScreen` via `.sheet`.
- Evidence: `ios/PulsePlate/Screens/BMICalculatorScreen.swift:60-110`

## Tests

### CTA routing unit test

- Added a small unit test to ensure `PaywallRouter` toggles presentation state and stores context (source/target).
- Evidence: `ios/PulsePlateTests/SoftPaywallCTARoutingTests.swift:1-24`

### Test execution (CI-relevant)

`make ios-test` runs an explicit allowlist of iOS tests via `-only-testing:` flags.
This PR adds `SoftPaywallCTARoutingTests` to that default allowlist.

- Evidence: `Makefile:310-352`

## Scope / Non-scope

### In scope

- Wire existing soft paywall CTA to paywall navigation handler
- Minimal paywall screen using existing StoreKit manager
- Deterministic unit test + ensure it runs in `make ios-test`

### Out of scope

- Changing paywall copy, pricing, or offers
- Adding subscription eligibility / tier inference in iOS
- Refactoring navigation across the app
- Backend changes

## Verification

### Local commands

```bash
pre-commit run --all-files
make ios-test
```
