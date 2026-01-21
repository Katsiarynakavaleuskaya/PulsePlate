# PR-560: iOS CI Stability Hardening — Audit Report

**Date:** 2026-01-20
**Scope:** CI workflow stability improvements for iOS unit tests
**Status:** Pre-implementation audit

---

## Executive Summary

**Audit result:** CI uses boot + bootstatus (with `|| true`), single `xcodebuild test` command, job-level timeout (25 min); **missing** deterministic bootstatus verification, per-command timeout, split build/test, warmup; **proposed minimal changes:** enforce bootstatus -b, add timeout wrapper, split build/test, document canonical recipe.

---

## 1. Current State Analysis

### 1.1 Simulator Boot Sequence (`.github/workflows/ci.yml:809-818`)

**Current implementation:**
```bash
xcrun simctl boot "$UDID" || true
echo "Waiting for simulator to be ready..."
xcrun simctl bootstatus "$UDID" -b || true
echo "✓ Simulator booted and ready"
```

**Issues identified:**
- ❌ **`|| true` masks failures:** If boot or bootstatus fails, CI continues anyway, leading to "Unable to find a destination" errors later
- ❌ **No verification:** `bootstatus -b` exit code is ignored; simulator may not be ready when `xcodebuild test` runs
- ❌ **No warmup:** System services (SpringBoard, etc.) may not be initialized, causing flaky test failures

**Evidence:**
- Historical CI failures: "Unable to find a destination matching the provided destination specifier" after boot
- No explicit check that `bootstatus -b` actually succeeded

**Rationale for change:**
- Deterministic boot verification prevents downstream failures
- Explicit failure mode (boot fails → CI fails fast) is better than silent continuation

---

### 1.2 Test Execution (`.github/workflows/ci.yml:830-843`)

**Current implementation:**
```bash
xcodebuild test \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -skip-testing:PulsePlateUITests \
  -only-testing:PulsePlateTests/ThinClientGuardsTests \
  -only-testing:PulsePlateTests/BMIServiceTests \
  -only-testing:PulsePlateTests/BMIResponseDecodingTests \
  -only-testing:PulsePlateTests/BMIRequestEncodingTests \
  -only-testing:PulsePlateTests/LocaleParsingTests \
  -destination "$DESTINATION" \
  -configuration Debug \
  -derivedDataPath ../.derivedData \
  -enableCodeCoverage NO \
  -parallel-testing-enabled NO
```

**Issues identified:**
- ❌ **No timeout wrapper:** If `xcodebuild test` hangs (network issue, simulator deadlock), job waits for full 25-minute timeout
- ❌ **Single command:** Build and test are combined; cannot diagnose "build failed" vs "test runtime failed" separately
- ❌ **No retry mechanism:** Transient failures (simulator state, network) cause full job failure

**Evidence:**
- Job timeout is 25 minutes (`.github/workflows/ci.yml:581`), but individual command has no timeout
- Historical CI runs show "hanging" behavior where `xcodebuild test` never completes

**Rationale for change:**
- Per-command timeout (e.g., 15 minutes) fails fast instead of consuming full job budget
- Split build/test enables targeted retries (retry test without rebuilding)

---

### 1.3 Timeout Configuration

**Current state:**
- Job-level timeout: **25 minutes** (`.github/workflows/ci.yml:581`)
- No per-command timeout for `xcodebuild test`
- No timeout for `bootstatus -b` (relies on default simctl timeout)

**Issues identified:**
- ❌ **Job timeout too coarse:** If `xcodebuild test` hangs at minute 5, job waits 20 more minutes before failing
- ❌ **No timeout for bootstatus:** If simulator never becomes ready, `bootstatus -b` may wait indefinitely (though simctl has internal timeout)

**Rationale for change:**
- Per-command timeout (15 minutes for `xcodebuild test`) provides faster feedback
- Explicit timeout for `bootstatus -b` (180 seconds, configurable via `SIM_BOOT_TIMEOUT_SECONDS`) prevents indefinite waits and accounts for GitHub runner data migrations (70-120s+)

---

### 1.4 Documentation Alignment

