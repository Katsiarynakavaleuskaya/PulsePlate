# iOS Docs Drift Audit — PR-669

**Date**: 7 February 2026
**PR**: 669
**Branch**: `docs/ios-api-integration-sot-pr-670`
**Type**: docs-only (no runtime/iOS/backend code changes)
**Owner**: @katsiaryna_kavaleuskaya

---

## Problem statement

After PR-667 (Plate PRO canonical migration) and PR-668 (ledger/roadmap evidence hygiene),
two BACKLOG_LEDGER P1 items remain open:

1. `Docs: Canonicalize iOS API integration guide to current Networking SoT` — the guide
   (`docs/IOS_API_INTEGRATION.md`) omits `ProfileProvider`, `ProDailyNutritionService`,
   and lacks `file:line` evidence for existing entries.
2. `Docs: Refresh iOS roadmap to AS-IS / NEXT ACTIONS` — the roadmap
   (`docs/roadmap/IOS_ROADMAP.md`) still lists completed P0 items under "P0 Next Actions"
   and does not reflect that all P0s are shipped.

Both items block iOS P1 features per project process:
> "PR-D (Frontend Audit) is forbidden until backend stable + docs aligned" (root `AGENTS.md`).

---

## Evidence (current repo truth — before this PR)

### iOS Networking SoT (code)

| Component | File | Lines | What it does |
|-----------|------|-------|-------------|
| Transport protocol | `ios/PulsePlate/Networking/APIClient.swift` | `4`, `57` | `APIClientProtocol` + `APIClient` class |
| PRO key | `ios/PulsePlate/Services/ProKeyProvider.swift` | `3` | `enum ProKeyProvider` (Keychain + DEBUG env) |
| Profile params protocol | `ios/PulsePlate/Services/ProfileProvider.swift` | `42-49` | `ProfileProviding` (language + nutrition profile) |
| Profile params impl | `ios/PulsePlate/Services/ProfileProvider.swift` | `52-115` | `DefaultProfileProvider` (reads UserDefaults) |
| PRO daily nutrition service | `ios/PulsePlate/Services/ProDailyNutritionService.swift` | `80-115` | Builds `GET /api/v1/pro/nutrition/daily` + query + header |
| BMI service (FREE) | `ios/PulsePlate/Services/BMIService.swift` | `19-39` | Calls `POST /api/v1/bmi/calculate` |
| Tests (PRO daily) | `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift` | `6-65` | Deterministic URL + header assertion |
| Thin-client guards | `ios/PulsePlateTests/Guards/ThinClientGuardsTests.swift` | — | No BMI thresholds in app sources |

### Docs drift (what was stale)

| Document | Drift | Specifics |
|----------|-------|-----------|
| `docs/IOS_API_INTEGRATION.md` | Missing SoT entries | No `ProfileProvider`, no `ProDailyNutritionService` as example, no `file:line` evidence |
| `docs/roadmap/IOS_ROADMAP.md` | Stale P0 section | Lists shipped P0 items as "Next Actions"; does not reflect all P0 = done |

### What was already accurate

- `docs/IOS_API_INTEGRATION.md`: Transport, Base URL, Rules, Key handling, Deprecated endpoints — all correct.
- `docs/roadmap/IOS_ROADMAP.md`: AS-IS (entry + navigation), localization, "What changed recently" — all correct.

---

## Plan (this docs-only PR)

### A) `docs/IOS_API_INTEGRATION.md`

1. Add `PRO key provider` and `Profile query params` to "Current SoT" with `file:line`.
2. Add `ProDailyNutritionService` as example in "How to add a new endpoint" recipe.
3. Add `ProDailyNutritionServiceTests` to test examples with `file:line`.
4. Bump `Last Updated` to 7 February 2026.

### B) `docs/roadmap/IOS_ROADMAP.md`

1. Rename "P0 Next Actions" to "Completed P0 actions" (all shipped).
2. Add "P1 Next Actions" section with remaining items + `file:line` evidence for code anchors.
3. Add `ProKeyProvider` and `ProfileProvider` to Networking SoT section with `file:line`.

### C) This audit document

Evidence-driven record of what was stale and what was fixed.

---

### Non-goals

- iOS/backend code unchanged.
- No contract changes or OpenAPI regeneration.
- Policies remain unchanged (AGENTS/ios/AGENTS).
- BACKLOG_LEDGER checkbox update for these items belongs to a separate follow-up
  (to avoid scope creep; the items reference this PR as evidence).

---

### Docs-only enforcement

```bash
git diff --name-only origin/main...HEAD | rg -v "\.md$"

# Exit code: 1
```

**Verification result**: Only `.md` files modified in this PR.
