# PR-562 CI Checklist

**PR:** PR-562 / PR-563 (Thin HTTP Adapter iOS)
**Date:** 2026-01-22

---

## Pre-CI Checks

### 1. New Test Files Added to Target

**Check:** New test files must be in `PulsePlateTests` target.

**Files to verify:**
- `ios/PulsePlateTests/Networking/HTTPClientTests.swift`
- `ios/PulsePlateTests/Networking/APIClientTests.swift`
- `ios/PulsePlateTests/Services/BMIServiceThinAdapterTests.swift`

**Command:**
```bash
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -showBuildSettings 2>&1 | grep -A 5 "PulsePlateTests" | head -20
```

**Expected:** All 3 test files should be listed in test target sources.

---

### 2. CI Will Run New Tests

**Current CI config:** `.github/workflows/ci.yml` lines 922-924

**Check:** CI uses `-only-testing:PulsePlateTests/BMIServiceTests` (legacy), but new tests are:
- `HTTPClientTests`
- `APIClientTests`
- `BMIServiceThinAdapterTests`

**Options:**

#### A) CI runs all tests in PulsePlateTests target (default behavior)
- ✅ New tests will run automatically
- No CI changes needed

#### B) CI uses explicit `-only-testing` flags
- ⚠️ Need to add new test classes to CI config
- Add: `-only-testing:PulsePlateTests/HTTPClientTests`
- Add: `-only-testing:PulsePlateTests/APIClientTests`
- Add: `-only-testing:PulsePlateTests/BMIServiceThinAdapterTests`

**Verification:**
```bash
# Check if CI uses -only-testing
grep -n "-only-testing" .github/workflows/ci.yml

# If yes, verify new tests are included
grep -E "HTTPClientTests|APIClientTests|BMIServiceThinAdapterTests" .github/workflows/ci.yml
```

---

### 3. Xcode Project File Changes

**Check:** `ios/PulsePlate.xcodeproj/project.pbxproj` was modified.

**Verify:** New files are properly added to:
- `PulsePlate` target (source files)
- `PulsePlateTests` target (test files)

**Command:**
```bash
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -list 2>&1 | grep -A 10 "Test targets"
```

---

## CI Run Verification

### After CI Completes

**Check CI logs for:**
- ✅ `HTTPClientTests` test results (4 tests)
- ✅ `APIClientTests` test results (3 tests)
- ✅ `BMIServiceThinAdapterTests` test results (3 tests)
- ✅ Total: 10 tests passing

**If tests don't run:**
1. Check Xcode project file (target membership)
2. Check CI config (explicit `-only-testing` flags)
3. Check test file compilation (Swift syntax errors)

---

## Common CI Issues

### Issue 1: "Test target not found"

**Cause:** Test files not added to `PulsePlateTests` target.

**Fix:** Add files to target in Xcode or update `project.pbxproj`.

### Issue 2: "No tests to run"

**Cause:** CI uses explicit `-only-testing` flags that don't include new tests.

**Fix:** Add new test classes to CI config (see Option B above).

### Issue 3: "Compilation errors"

**Cause:** Swift syntax errors or missing imports.

**Fix:** Run `xcodebuild build` locally to catch errors before CI.

---

## Quick Local Verification

```bash
# 1. Build project
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  build

# 2. Run new tests only
cd ios && xcodebuild -project PulsePlate.xcodeproj -scheme PulsePlate \
  -destination 'platform=iOS Simulator,name=iPhone 16' \
  -only-testing:PulsePlateTests/HTTPClientTests \
  -only-testing:PulsePlateTests/APIClientTests \
  -only-testing:PulsePlateTests/BMIServiceThinAdapterTests \
  test

# 3. Verify all 10 tests pass
```

---

**Last updated:** 2026-01-22