**Current state (`ios/AGENTS.md`):**
- ✅ Documents boot requirement (line 169)
- ✅ Documents UDID-only destination (line 166)
- ✅ Documents device fallback (line 171-178)
- ❌ **Missing:** Explicit bootstatus -b requirement
- ❌ **Missing:** Timeout policy
- ❌ **Missing:** Split build/test canonical recipe

**Issues identified:**
- Documentation says "boot + bootstatus is the first remediation step" but doesn't mandate it as **required** in CI
- No mention of timeout wrappers
- No mention of split build/test as canonical pattern

**Rationale for change:**
- Canonical recipe must be documented to prevent regression
- Timeout policy prevents "hanging CI" anti-pattern

---

## 2. Proposed Changes

### 2.1 Enforce Bootstatus Verification

**Change:**
```bash
# Before:
xcrun simctl bootstatus "$UDID" -b || true

# After (illustrative snippet; actual implementation uses Python with os.environ.get("UDID")):
# Timeout: 180 seconds (GitHub runners may need 70-120s+ for data migrations)
echo "Waiting for simulator to be ready (timeout: 180s)..."
python3 - << 'PY'
import os, subprocess, sys
udid = os.environ.get("UDID", "")
timeout_s = int(os.environ.get("SIM_BOOT_TIMEOUT_SECONDS", "180"))
if not udid:
    print("::error::UDID is empty", file=sys.stderr)
    sys.exit(1)
try:
    subprocess.run(["xcrun", "simctl", "bootstatus", udid, "-b"], timeout=timeout_s, check=True)
except subprocess.TimeoutExpired:
    print(f"::error::Simulator not ready after {timeout_s}s", file=sys.stderr)
    sys.exit(1)
PY
echo "✓ Simulator booted and ready"
```

**Rationale:**
- Explicit failure mode: if simulator doesn't boot, CI fails fast
- Timeout prevents indefinite waits
- Diagnostic output helps debugging

**Risk:**
- Low: If simulator genuinely fails to boot, failing fast is correct behavior
- Mitigation: Diagnostic output helps identify root cause

---

### 2.2 Add System Services Warmup

**Change:**
```bash
# After bootstatus succeeds:
echo "Warming up system services..."
xcrun simctl launch "$UDID" com.apple.springboard || true
sleep 2
echo "✓ System services ready"
```

**Rationale:**
- Reduces flaky test failures due to uninitialized SpringBoard
- Minimal overhead (2 seconds)
- `|| true` acceptable here (warmup is best-effort)

**Risk:**
- Low: Warmup failure doesn't block tests (best-effort)
- Benefit: Reduces flakiness

---

### 2.3 Split Build and Test

**Change:**
```bash
# Step 1: Build for testing
echo "=== Building for testing ==="
xcodebuild build-for-testing \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -destination "$DESTINATION" \
  -configuration Debug \
  -derivedDataPath ../.derivedData \
  -enableCodeCoverage NO

# Step 2: Run tests (without building)
echo "=== Running tests ==="
xcodebuild test-without-building \
  -project PulsePlate.xcodeproj \
  -scheme PulsePlate \
  -skip-testing:PulsePlateUITests \
  -only-testing:PulsePlateTests/ThinClientGuardsTests \
  -only-testing:PulsePlateTests/BMIServiceTests \
  -only-testing:PulsePlateTests/BMIResponseDecodingTests \
  -only-testing:PulsePlateTests/BMIRequestEncodingTests \
  -only-testing:PulsePlateTests/LocaleParsingTests \
  -destination "$DESTINATION" \
  -derivedDataPath ../.derivedData \
  -enableCodeCoverage NO \
  -parallel-testing-enabled NO
```

**Rationale:**
- **Faster diagnosis:** "Build failed" vs "Test runtime failed" are separate errors
- **Targeted retries:** Can retry `test-without-building` without rebuilding
- **Better observability:** Step summary shows build vs test duration separately

**Risk:**
- Low: Split is standard Xcode pattern, no functional change
- Benefit: Improved debugging and retry efficiency

---

### 2.4 Add Timeout Wrapper

