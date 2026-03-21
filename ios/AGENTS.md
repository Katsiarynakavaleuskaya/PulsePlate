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
- PR-653 scope guard (P0 Welcome): iOS only — do not mix web/backend/analytics/Lottie/deeplinks.
- For coordinated iOS+frontend work (designer/marketing/dev), follow:
  `docs/orchestration/IOS_FRONTEND_MULTIAGENT_PLAYBOOK.md`.
- Visual quality SoT for premium UX:
  `docs/design/PULSEPLATE_LUXURY_WEB_IOS_VISUAL_GUIDELINES.md`.
- PR review gate (short checklist):
  `docs/design/LUXURY_UI_REVIEW_CHECKLIST.md`.
- For button-level visual execution and prompt references, use the canonical root section in
  `AGENTS.md` (matrix + prompt playbook links are maintained there to avoid duplicated scoped text).
- App Store and mascot packaging for FitChef follows the initiative foundation contract:
  `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md`.
- Canonical FitChef mascot/icon taxonomy for asset-focused PRs lives in:
  `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md`.

## CI: Greenlight iOS preflight (P0 report-only)

- Workflow: `.github/workflows/greenlight-ios.yml`
- Purpose: iOS-only preflight checks via Greenlight to measure signal quality before enabling blocking gates.
- Triggers: path-scoped (iOS/CI-related changes only).
- Preflight script: `scripts/ci/greenlight_ios_preflight.sh`
  - Runs: `greenlight preflight --format json` (report artifact)
  - Deterministic version pin: `GREENLIGHT_VERSION=v0.1.0`
  - Report-only by default: `GREENLIGHT_BLOCKING=false`
- Timeouts: Job-level `timeout-minutes` must use `vars` (GitHub Actions: `env` not available at job level; actionlint). Step-level scripts can read timeout from `env` (see root AGENTS.md timeout SSOT rule).
- Runner/approvals: Uses default runner; does not modify backend runtime.

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

## FitChef thin client policy

- iOS must treat FitChef as a thin presentation layer over backend contracts; no local coaching logic, nutrition math, or entitlement inference in Swift.
- Current live FitChef mascot routes remain `/api/v1/insight/fitchef*`; future structured-coach routes must be additive and schema-driven.
- FitChef screens/cards must render structured DTO fields or approved response envelopes; do not parse raw prose to decide navigation, state transitions, or action visibility.
- FREE-tier iOS surfaces may show bounded/static FitChef guidance, but must not expose open-ended coach runtime.
- Mascot or App Store asset changes must land through dedicated asset-focused PRs; docs/policy PRs must not mix in binary asset promotion.

## iOS billing runtime thin-client policy

- `SubscriptionManager` is orchestration-only; entitlement truth remains backend-owned.
- StoreKit purchase success must not unlock paid UI until backend verification, activation, and refresh confirm entitlement.
- Missing, stale, or malformed activation payload or activation context must keep UI locked (fail-closed).
- All billing-runtime calls must go through `APIClient` / `HTTPClient`; direct `URLSession` networking is forbidden on this seam.
- App relaunch or foreground refresh with stored activation context must re-check entitlement with the backend instead of inferring tier locally.

## Enforced CI Rules (Anti-Duplication)

**Guard test:** `ThinClientGuardsTests` in `PulsePlateTests/Guards/`

**What it enforces:**

- No BMI threshold literals (`18.5`, `25`, `30`, `0.5`, `0.6`) in Swift source code
- No BMI computation function patterns (`computeBMI`, `categoryForBMI`, `riskForBMI`)
- No suspicious patterns (`whtRatio =`, `waistCm /`, `heightCm /`)
- Fixtures must match backend contract (not invented)
- Response DTOs are read-only (no computed properties with BMI logic)

**Regex policy:**

- Regex for identifier detection (BMI thresholds, branches) is **case-sensitive by design** (Swift variable names are case-sensitive).
- `whtDivisionRegex` uses case-insensitive matching for division patterns (`waist/height`), which is acceptable as it detects mathematical operations, not identifiers.

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

- Preferred: Xcode 16.4 (`/Applications/Xcode_16.4.app`)
- Fallback: Xcode 16.3 (`/Applications/Xcode_16.3.app`)
- Fallback: Xcode 16.2 (`/Applications/Xcode_16.2.app`)
- CI fails if no suitable Xcode 16.x is found (see `.github/workflows/ci.yml` `select-xcode` step).

