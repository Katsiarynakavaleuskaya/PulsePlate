# Design Runtime System Web+iOS — Figma Runtime Canon Sync Closeout

**Date:** 2026-04-25 (`America/New_York`)
**Branch:** `docs/design-runtime-figma-sync-closeout`
**Lane:** design runtime system web+iOS
**Type:** docs-only governance closeout
**Figma file:** `PulsePlate_v3_Canonical_Foundations_Welcome_Gate`
**Figma file key:** `2JDwOByQIbcPgp93FDzHii`

## Summary

This document records the repo-grounded Figma synchronization pass completed for
the runtime product-canon and presentation layers.

The pass updated Figma as a design-intent / governance surface only. It does not
change runtime code, public contracts, OpenAPI, entitlement logic, billing,
tokens, generated mirrors, Storybook, or iOS runtime.

Repo code, docs, tests, and generated runtime artifacts remain the source of
truth. Figma remains a secondary design-intent lane.

## Source-of-truth references

- `docs/orchestration/DESIGN_RUNTIME_SYSTEM_WEB_IOS_PR_SERIES_RUNBOOK.md`
- `docs/design/UI_COMPONENT_VOCABULARY.md`
- `docs/design/TOKENS_SOT.md`
- `docs/design/TOKEN_PIPELINE_GOVERNANCE.md`
- `docs/runbooks/DESIGN_TOOLING_OPERATING_MODEL.md`
- `frontend/src/config/routes.ts`
- `ios/PulsePlate/Views/RootTabs.swift`
- `frontend/src/pages/Profile.tsx`
- `ios/PulsePlate/Views/ProfileView.swift`
- `frontend/src/pages/Pro/ProPaywallPage.tsx`
- `frontend/src/components/Paywall/BeforeAfter.tsx`
- `frontend/src/lib/paywallPurchase.ts`
- `frontend/src/pages/Onboarding/EnterKey.tsx`
- `ios/PulsePlate/Screens/PaywallScreen.swift`
- `ios/PulsePlate/Services/SubscriptionManager.swift`
- `ios/PulsePlate/Routing/PaywallRouter.swift`
- `ios/PulsePlate/Services/ProKeyProvider.swift`
- `app/routers/recipes.py`
- `app/routers/vip_shoplist.py`

## Figma pages updated

### 25_Profile_Settings_Product_Canon

**Node:** `219:2`
**Classification:** `DIVERGENT`

Decision:

- Web Profile is a status + handoff surface.
- iOS Profile is an in-place profile editing surface.
- Web and iOS Profile / Settings must not be presented as equivalent until code
  creates equivalent runtime behavior.

Confirmed Web runtime:

- `/profile` route is inside the tab shell.
- Profile reads API connection state from auth.
- Profile links to API-key setup and nutrition setup.
- Profile includes About and Legal cards.

Confirmed iOS runtime:

- `ProfileView()` is a `RootTabs` destination.
- `ProfileView` edits PRO profile values in place through `AppStorage`.
- Legal and language sections exist in `ProfileView`.
- `SettingsView` and `LanguagePickerView` are not promoted to runtime canon.

### 26_Paywall_Account_Support_Product_Canon

**Node:** `245:2`
**Classification:** `DIVERGENT`

Decision:

- Web paywall is informational and fails closed for checkout.
- Web account support is the API-key entry surface.
- iOS owns StoreKit purchase, restore, activation, and entitlement refresh.
- Web and iOS Paywall / Account Support must not be presented as equivalent.

Confirmed Web runtime:

- `ProPaywallPage` passes source / trigger context into `BeforeAfter`.
- `BeforeAfter` renders modal paywall behavior and analytics exposure events.
- `purchasePremium` logs failure and throws web-checkout-unavailable.
- `EnterKey` is the active API-key support surface.

Confirmed iOS runtime:

- `PaywallScreen` renders plans, restore, retry, entitlement, and error states.
- `SubscriptionManager` owns product loading, purchase, restore, receipt
  verification, activation, and entitlement refresh.
