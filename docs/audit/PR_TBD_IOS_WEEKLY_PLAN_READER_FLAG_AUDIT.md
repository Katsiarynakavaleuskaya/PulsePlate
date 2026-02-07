# PR-TBD Audit — iOS: Mount WeeklyPlanReader behind feature flag

**Date**: 7 February 2026
**PR**: TBD
**Branch**: `feat/ios-weekly-plan-reader-flag`
**Type**: iOS runtime + audit doc

---

## Summary

We already have a Weekly Plan Reader implementation (view + view model + service), but it is not
reachable from the running app. This PR mounts it behind an existing feature flag
(`FeatureFlags.weeklyPlanReaderEnabled`) via a controlled entrypoint (Debug Tools), and tightens
error UX for common auth failures (400/401/403) without adding any domain logic on the client.

---

## Scope

- Mount `WeeklyPlanReader` behind `FeatureFlags.weeklyPlanReaderEnabled`.
- Expose the entrypoint via Debug Tools (controlled, non-user-facing in release).
- Ensure 400/401/403 failures render as user-readable UI states (no crashes / no raw debug dumps).

## Non-scope

- No backend changes.
- No paywall implementation / StoreKit wiring.
- No “unify all tabs under NavigationStack” refactor.
- No new client-side business logic (thin client policy).

---

## Evidence (repo-truth)

### Feature flag exists

- `ios/PulsePlate/Utilities/FeatureFlags.swift:12-36`

### WeeklyPlanReader implementation exists (but is not mounted)

- View: `ios/PulsePlate/Views/WeeklyPlan/WeeklyPlanReaderView.swift:8-67`
- ViewModel: `ios/PulsePlate/ViewModels/WeeklyPlanReaderViewModel.swift:9-105`
- Service: `ios/PulsePlate/Services/WeeklyPlanService.swift:3-38`

### Debug Tools exists as a controlled entrypoint

- `ios/PulsePlate/Views/DebugToolsScreen.swift:11-72`

### Test coverage (ViewModel error/auth mapping)

- `ios/PulsePlateTests/WeeklyPlanReaderViewModelTests.swift:1-120`

---

## Implementation plan (one path)

1. Add a conditional Debug Tools entry for WeeklyPlanReader when the feature flag is enabled.
2. Ensure WeeklyPlanReader screen integrates cleanly with existing navigation (no nested stacks).
3. Improve ViewModel error mapping for HTTP 400/401/403 into user-readable messages.
4. Add focused unit tests for the ViewModel auth/error mapping.

---

## Verification

Local commands used:

```bash
pre-commit run --all-files
make ios-test
```