**Simulator (CI):**

- **Auto-selected** from available simulators at runtime (no hard-coded device)
- **Runtime policy:** prefer iOS 18.6 → fallback to iOS 18.x → fallback to any iOS runtime (if needed)
- **Device preference:** `iPhone 16e` → `iPhone 16` → `iPhone 16 Pro` → `iPhone 15` → `iPhone 14`
  - If none of the preferred devices exist on the runner, CI falls back to **any available iPhone**, then to **any iOS simulator** (deterministic sort)
- **Destination:** **UDID-only** `platform=iOS Simulator,id=<UDID>`
- **Hard rule:** CI must **never** use `OS=latest`. There is a guard that fails the job if `latest` appears in the destination spec.

**Testing device fallback (CI):**

- You can force fallback behavior by overriding:
  - `PREFERRED_DEVICES="iPhone 99,iPhone 98"`
- CI logs + Step Summary must show when fallback is used and which UDID/device were selected.

**Test execution (project-based, split build/test):**

- **Hard rule:** CI **must** split build and test: `build-for-testing` → `test-without-building`
- **Rationale:** Faster diagnosis (build failed vs test runtime failed), targeted retries (retry test without rebuilding), better observability (separate step durations)
- **Step 1: Build for testing** (timeout: 10 minutes):
  ```bash
  xcodebuild build-for-testing \
    -project PulsePlate.xcodeproj \
    -scheme PulsePlate \
    -destination "$DESTINATION" \
    -configuration Debug \
    -derivedDataPath ../.derivedData \
    -enableCodeCoverage NO
  ```
- **Step 2: Run tests** (timeout: 15 minutes):
  ```bash
  # Canonical test list: scripts/ios_test_targets.sh (run from ios/)
  xcodebuild test-without-building \
    -project PulsePlate.xcodeproj \
    -scheme PulsePlate \
    -skip-testing:PulsePlateUITests \
    $(../scripts/ios_test_targets.sh | tr ',' '\n' | while read t; do [ -n "$t" ] && echo "-only-testing:$t"; done) \
    -destination "$DESTINATION" \
    -derivedDataPath ../.derivedData \
    -enableCodeCoverage NO \
    -parallel-testing-enabled NO
  ```
- **Canonical test list:** `scripts/ios_test_targets.sh` (single source for Makefile, ci.yml, AGENTS.md)
- **Do not use `-workspace` for tests unless scheme has explicit TestAction** (confirmed via separate PR)
- Workspace (`PulsePlate.xcworkspace`) is used for building/running app (SPM dependencies), but tests run via project
- Project-based approach avoids exit code 66 when app scheme lacks TestAction in workspace context
- (Do not rely on `-only-testing:PulsePlateTests` blanket targeting in CI; keep it explicit and stable.)

**Enforcement:**

- XCTest unit tests (including guard tests)
- Thin-client guard tests (anti-duplication)
- Tests must pass before PR merge
- CI failure blocks merge

**Test scope policy (PR-559):**

- **Unit tests (Guards + BMI + Keychain)** — mandatory, block merge if failing
  - `ThinClientGuardsTests` (anti-duplication guard)
  - `ProKeyProviderTests`, `KeychainStoreTests` (Keychain conformance)
  - `BMIServiceTests`, `BMIResponseDecodingTests`, `BMIRequestEncodingTests`, `LocaleParsingTests`
- **UI tests** — excluded from CI (do not block PR-559)
  - `PulsePlateUITests` skipped via `-skip-testing:PulsePlateUITests`
  - `PlateViewTests` excluded (unstable, needs stabilization/rewrite)
  - **Backlog item:** Stabilize/rewrite `PlateViewTests` and restore to CI (see `docs/roadmap/BACKLOG_LEDGER.md`)

**Destination policy (CI):**

- CI **auto-selects** destination from available simulators dynamically
- Prefers **iOS 18.x runtime** (avoids `OS=latest` resolving to iOS 26.x betas)
- Preferred devices: `iPhone 16e` → `iPhone 16` → `iPhone 16 Pro` → `iPhone 15` → `iPhone 14`
- **Hard rule:** never pin a simulator that may not exist; CI must discover availability first
- Never uses `OS=latest` for named devices (to avoid iOS 26.x beta runtimes)

**Destination policy (Local):**

- Local defaults to `iPhone 16e` (can be overridden via `IOS_SIM_NAME`/`IOS_SIM_OS`)
- Uses `OS=latest` locally (acceptable for development, not for CI)

