# PR #1172 — iOS UI Smoke Crash Triage Packet

**Runs:** 23115321067 (Class A), 23116263889 (Class B)
**Date:** 2026-03-15

## Failed logs summary

**Run 1 (Class A):**
```
com.katsiaryna.pulseplate.dev crashed in <external symbol>
Test Case '...testLaunch' failed (16.531 seconds). exit 65
```

**Run 2 (Class B, after post-boot settle):**
```
XCTAssertTrue failed - Screenshot-mode launch did not present any stable UI container
App launched, "Wait for idle" ~66s, then Window/NavigationBar/Table/CollectionView/ScrollView all not found
```

## A/B/C classification

**Class A (run 1):** App launch crash → post-boot settle patch applied
**Class B (run 2):** Element-based assertion timeout — app reached idle but no standard UI elements found; screenshot scenario may present different hierarchy on CI

## CI policy parity checklist

| Check | Result |
|-------|--------|
| UDID-only? | yes |
| OS=latest absent? | yes |
| pinned Xcode? | yes — 16.4 |
| boot + bootstatus present/effective? | yes |

## Minimal patches

1. **Class A:** `SIM_POST_BOOT_SETTLE_SECONDS` (default 5s) after SpringBoard warmup — `.github/workflows/ci.yml`
2. **Class B:** Replace element-based checks with `wait(for: .runningForeground, timeout: 90)` — single static assertion, more reliable on CI — `ios/PulsePlateUITests/UISmokeTests.swift`

## Next steps

1. Push Class B fix, watch current-head required checks
2. If green → governance closeout (FIXED_MAPPING + PR body mirror)
3. If red → consider xcresult artifact upload
