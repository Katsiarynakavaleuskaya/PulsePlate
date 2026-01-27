# PR-Q2b — iOS UITests bundle load failure audit (exit 65)

**Date (ISO 8601):** 2026-01-27Z
**Revision:** v1
**Owner:** @katsiaryna_kavaleuskaya
**Track:** Quality / CI Trust (iOS)

## 0) Scope / Non-goals

### Scope

- Establish reproducible evidence for the iOS UI test runner failure:
  - `PulsePlateUITests.xctest` fails to load because its executable is missing.
- Produce a ranked hypothesis list for the minimal `project.pbxproj` fix.
- Define DoD for the remediation PR that will:
  - make UI test bundle loadable locally
  - enable a minimal CI UI-smoke job (separate from unit tests)

### Non-goals

- Product/UX changes are out of scope.
- New features are out of scope.
- No “green because skipped”.
- No remediation changes in this PR (audit-only).

## A) Evidence (observed)

### A1) Repro command (local)

This is the canonical Q2b reproduction after Q2a (`make ios-test` wiring) is merged:

```bash
make ios-test IOS_ONLY_TESTING="PulsePlateUITests" IOS_SKIP_TESTING=""
```

> NOTE: Destination is intentionally not pinned to a specific simulator UDID in docs to keep evidence
> durable across machines/CI runners. The observed failure is independent of the specific simulator.

### A2) Observed output (raw excerpt; first failure)

```text
PulsePlateUITests-Runner[...] [loading] Cannot find executable for CFBundle .../PulsePlateUITests.xctest> (not loaded)
NSBundle .../PulsePlateUITests.xctest/ loading failed because of an error Error Domain=NSCocoaErrorDomain Code=4
"Не удалось загрузить пакет «PulsePlateUITests», так как не найден исполняемый файл."

Testing failed:
  PulsePlateUITests-Runner (...) encountered an error (Failed to load the test bundle. (Underlying Error: ...))

make: *** [ios-test] Error 65
```

**Observed exit:** `xcodebuild` failed (exit code 65); `make` wraps this as exit 2.

### A3) Classification

- ❌ Not a UI regression
- ❌ Not a test logic failure
- ✅ Infra / build-product issue:
  - UI test bundle exists, but the bundle executable is missing

> This failure occurs **before** any UI test code is executed.

## B) Inspection commands (for audit completeness)

Run these locally to confirm whether the `.xctest` bundle contains an executable:

```bash
# 1) Locate UI test bundle in DerivedData (path varies by build)
ls -la .derivedData/Build/Products/Debug-iphonesimulator/PulsePlateUITests-Runner.app/PlugIns/PulsePlateUITests.xctest || true

# 2) Confirm bundle Info.plist and the expected executable name
plutil -p .derivedData/Build/Products/Debug-iphonesimulator/PulsePlateUITests-Runner.app/PlugIns/PulsePlateUITests.xctest/Info.plist || true

# 3) Check if the bundle executable exists (usually same as CFBundleExecutable)
ls -la .derivedData/Build/Products/Debug-iphonesimulator/PulsePlateUITests-Runner.app/PlugIns/PulsePlateUITests.xctest/* || true

# 4) Build settings that commonly explain “no executable in xctest”
cd ios
xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate -showBuildSettings \
  | rg -n "TEST_HOST|BUNDLE_LOADER|WRAPPER_EXTENSION|EXECUTABLE_NAME|PRODUCT_NAME|PRODUCT_BUNDLE_IDENTIFIER"
```

## C) Ranked hypotheses (most likely first)

1) **UITests target is not producing a binary**
   - e.g., missing/incorrect `PBXSourcesBuildPhase`, or target marked as “bundle only” with no compile sources.
2) **UITests bundle is built, but executable is not copied/embedded into the runner**
   - runner app contains `.xctest/Info.plist` but not the binary referenced by `CFBundleExecutable`.
3) **Scheme/test action mismatch**
   - `xcodebuild test` runs a scheme/config that does not build the UITests target product correctly.
4) **Broken `TEST_HOST` / `BUNDLE_LOADER` configuration**
   - causes Xcode to generate runner artifacts incorrectly for UI tests.
5) **File-system-synchronized groups / exceptions misconfiguration**
   - target membership / exceptions prevent the UITests target from compiling sources into an executable.

## D) Decision

**Decision:** Remediation required in `ios/PulsePlate.xcodeproj/project.pbxproj` (build-product correctness).

- This is a **P0 blocker** for restoring CI trust: UI tests cannot run at all.
- Fix must be minimal and auditable (no “magic” UI changes).

## E) DoD (for remediation PR-Q2b)

DoD gates (all required):

- **G1:** `PulsePlateUITests.xctest` bundle contains an executable (`CFBundleExecutable` file exists).
- **G2:** Local UI-only run loads the test bundle (runner starts executing tests):
  - `make ios-test IOS_ONLY_TESTING="PulsePlateUITests" IOS_SKIP_TESTING=""` no longer fails with Code=4.
- **G3:** CI has a dedicated `ios-ui-smoke` job (separate from unit tests) that runs minimal UI smoke
  without `-skip-testing:PulsePlateUITests`.
- **G4:** UI-smoke job is green for ≥2 consecutive runs (PR checks / reruns).

## Security Notes

- UI tests must not send real credentials or hit real endpoints.
- Any network must be stubbed/isolated to keep CI deterministic.