## Local iOS checks

**Fast (pre-commit):**

- Swift syntax/build checks (automatic via pre-commit hooks)
- No full unit tests (too slow for every commit)

**Recommended before pushing an iOS PR:**

- Run `make ios-test` locally (xcodebuild test)
- This runs all unit tests including guard tests
- Catches issues before CI

## Secret storage conformance (iOS)

- Sensitive values on iOS (`PRO_API_KEY`, auth/session tokens, passwords, secrets) must use Keychain-backed storage only.
- `UserDefaults` / `@AppStorage` are allowed for non-sensitive UX state and profile inputs, but forbidden for secret-like keys.
- Guard coverage for this rule lives in `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`.

**Local iOS test targeting (Makefile):**

- `make ios-test IOS_ONLY_TESTING="PulsePlateTests/PlateViewTests"`
- `make ios-test IOS_ONLY_TESTING="PulsePlateUITests"`
- `make ios-test IOS_ONLY_TESTING="PulsePlateUITests" IOS_SKIP_TESTING=""` (override default skip behavior)
- Optional deterministic destination: `IOS_DESTINATION="platform=iOS Simulator,id=<UDID>"`

**Local vs CI differences:**

- **Local:** Default `iPhone 16e` (can be overridden via `IOS_SIM_NAME`/`IOS_SIM_OS`)
- **CI:** Auto-selects destination using **UDID-only** format (`platform=iOS Simulator,id=<UDID>`)
  - Prefers `iPhone 16e` → `iPhone 16` → `iPhone 16 Pro` → `iPhone 15` from available simulators
  - Pins iOS 18.6 runtime (fallback to iOS 18.x if 18.6 unavailable)
  - **Never uses `OS=latest`** (guard fails job if `latest` detected)
- Both use `-project PulsePlate.xcodeproj` (canonical: app scheme tests = project-based)
- Both use explicit `-only-testing:PulsePlateTests/ClassName` entries + `-parallel-testing-enabled NO` (canonical pattern)
- CI includes diagnostic steps: `xcodebuild -version`, `xcodebuild -list`, `xcodebuild -showdestinations`

**CI destination policy (hard rule):**

- **CI destination must be UDID-only:** `platform=iOS Simulator,id=<UDID>`
- **`OS=latest` is forbidden:** Job fails if destination contains `latest` (anti-nondeterminism guard)
- **Rationale:** UDID-only kills `latest` ambiguity, name mismatch, and OS version format issues on multi-runtime runners
- **Boot requirement:** If `xcodebuild test` cannot match UDID destination, boot + bootstatus is the first remediation step; keep UDID-only strategy. Some runners require simulator to be booted before `xcodebuild` can resolve destination by UDID.

**Device fallback (hard rule):**

- Preferred devices: `iPhone 16e → iPhone 16 → iPhone 16 Pro → iPhone 15 → iPhone 14`
- If none found: pick **any available iPhone** (sorted by name, then UDID)
- If no iPhone: pick **any available iOS simulator** (iPad acceptable)
- CI **must not fail** solely due to missing preferred simulators
- Output must include: `ios_runtime_id`, `device_name`, `udid`, and `DESTINATION`
- Step summary logs runtime, device, UDID, and destination for easy debugging
- **Testing fallback:** Override `PREFERRED_DEVICES` env var (e.g., `PREFERRED_DEVICES="iPhone 99,iPhone 98"`) **only for testing** to force fallback behavior. Default preferred list remains unchanged for normal CI runs.

## CI invariants (hard rules)

**Boot verification:**

- CI **must** run `xcrun simctl bootstatus "$UDID" -b` after boot
- `bootstatus -b` **must** succeed (exit code 0); CI fails if simulator doesn't become ready
- Timeout: 180 seconds (configurable via `SIM_BOOT_TIMEOUT_SECONDS` env var; default 180)
- Rationale: Deterministic boot verification prevents downstream "Unable to find a destination" errors; longer timeout accounts for runner data migrations (70-120s+)
- **Timeout tuning:** If two consecutive failures due to data migrations, increase `SIM_BOOT_TIMEOUT_SECONDS` to 240s and consider adding retry logic (shutdown → boot → bootstatus)

**System services warmup:**

- After bootstatus succeeds, CI runs `xcrun simctl launch "$UDID" com.apple.springboard` (best-effort)
- Warmup reduces flaky test failures due to uninitialized SpringBoard
- Rationale: Minimal overhead (2 seconds) with significant flakiness reduction

