# iOS Docs ↔ BACKLOG_LEDGER Alignment Audit (2026-02-07)

**Date:** 7 February 2026
**Owner:** @katsiaryna_kavaleuskaya
**Scope:** Docs-only (repo-truth alignment after PR-667)
**Branch:** `docs/ios-docs-ledger-alignment-2026-02-07`

## Problem statement

After merging **PR-667** (iOS Plate → canonical `GET /api/v1/pro/nutrition/daily`) into `main`, the canonical docs set
(`BACKLOG_LEDGER.md`, iOS roadmaps) still describes Plate as a pending follow-up. This is now incorrect and creates
planning noise: readers may assume iOS is still blocked on the legacy alias or missing a profile/query story.

This audit captures **evidence (commands + raw output + exit code)** and defines a **docs-only PR plan** to restore
repo-truth alignment.

## Evidence (current repo truth)

### 1) Latest merge on `main` is PR-667

- **Command**

```bash
git log -1 --oneline
```

- **Output (raw)**

```text
a396d0ff PR-667: iOS Plate → canonical /api/v1/pro/nutrition/daily (#667)
```

- **Exit code:** 0

### 2) iOS uses canonical Plate endpoint in code + tests

- **Command**

```bash
rg -n "/api/v1/pro/nutrition/daily" ios/PulsePlate/Services/ProDailyNutritionService.swift
```

- **Output (raw)**

```text
7://     GET /api/v1/pro/nutrition/daily
9://     GET /api/v1/pro/nutrition/daily
38:        components.path = "/api/v1/pro/nutrition/daily"
53:        // "/api/v1/pro/nutrition/daily?..."
```

- **Exit code:** 0

- **Command**

```bash
rg -n "^\s*\"/api/v1/pro/nutrition/daily\?" ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift
```

- **Output (raw)**

```text
19:            "/api/v1/pro/nutrition/daily?date=2026-02-07&sex=female&age=30&height_cm=170&weight_kg=70&activity=moderate&goal=maintain&lang=ru"
64:            "/api/v1/pro/nutrition/daily?date=2026-02-07&sex=male&age=40&height_cm=180&weight_kg=85&activity=active&goal=gain&lang=en"
```

- **Exit code:** 0

## Evidence (docs drift)

### 3) BACKLOG_LEDGER still marks Plate alignment as not done

- **Command**

```bash
rg -n "iOS: Plate \(PRO\) align" docs/roadmap/BACKLOG_LEDGER.md
```

- **Output (raw)**

```text
471:- [ ] iOS: Plate (PRO) align to canonical backend `GET /api/v1/pro/nutrition/daily` + profile input
```

- **Exit code:** 0

### 4) IOS_ROADMAP still lists Plate alignment as “Next”

- **Command**

```bash
rg -n "Plate \(PRO\): align iOS" docs/roadmap/IOS_ROADMAP.md
```

- **Output (raw)**

```text
41:  - Plate (PRO): align iOS to canonical `GET /api/v1/pro/nutrition/daily` + profile input
```

- **Exit code:** 0

## Plan (this docs-only PR)

### Changes

- `docs/roadmap/BACKLOG_LEDGER.md`
  - Mark “iOS: Plate (PRO) align…” as ✅ done and link to PR-667 + iOS SoT files:
    - `ios/PulsePlate/Services/ProDailyNutritionService.swift`
    - `ios/PulsePlate/Views/ProfileView.swift`
    - `ios/PulsePlateTests/Services/ProDailyNutritionServiceTests.swift`
- `docs/roadmap/IOS_ROADMAP.md`
  - Move Plate alignment from “Next” to “What changed recently” (PR-667).
  - Keep only real remaining follow-ups under “Next”.
- `docs/roadmap/IOS_BACKEND_REALIZATION_ROADMAP.md`
  - Update Slice P2 (Plate PRO) status to shipped (PR-667) and point to the same SoT files.
- `docs/audit/IOS_DOCS_LEDGER_ALIGNMENT_AUDIT_2026-02-06.md`
  - Add a short “Update (2026-02-07)” note pointing to this audit (the 2026-02-06 “before” evidence is now stale).

### Non-goals

- No iOS/backend code changes.
- No contract changes / no OpenAPI generation.
- No policy changes (AGENTS/ios/AGENTS unchanged).

## Docs-only enforcement (required before push)

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

**Expected:** empty output (docs-only PR).