**Change:**
```bash
# macOS doesn't have `timeout` by default; use Python or gtimeout (if installed)
# Fallback: use Python subprocess with timeout

python3 - << 'PY'
import subprocess
import sys
import os

cmd = [
    "xcodebuild", "test-without-building",
    "-project", "PulsePlate.xcodeproj",
    "-scheme", "PulsePlate",
    # ... other args ...
]

try:
    result = subprocess.run(cmd, timeout=900, check=True)  # 15 minutes
except subprocess.TimeoutExpired:
    print("::error::xcodebuild test timed out after 15 minutes")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    sys.exit(e.returncode)
PY
```

**Alternative (simpler, if `gtimeout` available):**
```bash
# Install via: brew install coreutils
if command -v gtimeout >/dev/null 2>&1; then
  gtimeout 900 xcodebuild test-without-building ...
else
  # Fallback: no timeout (rely on job timeout)
  xcodebuild test-without-building ...
fi
```

**Rationale:**
- **Fail fast:** 15-minute timeout prevents consuming full 25-minute job budget
- **Better diagnostics:** Timeout error is explicit, not "job timed out"

**Risk:**
- Medium: macOS doesn't have `timeout` by default; need Python fallback or `gtimeout`
- Mitigation: Python is available on GitHub Actions macOS runners

---

## 3. Post-Audit Evidence Requirements

After implementation, PR must demonstrate:

- [ ] **Step Summary shows:**
  - Runtime, device, UDID, destination (already present)
  - `bootstatus -b` exit code (success/failure)
  - Build-for-testing completion time
  - Test-without-building completion time

- [ ] **Logs show:**
  - `bootstatus -b` passed (not `|| true` ignored failure)
  - System services warmup completed
  - Build-for-testing succeeded
  - Test-without-building succeeded (or failed with explicit error)

- [ ] **Timeout behavior:**
  - If `xcodebuild test` hangs, timeout triggers within 15 minutes (not 25)
  - Timeout error message is explicit

---

## 4. Documentation Updates

### 4.1 `ios/AGENTS.md` Updates

**Add section: "CI invariants (hard rules)":**
```markdown
## CI invariants (hard rules)

**Boot verification:**
- CI **must** run `xcrun simctl bootstatus "$UDID" -b` after boot
- `bootstatus -b` **must** succeed (exit code 0); CI fails if simulator doesn't become ready
- Timeout: 180 seconds (configurable via `SIM_BOOT_TIMEOUT_SECONDS`; GitHub runners may need 70-120s+ for data migrations)

**System services warmup:**
- After bootstatus succeeds, CI runs `xcrun simctl launch "$UDID" com.apple.springboard` (best-effort)
- Warmup reduces flaky test failures due to uninitialized SpringBoard

**Test execution:**
- CI **must** split build and test: `build-for-testing` → `test-without-building`
- Rationale: faster diagnosis, targeted retries, better observability

**Timeout policy:**
- `xcodebuild test-without-building` **must** be wrapped in timeout (15 minutes)
- Rationale: fail fast instead of consuming full job budget (25 minutes)
- Implementation: Python `subprocess.run(timeout=900)` (macOS doesn't have `timeout` by default)
```

**Update "Debugging recipe" section:**
```markdown
**Debugging CI failures:**
1. Check Step Summary for: runtime, device, UDID, destination
2. Check logs for `bootstatus -b` exit code (must be 0)
3. Check logs for build-for-testing vs test-without-building failures
4. If timeout: check if 15-minute timeout triggered (vs job-level 25-minute timeout)
```

---

### 4.2 `docs/roadmap/BACKLOG_LEDGER.md` Updates

**Add entry:**
```markdown
## Closed Items

### CI iOS stability hardening (PR-560)
- **Owner:** @katsiaryna_kavaleuskaya
- **Priority:** P0
- **Status:** Closed (merged PR-560)
- **DoD:**
  - [x] Enforce bootstatus -b verification (no `|| true`)
  - [x] Add system services warmup
  - [x] Split build-for-testing / test-without-building
  - [x] Add timeout wrapper (15 minutes) for xcodebuild test
  - [x] Update ios/AGENTS.md with canonical CI recipe
  - [x] CI green on main-compatible workflow
- **Links:**
  - PR: #560
  - Audit: `docs/audit/PR_560_CI_IOS_STABILITY_AUDIT.md`
```

