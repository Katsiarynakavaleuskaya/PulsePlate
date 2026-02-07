# PR-TBD Audit — iOS ShoppingPlan public API fix

**Date**: 7 February 2026
**PR**: TBD (GitHub PR number is source of truth)
**Type**: iOS runtime + tests

## Summary

Fix an iOS API-surface smell: `ShoppingPlan` was declared `public` but was not constructible outside the module (internal nested types and no public initializer). This was flagged in review tooling as “ShoppingPlan isn't constructible”.

This PR **narrows the API surface** by making the “stub plan” types internal to the app module:

- `ShoppingPlan`
- `ShoppingListRequestPayload`

These are implementation details of the Shopping List reader flow and are consumed only inside `PulsePlate` (tests use `@testable import PulsePlate`).

## Evidence (why this is safe)

- `PulsePlateTests` imports the app module with `@testable`, so internal symbols remain accessible to tests:
  - `ios/PulsePlateTests/Fixtures/ShoppingListFixtures.swift:2`

## Changes (file:line)

- Narrow `ShoppingPlan` to internal:
  - `ios/PulsePlate/Models/ShoppingList/ShoppingListStubPlan.swift:6`
- Narrow `ShoppingListRequestPayload` to internal:
  - `ios/PulsePlate/Models/ShoppingList/ShoppingListRequestPayload.swift:5-21`

## Test plan

- `pre-commit run --all-files`
- `make ios-test`
