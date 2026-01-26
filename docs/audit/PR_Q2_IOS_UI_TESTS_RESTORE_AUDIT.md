# PR-603 (PR-Q2) — iOS UI tests restore audit (PlateViewTests + PulsePlateUITests)

**Date:** 2026-01-26 (UTC)
**Revision:** v2
**Owner:** @katsiaryna_kavaleuskaya
**Track:** Quality / CI Trust (iOS)

## 0) Scope / Non-goals

### Scope

- Restore iOS test signal in CI by:
  - Stabilizing `PlateViewTests` (no crashes).
  - Enabling a **minimal UI smoke** in CI (no `-skip-testing:PulsePlateUITests`).

### Non-goals

- No product/UX changes.
- No new features.
- No “green because skipped”.

---

## A) Audit

### A1) Where exactly are UI tests disabled today?

**Evidence commands:**

```bash
rg -n "skip-testing:PulsePlateUITests|only-testing|xcodebuild (test|test-without-building|build-for-testing)" .github/workflows Makefile ios/AGENTS.md
```

**Observed output (raw excerpt):**

```text
.github/workflows/ci.yml:999:              "-skip-testing:PulsePlateUITests",
Makefile:322:            -skip-testing:PulsePlateUITests \
ios/AGENTS.md:144:    -skip-testing:PulsePlateUITests \
```

**Decision:** ✅ Disabled locations identified (CI workflow + local Make target + docs).

---

### A2) What fails when we try to run UI tests (UI-only)?

**Evidence command (local):**

```bash
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "platform=iOS Simulator,name=iPhone 15" \
  -configuration Debug \
  -derivedDataPath ../.derivedData \
  -enableCodeCoverage NO \
  -parallel-testing-enabled NO \
  -only-testing:PulsePlateUITests/PulsePlateUITests/testExample
```

NOTE: Simulator destination intentionally uses a generic form
(`platform=iOS Simulator,name=iPhone 15`) to keep the audit durable.
The observed failure is independent of a specific simulator UDID.

**Observed output (raw excerpt; first failure):**

```text
PulsePlateUITests-Runner[...] [loading] Cannot find executable for CFBundle .../PulsePlateUITests.xctest> (not loaded)
NSBundle .../PulsePlateUITests.xctest/ loading failed because of an error Error Domain=NSCocoaErrorDomain Code=4
"Не удалось загрузить пакет «PulsePlateUITests», так как не найден исполняемый файл."
...
Testing failed:
  PulsePlateUITests-Runner (...) encountered an error (Failed to load the test bundle. ...)
** TEST FAILED **
```

**Observed exit:** non-zero (`xcodebuild` failed; exit code 65).

**Classification:**

- ❌ Not a UI regression
- ❌ Not a test logic failure
- ✅ Infra / build-product issue:
  - missing test bundle executable
  - runner misconfiguration OR build-for-testing gap

> This failure occurs **before** any UI test code is executed.

**Decision:** ❌ UI tests are not runnable yet; remediation required (bundle/executable missing).

---

### A2.1) Local developer ergonomics: does Makefile support UI-only runs?

**Evidence command:**

```bash
make ios-test IOS_ONLY_TESTING="PulsePlateUITests/PulsePlateUITests/testExample" IOS_SKIP_TESTING=""
```

**Observed output (raw):**

```text
xcodebuild: error: Unknown build action ' -only-testing:PulsePlateUITests/PulsePlateUITests/testExample'.
make: *** [ios-test] Error 65
```

**Decision:** ❌ Current Makefile does NOT support UI-only execution.
This blocks:

- local reproduction
- CI smoke enablement

Remediation required.

---

### A3) PlateViewTests (unit) — flake or real crash?

**Evidence command (local):**

```bash
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "platform=iOS Simulator,name=iPhone 15" \
  -configuration Debug \
  -derivedDataPath ../.derivedData \
  -enableCodeCoverage NO \
  -parallel-testing-enabled NO \
  -only-testing:PulsePlateTests/PlateViewTests
```

**Observed output (raw excerpt):**

```text
Test Suite 'PlateViewTests' started ...
Test Case '-[PulsePlateTests.PlateViewTests testColorMapping]' passed
Test Case '-[PulsePlateTests.PlateViewTests testPlateViewInitialization]' passed
** TEST SUCCEEDED **
```

**Note:** PlateViewTests passing confirms that prior crashes were not due to view-layer logic, but to test execution context.

**Decision:** ✅ PlateViewTests can be made stable (crash removed).

---

## B) Remediation plan (from audit)

### B1) CI strategy

**Decision:** We will introduce a dedicated UI-smoke job.

**Rationale:**

- avoid flakiness bleeding into unit test signal
- preserve fast feedback loop
- isolate infra failures

Minimum acceptable signal: `PulsePlateUITests/PulsePlateUITests/testExample`.
Smoke is intentionally minimal; expansion is out of scope for PR-603.

### B2) DoD (hard)

DoD gates (all required):

G1. No `-skip-testing` flags for UI path
G2. UI-smoke green in CI (≥2 runs)
G3. PlateViewTests stable (no malloc/free crashes)
G4. Local UI-only command documented and verified (Makefile or explicit `xcodebuild`)

---

## Security Notes

- UI tests must not use real credentials or hit real endpoints.
- Any network should be stubbed/isolated for deterministic CI.

---

## Marketing & GTM (minimal)

Milestone: “CI trust restored: iOS UI tests executing (no skips)”.
