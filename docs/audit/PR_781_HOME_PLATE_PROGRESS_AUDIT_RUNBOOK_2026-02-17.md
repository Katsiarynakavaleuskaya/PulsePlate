# PR_781 Home+Plate+Progress Audit + Runbook (2026-02-17)

## 1. Scope and non-goals

### Scope

- Slice: `Home + Plate + Progress` for iOS first, then web parity.
- Artifact contract for PR1: one combined audit+runbook document.
- Figma stage in this stream: blueprint definition + execution track
  (seat unblocked).
- Delivery order: `PR1 docs` -> `PR2 iOS` -> `PR3 web`.

### Non-goals (PR1)

- No runtime backend API/contract changes.
- No rate-limit/quota/policy rewrites.
- No desktop RPA/GUI automation.
- No merge-readiness claim from docs-only work.

## 2. Evidence baseline (SoT anchors)

### Anchor maintenance protocol

- `file:line` anchors are evidence snapshots at the audit date.
- When referenced files change in follow-up PRs, refresh affected
  anchors in this audit in the same PR.
- Minimum refresh check:
  - `rg -n "HomeView|ProgressViewPP|PlateViewPP|weekly-plan|shopping-list" \
    ios/PulsePlate frontend/src app/routers`
  - confirm changed symbols still map to the listed `file:line` anchors.
- If a symbol moves significantly, update this audit and add a short
  note in PR body under `Deferred / Follow-ups`.

### Web baseline

- Home placeholder shell: `frontend/src/pages/Home.tsx:1`
- Profile placeholder shell: `frontend/src/pages/Profile.tsx:1`
- Plate entry and premium gate shell: `frontend/src/pages/Plate.tsx:5`
- Route registration for Home/Profile/Plate/Progress: `frontend/src/config/routes.ts:23`
- Web style tokens (CSS): `frontend/src/styles/tokens.css:15`
- Web style tokens (TS): `frontend/src/styles/tokens.ts:15`
- Tailwind semantic mapping: `frontend/tailwind.config.ts:13`

### iOS baseline

- Home placeholder shell: `ios/PulsePlate/Views/HomeView.swift:3`
- Progress placeholder shell: `ios/PulsePlate/Views/ProgressView.swift:3`
- Plate screen and service-driven states: `ios/PulsePlate/Views/PlateView.swift:33`
- Root tab composition: `ios/PulsePlate/Views/RootTabs.swift:10`
- Debug-only discoverability for weekly/shopping: `ios/PulsePlate/Views/DebugToolsScreen.swift:21`
- iOS color bridge extension: `ios/PulsePlate/Extensions/Color+Assets.swift:4`

### Backend contract baseline (no contract change in this stream)

- Weekly meal endpoint: `app/routers/pro.py:245`
- Daily plate endpoint: `app/routers/pro.py:369`
- Nutrition targets/plate contracts router: `app/routers/pro_nutrition_contracts.py:26`
- Shopping list endpoint: `app/routers/shopping_list_pro.py:18`
- BMI calculate endpoint: `app/routers/bmi.py:198`

## 3. Visual inventory (iOS + web)

### iOS visual inventory

- Screens in slice:
  - Home: hero/status/quick-actions shell.
  - Plate: segmented plate + progress ring + issue handling + CTAs.
  - Progress: summary KPIs + trend/chart surfaces.
- Layers:
  - Navy background layer.
  - Glass card surfaces.
  - CTA layer (primary/secondary).
  - State overlays (loading/error/empty).
- Buttons/entries:
  - Primary CTA to setup/profile when required data is missing.
  - Navigation entries for weekly plan and shopping list (feature-gated).
- Transitions:
  - Existing spring/fade/slide usage in plate components remains canonical.
- Logos/mascot:
  - FitChef mascot bubble remains the canonical mascot block.

### Web visual inventory

- Screens in slice:
  - Home dashboard shell with status + route actions.
  - Plate page with premium gate framing + canonical route links.
  - Progress page with chart area and token-aligned cards.
  - Profile as non-placeholder production shell.
- Layers:
  - App background `--pp-navy` + semantic text and muted tokens.
  - Card layer via existing glass/card patterns.
  - Action layer with route buttons/links.