**Test execution:**

- CI **must** split build and test: `build-for-testing` → `test-without-building`
- Rationale: Faster diagnosis (build failed vs test runtime failed), targeted retries (retry test without rebuilding), better observability (separate step durations)

**Timeout policy:**

- `xcodebuild build-for-testing` **must** be wrapped in timeout (10 minutes)
- `xcodebuild test-without-building` **must** be wrapped in timeout (15 minutes)
- Rationale: Fail fast instead of consuming full job budget (25 minutes)
- Implementation: Python `subprocess.run(timeout=...)` (macOS doesn't have `timeout` by default)
- If timeout triggers, error message is explicit ("xcodebuild ... timed out after X minutes")

**Environment variables (hard rule):**

- Variables used in embedded Python scripts (heredoc) **must** be exported: `export DESTINATION`, `export UDID`
- Rationale: Python `os.environ.get()` requires exported variables; shell variables are not visible to subprocesses
- **Never interpolate shell vars into python code strings** (e.g., `python3 -c "... '$UDID' ..."`); always pass via env + `os.environ.get()`
- Rationale: Shell interpolation in python strings is fragile and error-prone; env vars are the canonical approach

**Debugging CI failures:**

1. Check Step Summary for: runtime, device, UDID, destination
2. Check logs for `bootstatus -b` exit code (must be 0)
3. Check logs for build-for-testing vs test-without-building failures
4. If timeout: check if 15-minute timeout triggered (vs job-level 25-minute timeout)

**Required (CI):**

- `ios-tests` GitHub Actions job must pass
- CI is the enforcement gate (blocks merge if tests fail)

**Test execution (canonical, split build/test):**

- CI **must** split build and test: `build-for-testing` → `test-without-building`
- **Step 1: Build for testing** (timeout: 10 minutes):
  ```bash
  xcodebuild build-for-testing \
    -project PulsePlate.xcodeproj \
    -scheme PulsePlate \
    -destination "$DESTINATION" \
    -configuration Debug \
    -derivedDataPath ../.derivedData \
    -enableCodeCoverage NO
  ```
- **Step 2: Run tests** (timeout: 15 minutes):
  ```bash
  # Canonical list: scripts/ios_test_targets.sh (run from ios/)
  xcodebuild test-without-building \
    -project PulsePlate.xcodeproj \
    -scheme PulsePlate \
    -skip-testing:PulsePlateUITests \
    $(../scripts/ios_test_targets.sh | tr ',' '\n' | while read t; do [ -n "$t" ] && echo "-only-testing:$t"; done) \
    -destination "$DESTINATION" \
    -derivedDataPath ../.derivedData \
    -enableCodeCoverage NO \
    -parallel-testing-enabled NO
  ```
- Project-based approach avoids workspace TestAction requirement
- Explicit test targeting ensures stable CI behavior
- Split build/test enables faster diagnosis and targeted retries

⚠️ **Hard rule (PR-559):** App scheme tests in CI must use **project-based** approach (`-project`, not `-workspace`). Workspace-based tests require explicit TestAction configuration, which app scheme does not have.

---

## iOS workflow: Cursor-first (hard rule)

**Default workflow:** 100% changes in Cursor (editor + terminal).
**Xcode is allowed only for:**

- Booting/running simulator
- Visual UI smoke checks (manual)
- Inspecting Build Phases when needed (rare)
- Opening `.xcresult` if debugging requires it

**Forbidden:**

- ❌ Doing routine code edits in Xcode (use Cursor)
- ❌ "Fix by clicking" without reflecting changes in repo files (pbxproj / sources)

### Canonical working directory (hard rule)

All iOS CLI commands must run from `ios/`:

```bash
cd ios
```

If `xcodebuild` says "does not contain an Xcode project" → you ran it from repo root.

### Daily commands (reference)

```bash
cd ios

# Show available devices (copy UDID for CI)
xcrun simctl list devices

# Run CI test suite (locally can use name, but UDID preferred)
# Run `xcrun simctl list devices` to find a valid simulator name (e.g., "iPhone 14").
# Canonical test list: scripts/ios_test_targets.sh
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "platform=iOS Simulator,name=<SIMULATOR_NAME>" \
  -configuration Debug \
  -skip-testing:PulsePlateUITests \
  $(../scripts/ios_test_targets.sh | tr ',' '\n' | while read t; do [ -n "$t" ] && echo "-only-testing:$t"; done)
```

### Simulator troubleshooting (runtime state issues)

If `xcodebuild test` fails with "Invalid device state" or "No such process", reset simulators:

```bash
cd ios

# 1) Shutdown and erase all simulators (most reliable)
xcrun simctl shutdown all || true
xcrun simctl erase all || true

# 2) Find UDID of needed device
# Replace "iPhone 14" with a simulator name that exists on your machine (see `xcrun simctl list devices`).
xcrun simctl list devices | rg "iPhone 14" -n

# 3) Boot and wait for readiness
xcrun simctl boot <UDID> || true
xcrun simctl bootstatus <UDID> -b || true
```

After reset, retry `xcodebuild test ... -destination "platform=iOS Simulator,id=<UDID>"`.

---

## Swift 6 / Concurrency policy for test mocks (hard rule)

Swift 6 treats some warnings as errors.

### Swift 6 concurrency for mocks

**Rule:** Test mocks with mutable fields must be explicitly marked as `@unchecked Sendable` **with a comment**, or be immutable/actor isolated.

**Goal:** Avoid accumulating "warning today → error tomorrow".

**Example:**

```swift
final class MockShoppingListService: ShoppingListService, @unchecked Sendable {
  // Test-only mock. Single-threaded by design.
  var result: Result<ShoppingListDTO, Error> = .success(...)
}
```

**Rule:** If CI emits "stored property of Sendable-conforming class is mutable" → fix it explicitly
(`@unchecked Sendable` + comment, or make property immutable/actor isolated).

---

## XCTest helpers: avoid cross-file symbol collisions (hard rule)

### Test helper scoping

**Rule:** Any test helper type that may be repeated across multiple files (`FailingURLProtocol` and similar) **must be `private`/`fileprivate`** to avoid redeclaration errors when using FileSystemSynchronized build files.

**Example:**

```swift
private final class FailingURLProtocol: URLProtocol { ... }
```

**Forbidden:**

- ❌ Reusing the same `final class FailingURLProtocol` at module scope in multiple files
  (causes `invalid redeclaration`)

**Rationale:** File-private classes prevent symbol collisions across test files while keeping helpers local to their test suites.

---

## Animated/UI helper tests policy (hard rule)

### Animation/UI-only tests CI policy

**Rule:** UI/Animation-only tests must not block CI.

**Mechanism:** Exclude such files via `PBXFileSystemSynchronizedBuildFileExceptionSet.membershipExceptions` (not via UI clicks).

**Rationale:** If a test depends on UI animation utilities/components that are not part of the public API surface (or not available in the test target), it must not block CI compilation.

**Implementation:**

- Create `PBXFileSystemSynchronizedBuildFileExceptionSet` for test target
- Add problematic test files to `membershipExceptions`
- Reference exception set in `PBXFileSystemSynchronizedRootGroup.exceptions`

**Example:** "AnimationTests.swift" (and similar UI-animation-only suites) must be excluded from CI compilation until stabilized and explicitly reintroduced via a dedicated PR.

### CI anchor test file policy (hard rule)

**Rule:** `__CIAnchorTests.swift` must be compiled **only** in `PulsePlateTests` target Sources build phase (`B6169A3E2E893CF200B218D8`); **never** in app target Sources build phase (`B6169A2F2E893CF100B218D8`).

**Rationale:** Test files must never be compiled into the app bundle. Anchor file exists solely to ensure test bundle executable generation in CI when using File System Synchronized groups.

**Verification:**
- `__CIAnchorTests.swift` must appear in `PBXSourcesBuildPhase` for `PulsePlateTests` target only
- App target Sources phase must not contain any test files

---

## ATS (App Transport Security) policy

**Debug builds:**

- `NSAllowsArbitraryLoads = true` (allows HTTP for local/dev endpoints)
- `NSAllowsLocalNetworking = true` (allows localhost/127.0.0.1)
- Configured in `PulsePlate/Info-Debug.plist`

**Release builds:**

- Strict ATS: `NSAllowsArbitraryLoads = false` (HTTPS only)
- `NSAllowsLocalNetworking = false`
- Configured in `PulsePlate/Info-Release.plist`

**Rationale:** Debug builds need HTTP access for local development and testing. Release builds must enforce HTTPS for App Store compliance.

---

## iOS Roadmap sync (reference)

For iOS localization + navigation sync plan, use:
`IOS_ROADMAP.md` (canonical).
