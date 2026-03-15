# PR #1172 — iOS UI Smoke Crash Triage Packet

**Run:** 23115321067 / **Job:** 67139818410
**Date:** 2026-03-15

## Failed logs summary

```
<unknown>:0: error: -[PulsePlateUITests.UISmokeTests testLaunch] : com.katsiaryna.pulseplate.dev crashed in <external symbol>
Test Case '-[PulsePlateUITests.UISmokeTests testLaunch]' failed (16.531 seconds).
** TEST EXECUTE FAILED **
Process completed with exit code 65.
```

## A/B/C classification

**Class A — App launch crash**

- App launched, ran ~16s, then crashed
- Signal: `crashed in <external symbol>`, exit 65
- Not Class B (no foreground timeout)
- Not Class C (bootstatus succeeded, UDID-only, no OS=latest)

## CI policy parity checklist

| Check | Result |
|-------|--------|
| UDID-only? | yes — `platform=iOS Simulator,id=F248267C-6C7E-4752-B627-8E1407A0AB92` |
| OS=latest absent? | yes |
| pinned Xcode? | yes — 16.4 |
| boot + bootstatus present/effective? | yes — succeeded after ~41s Data Migration |

## Suspected root cause

Data Migration (LaunchServicesMigrator, AddressBookLegacy, PreferencesMigrator) ran for ~41s before bootstatus. Per ios/AGENTS.md: "If two consecutive failures due to data migrations, increase SIM_BOOT_TIMEOUT_SECONDS... and consider adding retry logic". Simulator may need additional settle time after bootstatus before app launch to reduce fragile post-migration state.

## Minimal patch

- Add configurable `SIM_POST_BOOT_SETTLE_SECONDS` (default 5s) after SpringBoard warmup
- Increases settle from 2s to 5s in ios-ui-smoke job
- File: `.github/workflows/ci.yml`

## Next steps

1. Push fix, watch current-head required checks
2. If green → governance closeout (FIXED_MAPPING + PR body mirror)
3. If red → consider xcresult artifact upload for deeper diagnostics