- `PaywallRouter` is presentation-only.
- `ProKeyProvider` uses Keychain as the runtime secret source.

### 27_Runtime_Surface_Register

**Node:** `256:2`
**Type:** register / governance index

Changes recorded:

- Added GitHub-verified runtime inventory for Web routes.
- Added GitHub-verified runtime inventory for iOS tabs.
- Updated `25_Profile_Settings_Product_Canon` from `PRODUCT TRUTH` to
  `DIVERGENT`.
- Kept `26_Paywall_Account_Support_Product_Canon` as `DIVERGENT`.

Decision:

- Register is an index only.
- It must not rewrite product-canon pages.
- Runtime classification follows repo code.

### 28_Runtime_Presentation_Board

**Node:** `263:2`
**Type:** presentation board

Changes recorded:

- Updated Profile / Settings card classification to `DIVERGENT`.
- Added register-sync note.
- Presentation board now follows `27_Runtime_Surface_Register`.

Decision:

- Presentation board is not a new source of truth.
- It displays normalized runtime surfaces only.

### 29_Runtime_Visual_Companions

**Node:** `298:2`
**Type:** runtime visual companion board

Changes recorded:

- Improved page title / subtitle readability.
- Improved companion title hierarchy.
- Normalized companion containers to the PulsePlate dark navy style.
- Added code-verification note for Recipes and Shoplist.

Confirmed runtime anchors:

- Recipes runtime is grounded in `app/routers/recipes.py`.
- VIP Shoplist runtime is grounded in `app/routers/vip_shoplist.py`.

Decision:

- Recipes and Shoplist visual companions are product-specific visual companions.
- They do not automatically create new governed primitives.

### 01_Components alignment

**Node:** `6:3`
**Type:** component governance board

Changes recorded:

- Added `Runtime Companion Alignment Audit - Current Cycle`.

Decision:

- No new component extraction pass opens from this Figma cycle.
- Recipes and Shoplist map to existing runtime component families.
- Governed gaps remain unchanged.

Existing governed gaps remain:

- `select`
- `textarea`
- `checkbox`
- `radio-group`
- `alert`
- `dropdown-menu`
- `tabs`
- `tooltip`
- `stepper/progress-indicator`

## Explicit non-goals

This closeout does not:

- create new runtime screens;
- change frontend route behavior;
- change iOS navigation;
- alter billing or entitlement truth;
- alter OpenAPI;
- change tokens or generated mirrors;
- promote Figma-only elements into code;
- mark visual companions as product runtime;
- mark Recipes or Shoplist as new generic primitives.

## Agent role order

For this docs-only closeout PR:

1. `agent-coordinator`
2. `creative-designer`
3. `frontend-engineer` advisory only
4. `cursor-specialist-agent` advisory only
5. `architecture-specialist`
6. mandatory post-open `qa-engineer-agent -> bug-hunter`

## Validation

Required local checks:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
```

Docs-only diff check:

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\\.md$|README\\.md$|AGENTS\\.md$|RUNBOOK_AGENT\\.md$|DEPLOYMENT\\.md$"
```

Expected output: empty.

`make verify` is optional for this docs-only closeout unless repo policy or CI
requires it. Do not claim merge readiness without current-head CI and
`check_merge_ready.py`.

## DoD

* Closeout document exists in repo.
* Figma page decisions are recorded with node IDs.
* `25` and `26` are recorded as `DIVERGENT`.
* `27` is recorded as the classification source for the presentation board.
* Presentation-only: `28` recorded.
* Visual companions: `29` recorded.
* `01_Components` notes: no new extraction pass opens this cycle.
* No runtime code changed.
* No token or generated mirror changed.
* Review mapping artifact exists after PR number assignment.

## Deferred / follow-ups

No new follow-up is created by this closeout.

Existing governed follow-ups remain under the design runtime system train:

* missing governed primitives;
* accessibility / motion / state contract;
* export lock and manifest hardening;
* Storybook parity expansion.