- Buttons/transitions:
  - Primary route CTAs (`/setup`, `/plate`, `/progress`, `/pro`).
  - Hover/focus states using semantic tokens only.
- Brand blocks:
  - FitChef mention/mascot context should stay consistent with iOS copy tone.

## 4. Backend ↔ frontend ↔ iOS attachment matrix

- BMI calculate:
  - Backend SoT: `app/routers/bmi.py:198`
  - Web attachment: BMI route (`/bmi`) and existing BMI pages
  - iOS attachment: `ios/PulsePlate/Services/BMIService.swift:31`
  - Notes: Keep FREE flow contract intact.
- Plate daily nutrition:
  - Backend SoT: `app/routers/pro.py:369`
  - Web attachment: Plate/Setup adapters and Premium flow
  - iOS attachment:
    `ios/PulsePlate/Services/ProDailyNutritionService.swift:38`
  - Notes: Canonical path `/api/v1/pro/nutrition/daily`.
- Weekly plan:
  - Backend SoT: `app/routers/pro.py:245`
  - Web attachment: `frontend/src/api/premium/weekly-plan.ts:15`
  - iOS attachment: `ios/PulsePlate/Services/WeeklyPlanService.swift:8`
  - Notes: No endpoint migration in this stream.
- Shopping list:
  - Backend SoT: `app/routers/shopping_list_pro.py:18`
  - Web attachment: Existing web premium flow where used
  - iOS attachment: `ios/PulsePlate/Services/ShoppingListService.swift:8`
  - Notes: Surface discoverability moves to production entry points.
- Nutrition targets/plate contracts:
  - Backend SoT: `app/routers/pro_nutrition_contracts.py:26`
  - Web attachment:
    `frontend/src/api/premium/targets.ts:9`,
    `frontend/src/api/premium/plate.ts:12`
  - iOS attachment: iOS plate profile + daily contract path
  - Notes: Keep thin adapters only.
- Legacy BMR alias:
  - Backend SoT: backend alias preserved
  - Web attachment: `frontend/src/api/premium/bmr.ts:4`
  - iOS attachment: N/A (iOS uses dedicated services)
  - Notes: Migration only in separate audited PR.

## 5. Gap matrix (P0/P1/P2)

- P0, Home/Profile placeholders on web:
  - Owner: Frontend
  - DoD: production cards/states, token-only styling, tests green
  - Target PR: PR3
- P0, Home/Progress placeholders on iOS:
  - Owner: iOS
  - DoD: real stateful screens with loading/empty/error/data surfaces
  - Target PR: PR2
- P1, Weekly/Shopping discoverability limited to debug path on iOS:
  - Owner: iOS
  - DoD: production entry points behind existing feature flags
  - Target PR: PR2
- P1, Progress visual token drift on web charts/cards:
  - Owner: Frontend
  - DoD: replace ad-hoc color values with semantic tokens
  - Target PR: PR3
- P2, Figma slice structure absent in current Make file:
  - Owner: Design + FE + iOS
  - DoD: page/component blueprint defined; execution in progress
  - Target PR: PR1/Follow-up
- P2, Browser E2E evidence not consistently attached per flow:
  - Owner: Dev Operator
  - DoD: runbook + deterministic evidence contract for E2E-01..04
  - Target PR: PR3 + Step3

## 6. Figma structure spec (Home+Plate+Progress slice)

### Preconditions

- Current Make file (`MrztJU3CQtxhADBbtAsWJ6`) treated as blank scaffold.
- MCP seat is now `Full` (Pro plan); direct design edits are available.

### Pages

- `00_Foundation_Tokens`
- `01_Components`
- `10_iOS_Home`
- `11_iOS_Plate`
- `12_iOS_Progress`
- `20_Web_Parity`

### Component set (`01_Components`)

- Top bar
- Tab bar
- Glass card
- KPI card
- Progress ring
- Segment chip
- CTA button states
- Empty/error/loading state blocks
- Mascot block
- Section header

### Token mapping rules

- Web SoT: `frontend/src/styles/tokens.css`,
  `frontend/src/styles/tokens.ts`,
  `frontend/tailwind.config.ts`.
