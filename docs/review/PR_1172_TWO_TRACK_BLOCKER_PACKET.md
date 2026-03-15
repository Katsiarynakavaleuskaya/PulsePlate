# PR #1172 — Two-Track Blocker Packet

**Date:** 2026-03-15
**Strategy:** Option 1 + 2 now; Option 3 (disable) only as last resort. No merge until required checks green.

---

## Track A — iOS UI Smoke (Launch Crash)

### Evidence

**Run 23116509095 (latest):**
```
t = 4.14s  Setting up automation session
com.katsiaryna.pulseplate.dev crashed in <external symbol>
t = 25.18s Tear Down
Test Case '...testLaunch' failed (25.425 seconds). exit 65
```

**Classification:** Class A — app launch crash during automation session setup. Not Class B (element timeout). Post-boot settle and runningForeground timeout do not fix.

### Suspected launch paths

| Path | File | Notes |
|------|------|-------|
| ProKeyProvider | `ios/PulsePlate/Services/ProKeyProvider.swift` | `#if DEBUG assertionFailure` on Keychain throw → crash in CI simulator |
| KeychainStore | `ios/PulsePlate/Services/KeychainStore.swift` | Throws on `errSec*` (non‑ItemNotFound). Simulator may return `errSecNotAvailable` or similar |
| AppStoreScreenshotContext | `ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift` | `preconditionFailure` in screenshot mode; CI has no `-appstore-screenshot-mode` → skip |
| SubscriptionManager | `ios/PulsePlate/Services/SubscriptionManager.swift` | Uses `apiKeyProvider` closure; `bootstrap()` → `loadProducts()` (StoreKit) before first ProKeyProvider call on fresh install |
| HomeView.hasProKey | `ios/PulsePlate/Views/HomeView.swift` | `ProKeyProvider.value()` when HomeView renders; first launch shows WelcomeFlowView → HomeView may not render yet |

**Primary hypothesis:** `ProKeyProvider.value()` catches Keychain throws and in DEBUG calls `assertionFailure()`. In CI simulator, Keychain can legitimately fail (no keychain, different env). `assertionFailure` terminates the app.

### Minimal patch (hypothesis)

**ProKeyProvider.swift:** Remove or make conditional `assertionFailure` in DEBUG when Keychain throws. Callers already handle `nil`; the assertion was for programmer debugging but causes false crashes in CI.

```swift
// Current (crashes in CI):
} catch {
    #if DEBUG
    assertionFailure("Keychain error while reading PRO key: \(error)")
    #endif
    return nil
}

// Proposed: return nil without assertionFailure (or gate on !ProcessInfo.isUITesting)
```

### Crash evidence loop

1. **Added:** `Upload xcresult on failure` step in `.github/workflows/ci.yml` (ios-ui-smoke job). On failure, uploads `ios/.derivedData/Logs/Test/` as artifact `ios-ui-smoke-xcresult-<run_id>`.
2. **Next run:** After next failure, download artifact and inspect `.xcresult` for crash stack trace.
3. **If logs insufficient:** Consider `xcrun xcresulttool get --path ... --format json` or similar in CI to extract crash info.

---

## Track B — OpenAPI Sync

### Evidence

**CI failure:** `npm ci` step fails with `ECONNRESET` / network aborted. Not schema drift.

**Local verification:** `make openapi` and `make openapi-check` pass. No drift in `frontend/src/api/openapi.json` or `frontend/src/api/schema.ts`.

### Verdict

| Check | Result |
|-------|--------|
| OpenAPI artifact drift? | No — local `make openapi-check` passes |
| Root cause | Network / `npm ci` transient (ECONNRESET) |
| Next step | Rerun required checks. If reproducible, treat as CI/install issue, not OpenAPI artifact. |

### Toolchain notes (non-blocking)

- Node 20 deprecated in GitHub Actions; `style-dictionary` wants Node ≥22.
- Not the immediate cause of `ECONNRESET`; follow-up for later.

---

## Governance

- **No merge** until both required checks green.
- **No governance closeout** until smoke is green.
- **No disable** of `ios-ui-smoke` unless proven purely infrastructural; then must be tracked in BACKLOG_LEDGER as bad-skip with DoD.

---

## Next actions

1. **Track A:** Push xcresult upload step; on next failure, download artifact and inspect crash.
2. **Track A:** If ProKeyProvider hypothesis confirmed, apply minimal patch (remove assertionFailure).
3. **Track B:** Rerun OpenAPI sync; if still fails, investigate network/install path separately.
4. **Both:** Do not mix fixes; keep scope minimal.