---

## 5. Risk Assessment

### 5.1 Implementation Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|-------|------------|
| `bootstatus -b` fails on some runners | Medium | High | Diagnostic output helps identify root cause; explicit failure is better than silent continuation |
| Timeout wrapper adds complexity | Low | Medium | Python fallback is standard; well-documented |
| Split build/test increases step count | Low | Low | Benefit (better diagnostics) outweighs minor complexity |

### 5.2 Regression Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|-------|------------|
| Stricter boot verification causes false failures | Low | Medium | 60-second timeout is generous; diagnostic output helps |
| Timeout too aggressive (15 min) | Low | Medium | Can adjust based on actual test duration (currently ~5-10 min) |

---

## 6. DoD (Definition of Done)

- [ ] **CI changes:**
  - [ ] Enforce `bootstatus -b` (remove `|| true`, add timeout)
  - [ ] Add system services warmup
  - [ ] Split `build-for-testing` / `test-without-building`
  - [ ] Add timeout wrapper (15 minutes) for `test-without-building`

- [ ] **Documentation:**
  - [ ] Update `ios/AGENTS.md` with CI invariants section
  - [ ] Update `ios/AGENTS.md` debugging recipe
  - [ ] Update `docs/roadmap/BACKLOG_LEDGER.md` (close item)

- [ ] **Verification:**
  - [ ] CI green on `main`-compatible workflow
  - [ ] Step Summary shows bootstatus, build, test separately
  - [ ] Logs show explicit bootstatus success (not `|| true` ignored)

- [ ] **PR hygiene:**
  - [ ] PR description contains "Audit → Changes → Post-audit evidence"
  - [ ] Diff is minimal (only CI + docs)
  - [ ] Commits follow conventional format

---

## 7. Implementation Plan

### 7.1 Commits (recommended: 2 commits)

1. **`fix(ci-ios): enforce bootstatus verification + split build/test + timeout`**
   - Remove `|| true` from bootstatus
   - Add timeout for bootstatus (180s, configurable via env)
   - Add system services warmup
   - Split `xcodebuild test` into `build-for-testing` + `test-without-building`
   - Add timeout wrapper (15 min) for `test-without-building`

2. **`docs(ios): codify CI stability policy in AGENTS and ledger`**
   - Add "CI invariants" section to `ios/AGENTS.md`
   - Update debugging recipe
   - Close backlog item in `BACKLOG_LEDGER.md`

### 7.2 Testing Strategy

**Local verification:**
```bash
# Test bootstatus enforcement (should fail if simulator not ready)
xcrun simctl bootstatus <UDID> -b

# Test split build/test
xcodebuild build-for-testing -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=<UDID>"
xcodebuild test-without-building -project PulsePlate.xcodeproj -scheme PulsePlate -destination "platform=iOS Simulator,id=<UDID>" -only-testing:PulsePlateTests/ThinClientGuardsTests
```

**CI verification:**
- Run PR against `main`-compatible workflow
- Verify Step Summary shows bootstatus, build, test separately
- Verify logs show explicit bootstatus success

---

## 8. Conclusion

**Summary:**
- Current CI has boot + bootstatus but ignores failures (`|| true`)
- Single `xcodebuild test` command prevents targeted retries
- No timeout wrapper causes full job timeout (25 min) on hangs
- Documentation doesn't mandate canonical recipe

**Proposed changes:**
- Enforce bootstatus verification (fail fast if simulator not ready)
- Add system services warmup (reduce flakiness)
- Split build/test (better diagnostics, targeted retries)
- Add timeout wrapper (fail fast, 15 min)

**Expected outcome:**
- More deterministic CI (explicit failures, not silent continuation)
- Faster feedback (timeout at 15 min, not 25 min)
- Better observability (split steps, explicit bootstatus)

**Next steps:**
1. Implement changes in `.github/workflows/ci.yml`
2. Update `ios/AGENTS.md` and `BACKLOG_LEDGER.md`
3. Verify CI green on PR
4. Merge PR-560

---

**Audit completed:** 2026-01-20
**Next review:** After PR-560 merge (verify post-audit evidence)
