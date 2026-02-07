# iOS Docs ↔ BACKLOG_LEDGER Alignment Audit (2026-02-06)

**Date:** 6 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**Scope:** Docs-only (repo-truth alignment)

## Update (2026-02-07)

PR-667 merged on 7 February 2026 and changed repo truth for Plate (PRO): iOS now uses canonical
`GET /api/v1/pro/nutrition/daily`. The “before” evidence captured below is therefore partially stale.

See: `docs/audit/IOS_DOCS_LEDGER_ALIGNMENT_AUDIT_2026-02-07.md`

## Problem statement

iOS-facing canonical docs and `BACKLOG_LEDGER.md` drifted from repo truth (entrypoint, key handling, and nutrition endpoint story). This creates false assumptions that slow down Slice 1–3 delivery and can hide security risks (deprecated aliases).

This audit records **evidence (commands + file:line pointers)** and the **docs-only changes applied** to restore alignment.

## Evidence (before)

### 1) iOS entrypoint drift (Roadmap vs app code)

- **Command**

```bash
git show origin/main:docs/roadmap/IOS_ROADMAP.md | rg -n "Entry point:|PR-652"
```

- **Output (raw)**

```text
13:- Entry point: `ios/PulsePlate/PulsePlateApp.swift` → `RootTabs()`
16:> Note: PR-652 proposes a first-run Welcome gate before `RootTabs`. Keep that change in PR-652 scope only.
33:- PR-652 (pending): iOS P0 Welcome gate (versioned key `has_seen_welcome_v1`) + RU/EN/ES welcome copy.
```

- **Repo truth (code)**
  - **Evidence command (stable):**

```bash
rg -n "WelcomeGateView\\(" ios/PulsePlate/PulsePlateApp.swift
rg -n "@AppStorage\\(\"has_seen_welcome_v1\"\\)|RootTabs\\(" ios/PulsePlate/Welcome/WelcomeGateView.swift
```

  - **Output (raw)**:

```text
7:            WelcomeGateView()
4:    @AppStorage("has_seen_welcome_v1") private var hasSeenWelcome: Bool = false
8:            RootTabs()
```

  - **Expected snippet:** `PulsePlateApp.swift` renders `WelcomeGateView()` and `WelcomeGateView` gates `RootTabs()` behind `has_seen_welcome_v1`.

### 2) Key handling drift (docs claimed placeholder fallback)

- **Command**

```bash
git show origin/main:docs/IOS_API_INTEGRATION.md | rg -n "test_pro_key"
```

- **Output (raw)**

```text
73:  - **WARNING**: contains a placeholder fallback (`"test_pro_key"`) in DEBUG.
```

- **Repo truth (code)**
  - **Evidence command (stable):**

```bash
rg -n "PRO_API_KEY|KeychainStore\\(|assertionFailure\\(\"Keychain error\"|return nil" ios/PulsePlate/Services/ProKeyProvider.swift -S
rg -n "struct KeychainStore|SecItemCopyMatching|SecItemAdd|SecItemUpdate|SecItemDelete" ios/PulsePlate/Services/KeychainStore.swift -S
rg -n "XCTSkip\\(\"PRO_API_KEY\"|ProKeyProvider\\.(value|set|clear)" ios/PulsePlateTests/Services/ProKeyProviderTests.swift -S
```

  - **Output (raw)**:

```text
5:    private static let store = KeychainStore(service: "com.pulseplate.pro-key")
14:        if let envKey = ProcessInfo.processInfo.environment["PRO_API_KEY"],
28:            return nil
8:struct KeychainStore: Sendable {
10:        try ProKeyProvider.clear()
11:        XCTAssertNil(ProKeyProvider.value())
```

  - **Expected snippet:** `ProKeyProvider` reads `PRO_API_KEY` in DEBUG, uses Keychain otherwise, and returns `nil` on missing key; tests cover nil + keychain value.

### 3) Nutrition endpoint story drift + security risk (legacy alias)

- **Repo truth (iOS client)**
  - **Evidence command (stable):**

```bash
rg -n "api/nutrition/\\$\\{|api/nutrition/|not yet implemented" ios/PulsePlate/Models/NutritionData.swift -n
```

  - **Output (raw)**:

```text
38:  // TODO: Backend endpoint /api/nutrition/{date} not yet implemented (GitHub issue)
57:      let path = "api/nutrition/\\(dateString)"
```

  - **Expected snippet:** iOS client currently builds path `api/nutrition/<date>` and contains a TODO claiming it is not implemented (docs must forbid this as SoT).

