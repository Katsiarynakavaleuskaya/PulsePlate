# iOS Docs ↔ BACKLOG_LEDGER Alignment Audit (2026-02-06)

**Date:** 6 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**Scope:** Docs-only (repo-truth alignment)

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
  - `ios/PulsePlate/PulsePlateApp.swift:7` → `WelcomeGateView()`
  - `ios/PulsePlate/Welcome/WelcomeGateView.swift:7-11` → `RootTabs()` gated by `has_seen_welcome_v1`

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
  - `ios/PulsePlate/Services/ProKeyProvider.swift:12-28` (DEBUG reads `PRO_API_KEY`, release-safe Keychain, no placeholder fallbacks)
  - `ios/PulsePlate/Services/KeychainStore.swift:20-100` (Keychain storage)
  - `ios/PulsePlateTests/Services/ProKeyProviderTests.swift:6-22` (missing-key returns nil; keychain value when set)

### 3) Nutrition endpoint story drift + security risk (legacy alias)

- **Repo truth (iOS client)**
  - `ios/PulsePlate/Models/NutritionData.swift:38-58` calls legacy `api/nutrition/<date>` and claims endpoint is “not yet implemented”.

- **Repo truth (backend)**
  - `legacy_app.py:875-905` defines legacy alias `GET /api/nutrition/{date_str}` and directly calls `app/routers/pro.py:get_daily_nutrition(...)`.
  - `app/routers/pro.py:400+` defines canonical `GET /api/v1/pro/nutrition/daily` (PRO, requires profile query params).

- **Security concern (alias auth bypass risk)**
  - `legacy_app.py:884` uses `Depends(api_key_header)` which extracts header but does **not** enforce tier.
  - `app/middleware/api_tiers.py:165-202` shows the actual tier guard is `require_pro_tier(...)`.
  - Because the alias calls `get_daily_nutrition` directly, the PRO-tier dependency is not executed for the alias path unless enforced explicitly.

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
- `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
  - Move placeholder-key removal + guard items to “done” and add App Store rule for key entry UX.

## Self-audit checklist

- [ ] `docs/roadmap/IOS_ROADMAP.md` entrypoint matches `PulsePlateApp.swift` → `WelcomeGateView` → `RootTabs`
- [ ] `docs/IOS_API_INTEGRATION.md` does not claim placeholder fallback and references `ProKeyProvider` + `KeychainStore`
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` PR-656 checkbox is `[x]` and PR-657 is marked ✅ merged
- [ ] `docs/roadmap/BACKLOG_LEDGER.md` contains a P0 security item for `/api/nutrition/{date_str}` alias enforcement
- [ ] `rg -n "test_pro_key" ios/PulsePlate -S` has no matches (token only appears in tests/guards)

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
