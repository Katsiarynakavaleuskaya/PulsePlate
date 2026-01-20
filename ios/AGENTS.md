# Agent instructions (scope: ios/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `ios/` and below.
- Key paths: `PulsePlate.xcworkspace`, `PulsePlate.xcodeproj`, `PulsePlate/`.

## Commands
- Open the app in Xcode: `PulsePlate.xcworkspace`.
- Tests: run from Xcode (Unit/UI test targets) or `xcodebuild` if needed.

## Conventions
- Mobile client uses the same REST `/api/v1/*` endpoints and auth flow as web.
- Keep API changes synchronized with backend schema updates.
- Backend `app` facade is stable: FastAPI instance is defined in backend
  (`app.app` == `legacy_app.app`). Missing endpoints on iOS usually indicate
  backend feature flags or environment issues, not iOS routing bugs.

## Backend coordination (important)

- Some backend endpoints (e.g. export / premium features) may be gated by
  feature flags evaluated at backend import time.
- If an endpoint unexpectedly returns 404/422 on iOS:
  1) Verify the endpoint exists in backend OpenAPI.
  2) Check backend environment (TESTING / DEBUG / feature flags).
  3) Do NOT assume the issue is in iOS networking until backend routing is confirmed.

## iOS Thin Client Policy (BMI)

**Hard rule:** iOS thin client for BMI must NOT compute BMI logic.

**Forbidden:**
- ❌ Any BMI thresholds (18.5, 25, 30) in iOS code
- ❌ Any group/category inference (`if bmi > ...`, `if age < 12`)
- ❌ Any waist risk computation (thresholds, risk levels)
- ❌ Any BMI math (only backend calculates)
- ❌ Any enum with `from(bmi:)` or `categoryForBMI(_:)` methods
- ❌ Any computation of `wht_ratio` or `waist_cm / height_cm` in Swift

**Allowed:**
- ✅ Render backend fields as-is (`bmi`, `category`, `groupDisplay`, `interpretation`)
- ✅ Localize `visualization.ranges[].key` through iOS i18n table
- ✅ Format numbers for UI display (rounding, not recalculation)
- ✅ Handle `category == nil` for conditional UI rendering (UI logic, not computation)
- ✅ Map backend token to UI label (e.g., `category` → "Normal" for display), **without computing from bmi**

**Contract note:** `category` is treated as display string (may be localized or token). iOS does not infer thresholds.

## Enforced CI Rules (Anti-Duplication)

**Guard test:** `ThinClientGuardsTests` in `PulsePlateTests/Guards/`

**What it enforces:**
- No BMI threshold literals (`18.5`, `25`, `30`, `0.5`, `0.6`) in Swift source code
- No BMI computation function patterns (`computeBMI`, `categoryForBMI`, `riskForBMI`)
- No suspicious patterns (`whtRatio =`, `waistCm /`, `heightCm /`)
- Fixtures must match backend contract (not invented)
- Response DTOs are read-only (no computed properties with BMI logic)

**CI enforcement:**
- Guard test runs in CI (must pass)
- If guard fails → PR blocked
- Fixtures are the ONLY allowed place for threshold values (they're backend contract examples)

**Architectural guard policy:**
- `ThinClientGuardsTests.swift` is considered an **architectural guard**.
- Removing or weakening it requires explicit ADR / audit.
- This guard prevents "One BMI Engine" invariant violations.

**Full enforcement (recommended):**
- Add SwiftLint custom rule or build script to scan all `.swift` files for forbidden patterns
- Guard test is a minimum; full source scanning provides stronger protection

**Single source of truth:**
- Backend contract → iOS fixtures → iOS DTOs → UI rendering
- If contract changes → update fixtures first, no fallback logic in iOS

## CI Integration — iOS Tests Workflow

**Job:** `ios-tests` (GitHub Actions)

**Triggers:**
- `pull_request` events
- `push` to `feat/*`, `fix/*`, `main` branches

**Runner:** macOS 15 (GitHub Actions)

**Xcode selection:**
- Preferred: Xcode 16.2 (`/Applications/Xcode_16.2.app`)
- Fallback: newest available `Xcode_*.app` (sorted, deterministic)
- Final fallback: `/Applications/Xcode.app` (default)

**Simulator:**
- Device: `iPhone 16`
- OS: `latest` (automatically matches runner image)
- **Hard rule:** Never pin non-existent simulators (e.g., `iPhone 15` may not exist on runner)

**Workspace:**
- Uses `PulsePlate.xcworkspace` (required for SPM dependencies like Lottie)
- Not `PulsePlate.xcodeproj` (SPM packages won't resolve correctly)

**Enforcement:**
- XCTest unit tests (including guard tests)
- Thin-client guard tests (anti-duplication)
- Tests must pass before PR merge
- CI failure blocks merge

**Destination policy:**
- Use stable, guaranteed devices: `iPhone 16, OS=latest` (canonical)
- If primary destination fails, update to a device that exists on current runner images
- Never use `name=...` without `OS=latest` or auto-detect via `simctl` (unreliable)

## Local iOS checks

**Fast (pre-commit):**
- Swift syntax/build checks (automatic via pre-commit hooks)
- No full unit tests (too slow for every commit)

**Recommended before pushing an iOS PR:**
- Run `make ios-test` locally (xcodebuild test)
- This runs all unit tests including guard tests
- Catches issues before CI

**Local vs CI differences:**
- **Local:** Uses `-project` (workspace scheme has TestAction config issue) + iPhone 17
- **CI:** Uses `-workspace` + iPhone 16 (available on GitHub runner)
- Both run the same tests; only destination/build method differs

**Required (CI):**
- `ios-tests` GitHub Actions job must pass
- CI is the enforcement gate (blocks merge if tests fail)

**Test execution (canonical):**
- Use `-only-testing:PulsePlateTests` to explicitly target test bundle
- Required for app schemes in workspace context (Xcode edge case)
- Without `-only-testing`, xcodebuild may return exit code 66 even if tests run
- This is a known Xcode behavior, not a project configuration issue