- **Repo truth (backend)**
  - **Evidence command (stable):**
    ```bash
    rg -n "/api/nutrition/\\{date_str\\}" legacy_app.py
    rg -n "Depends\\(api_key_header\\)|from app\\.routers\\.pro import get_daily_nutrition|await get_daily_nutrition" legacy_app.py -S
    rg -n "\"/nutrition/daily\"|dependencies=\\[Depends\\(require_pro_tier\\)\\]" app/routers/pro.py -n
    ```
  - **Output (raw)**:
    ```text
    875:@app.get("/api/nutrition/{date_str}", tags=["pro", "legacy"])
    884:    api_key: str = Depends(api_key_header),
    896:    response = await get_daily_nutrition(
    372:    dependencies=[Depends(require_pro_tier)],
    ```
  - **Expected snippet:** legacy alias exists on `legacy_app.py` and calls `get_daily_nutrition(...)` directly; canonical endpoint declares `Depends(require_pro_tier)` on the route.

- **Security concern (alias auth bypass risk)**
  - **Evidence command (stable):**

```bash
rg -n "api_key_header\\s*=\\s*APIKeyHeader\\(" app/routers/api_key.py
rg -n "async def require_pro_tier\\b|_validate_api_key_tier\\(" app/middleware/api_tiers.py -n
```

  - **Output (raw)**:

```text
4:api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
165:async def require_pro_tier(x_api_key: Optional[str] = Security(api_key_header)) -> str:
```

  - **Expected snippet:** `api_key_header` is header extraction only (`auto_error=False`), while `require_pro_tier` performs the actual 401/403 tier validation. Direct function calls bypass decorator-level dependencies unless the alias enforces them explicitly.

### 4) Placeholder token presence policy (app sources vs guard tests)

- **Command**

```bash
rg -n "test_pro_key" ios/PulsePlate -S
```

- **Output (raw)**: no matches (exit code 1).

Note: `test_pro_key` is expected to exist in **guard tests** (e.g., `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift`) as a forbidden-token sentinel. The policy is “no placeholder keys in app sources”, not “never mention the token in tests”.

## Changes applied (docs-only)

- `docs/roadmap/BACKLOG_LEDGER.md`
  - Mark PR-656 item checkbox as `[x]` (status already ✅ merged).
  - Mark PR-657 guard item as ✅ merged (repo truth).
  - Add P0 security backlog item: legacy nutrition alias must enforce `require_pro_tier`.
- `docs/roadmap/IOS_ROADMAP.md`
  - Update entrypoint to `PulsePlateApp.swift` → `WelcomeGateView()` → `RootTabs()`.
  - Replace outdated PR-652 “pending” statements with “PR-653 merged”.
  - Update P0 Next Actions to reflect PR-656/PR-657 done; point to P1 follow-ups in ledger.
- `docs/IOS_API_INTEGRATION.md`
  - Remove placeholder fallback claim; document `PRO_API_KEY` (debug) + Keychain (release-safe) repo truth.
  - Explicitly forbid legacy `GET /api/nutrition/{date}` as iOS source-of-truth; point to canonical `GET /api/v1/pro/nutrition/daily`.
- `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
  - Move placeholder-key removal + guard items to “done” and add App Store rule for key entry UX.
  - Add Plate slice note: canonical `/api/v1/pro/nutrition/daily`, legacy alias forbidden as SoT.

## Self-audit checklist

- [ ] `docs/roadmap/IOS_ROADMAP.md` entrypoint matches `PulsePlateApp.swift` → `WelcomeGateView` → `RootTabs`
- [ ] `docs/IOS_API_INTEGRATION.md` does not claim placeholder fallback and references `ProKeyProvider` + `KeychainStore`
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` PR-656 checkbox is `[x]` and PR-657 is marked ✅ merged
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` contains a P0 security item for `/api/nutrition/{date_str}` alias enforcement
- [ ] `rg -n "test_pro_key" ios/PulsePlate -S` has no matches (token only appears in tests/guards)
- [ ] `docs/IOS_API_INTEGRATION.md` forbids legacy `/api/nutrition/{date}` as iOS SoT and points to canonical `/api/v1/pro/nutrition/daily`

## Verification

```bash
pre-commit run --all-files
make lint
```

## Acceptance criteria

- `IOS_ROADMAP.md` no longer claims direct entry to `RootTabs()`; it reflects `WelcomeGateView`.
- `IOS_API_INTEGRATION.md` no longer mentions placeholder fallback; it documents `PRO_API_KEY` (debug) + Keychain (release-safe).
- `BACKLOG_LEDGER.md`:
  - PR-656 item is closed consistently (`[x]` + ✅ merged status),
  - PR-657 item is ✅ merged,
  - P1 repo-truth gaps exist (Expose BMI / Plate align / WeeklyPlanReader mount),
  - P0 security item exists for `/api/nutrition/{date_str}` alias enforcement.
- Audit doc includes evidence + self-audit checklist.