- iOS SoT: color assets in
  `ios/PulsePlate/Assets.xcassets/*.colorset` and runtime bridge in
  `ios/PulsePlate/Extensions/Color+Assets.swift:4`.
- Naming convention: `PP/<Platform>/<Screen>/<Component>/<State>`.

## 7. Execution checklist (PR2 + PR3)

### PR2 (iOS-first)

1. Replace `HomeView` placeholder with stateful dashboard shell.
2. Replace `ProgressViewPP` placeholder with chart/KPI stateful shell.
3. Keep `PlateViewPP` API flow canonical; align style blocks to token SoT.
4. Lift weekly/shopping discoverability from debug-only path into
   production Home entry points behind existing flags.
5. Preserve thin-client invariants (no business-logic duplication).
6. Run iOS and repo gates before merge-ready statement.

### PR3 (web parity)

1. Replace `Home/Profile/Plate` placeholder shells with production
   card/state surfaces.
2. Keep API calls through existing adapters only
   (`frontend/src/api/client.ts` wrappers).
3. Keep canonical premium endpoints unchanged.
4. Align Progress visuals with semantic tokens, remove ad-hoc color drift.
5. Run frontend tests/build + repo guards + verify gates before
   merge-ready statement.

### Step 3 extension (post-stabilization)

- Run controlled Playwright operator scenarios from
  `tools/codex_skills/pulseplate-playwright-e2e/SKILL.md` and
  `docs/dev/PLAYWRIGHT_E2E_RUNBOOK.md`.
- Scenarios: `E2E-01` Home, `E2E-02` BMI, `E2E-03` Setup, `E2E-04` Pro.
- Deterministic dependency install: `cd frontend && npm ci`.

## 8. Verification commands and acceptance criteria

### PR1 (docs-only)

```bash
python scripts/ci/check_docs_phase1_gates.py --files \
  docs/audit/PR_781_HOME_PLATE_PROGRESS_AUDIT_RUNBOOK_2026-02-17.md
make lint
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
```

Acceptance criteria:

- Docs gate passes.
- At least one valid `file:line` evidence anchor exists
  (this doc includes explicit anchors).
- No runtime/API change introduced in PR1.

### PR2 (iOS)

```bash
make ios-test
make lint
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make verify
```

Acceptance criteria:

- Home/Progress are not placeholders.
- Plate remains canonical on `/api/v1/pro/nutrition/daily` flow.
- Weekly/Shopping production discoverability exists behind existing
  flags.

### PR3 (web)

```bash
cd frontend && npm test
cd frontend && npm run build
make lint
pytest -q tests/test_repo_policy_guards.py
pre-commit run --all-files
make verify
```

Acceptance criteria:

- Home/Profile/Plate are not skeleton placeholders.
- Progress style uses semantic tokens
  (no ad-hoc drift in updated surfaces).
- Thin-client policy remains green.

## Security notes

- Terminal operator remains allowlist-first and browser-only for Step 3.
- No secret dumping and no `.env` echoing in logs.
- No merge-readiness wording without local `make verify` evidence.

## Marketing & GTM notes

- Home+Plate+Progress creates stable demo surfaces for App Store and
  Product Hunt content.
- Web+iOS visual parity reduces brand drift and review friction for
  launch materials.
- Playwright Step 3 evidence gives deterministic walkthrough artifacts
  for stakeholders.

## Decision log

- 2026-02-17: Slice fixed to Home+Plate+Progress.
- 2026-02-17: Artifact format fixed to one combined audit+runbook.
- 2026-02-17: Figma execution deferred until Edit seat access.
- 2026-02-17: Delivery order fixed: PR1 docs -> PR2 iOS -> PR3 web.
- 2026-02-17: Figma access unblocked (`seat=Full`); execution moved to active follow-up.

## Assumptions and defaults

- Figma seat is `Full`; blueprint execution is allowed in the current workspace.
- Figma Make file is treated as blank scaffold baseline for this slice.
- No runtime backend contract changes are included in this stream.
- Deferred follow-ups must be tracked in
  `docs/roadmap/BACKLOG_LEDGER.md` with Owner, DoD, and Target PR.
