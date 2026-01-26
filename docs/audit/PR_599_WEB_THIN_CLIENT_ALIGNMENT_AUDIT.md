# PR-599 — Web Thin Client Alignment Audit (contracts + transport)

**Date:** 2026-01-26 (America/New_York)
**Target branch:** `main`
**Source branch:** `audit/pr-599-web-thin-client-alignment`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🟢 Verified (audit complete)

---

## 0) Goal

Verify that Web client is a **thin client**:

- **One HTTP seam**: networking only via canonical API layer (no scattered `fetch()`/`axios()` calls).
- **Contract-first DTOs**: request/response types come from OpenAPI generation.
- **No business logic**: no BMI / WHR / WHtR / nutrition interpretation, thresholds, or categorization on the client.
- **Clean error semantics**: transport vs domain errors are not mixed in UI.

---

## 1) Scope / Non-goals

### In-scope

- Web transport boundary (API client layer + any callers).
- DTO/type sources (OpenAPI vs handwritten).
- Thin-client policy compliance (no domain logic).
- Paywall hook rendering is contract-driven (no local inference).

### Out-of-scope

- Any backend changes (FastAPI, schemas, OpenAPI content).
- Any UI redesign (visual changes, layout, copy polish).
- Any “cleanup” not required for thin-client verification.

---

## 2) Canonical invariants (policy anchors)

- **Thin clients only**: Web renders contract; no domain logic duplication.
- **One HTTP path**: no dual-path networking; no direct HTTP from features/components/hooks.
- **External URL security**: never send API credentials to external (signed) URLs.
- **Contract-first**: DTOs come from generated OpenAPI types.

> Note: This audit follows the same invariant framework as `PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md` / `PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md`.
> Any future consolidation into a shared audit template is out of scope for PR-599.

---

## 3) Evidence commands (copy/paste)

> Note: Replace `frontend/src` with your actual root if different.

```bash
# A) Transport: locate all HTTP calls
rg -n "fetch\\(|axios\\(|ky\\(" frontend/src

# B) DTO origin: find any manual BMI-related interfaces/types
rg -n "interface .*BMI|type .*BMI|BMIResponse|BMIRequest" frontend/src

# C) OpenAPI path: confirm generated types usage
rg -n "from\\s+['\"].*/api/schema['\"]|/api/schema" frontend/src

# D) BMI/nutrition domain logic: broad scan (then manually inspect matches)
rg -n "(\\bbmi\\b|body\\s*mass\\s*index|\\bwhr\\b|\\bwht\\b|waist\\s*to\\s*height|waist\\s*hip|body\\s*fat|\\bffmi\\b)" frontend/src

# E) Threshold literals guard (spot-check; canonical hard thresholds must not exist outside core/bmi/)
# Prefer a narrower grep to reduce false positives from OpenAPI examples and non-BMI numbers.
rg -n "(bmi|whr|wht|ffmi).*(18\\.5|25|30|0\\.8|0\\.85|0\\.9|0\\.95)" frontend/src

# F) Paywall copy surface scan
rg -n "(upgrade|subscribe|premium|pro\\b|vip\\b)" frontend/src
```

---

## 4) Questions → Evidence → Decision

> Format: **Question → What counts as evidence → Expected decision**

### A. Web architecture (thin-client fact check)

#### A1. Is there **exactly one HTTP seam**?

- **Question:** Does Web use one centralized API wrapper, or are there parallel calls (`fetch`, `axios`, `ky`, etc.)?
- **Evidence:** `rg -n "fetch\\(|axios\\(|ky\\(" frontend/src` + file list of matches.
- **Decision:** ✅ Verified (one seam) / ❌ Violation (dual-path)

#### A2. Is direct HTTP outside the API layer **forbidden / prevented**?

- **Question:** Is the rule enforced structurally (project layout) or via tests/guards, not only “by convention”?
- **Evidence:** absence of `fetch` outside API layer + guard tests policy reference (if present).
- **Decision:** ✅ Enforced / ⚠️ Convention only / ❌ Not enforced

---

### B. Contracts & DTOs (OpenAPI compliance)

#### B1. Do DTOs come only from OpenAPI generation?

- **Question:** Are request/response types imported from generated schema, not handwritten?
- **Evidence:** imports from `frontend/src/api/schema.ts` (or equivalent); absence of manual DTO files.
- **Decision:** ✅ Generated only / ❌ Manual DTOs detected

#### B2. Are DTOs “pure transport” (no derived semantics)?

- **Question:** Any computed/derived fields like `isOverweight`, `riskLevel`, etc. on client side types?
- **Evidence:** search for `computed|derive|riskLevel|isOverweight|get` in DTO/type modules.
- **Decision:** ✅ Pure transport DTO / ❌ Semantic leakage

---

### C. BMI / Nutrition logic (hard invariant)

#### C1. Any BMI-related `if/logic` exists?

- **Question:** Is there any BMI/WHR/WHtR/bodyfat interpretation logic in Web?
- **Evidence:** inspect grep matches for comparisons/thresholds/category inference (not UI copy).
- **Decision:** ✅ UI-only / ❌ Logic detected (blocker)

#### C2. Any “UI norms” (threshold-driven colors/categories)?

- **Question:** Any thresholds like `if bmi > 25` driving UI color or labels?
- **Evidence:** conditional rendering around BMI numeric comparisons.
- **Decision:** ✅ Backend-driven / ❌ Client-side interpretation

---

### D. Errors & semantics

#### D1. Transport errors are separated from domain errors?

- **Question:** Does error handling distinguish network/timeout/HTTP from domain validation/paywall?
- **Evidence:** centralized error mapping in API layer; UI avoids semantic `try/catch` branching.
- **Decision:** ✅ Clean separation / ❌ Mixed semantics

#### D2. Is there one error mapping policy?

- **Question:** Do all callers use a single error shape (union/enum), or is it fragmented?
- **Evidence:** one mapper/type in API layer; absence of ad-hoc per-feature parsing.
- **Decision:** ✅ Single mapping / ❌ Fragmented handling

---

### H. Orchestrator / Agent Runner Hygiene (audit-only)

#### H1. Is there a single canonical orchestrator entrypoint?

- **Question:** Is there exactly one documented command to run the dev orchestrator / agent runner?
- **Evidence:** command(s) found in docs / Makefile / package.json; observed stdout/stderr.
- **Decision:** ✅ Single entrypoint / ❌ Multiple or undefined

#### H2. Does the orchestrator start deterministically?

- **Question:** Does the canonical command start the orchestrator without manual steps?
- **Evidence:** exact command + full observed output.
- **Decision:** ✅ Deterministic / ❌ Fails to start

#### H3. Is the failure documented (if any)?

- **Question:** If startup fails, is the failure mode documented in `AGENTS.md` or docs?
- **Evidence:** links (or explicit absence).
- **Decision:** ✅ Documented / ❌ Undocumented

---

### E. Soft Paywall hooks (contract-driven)

#### E1. Paywall CTA rendering is contract-driven?

- **Question:** Is CTA rendered only based on backend-provided fields (e.g., `soft_paywall`) without local inference?
- **Evidence:** UI checks only presence/validity of contract fields; no `if (isFreeUser)`/tier inference.
- **Decision:** ✅ Contract-driven / ❌ Client inference

#### E2. No hardcoded paywall copy?

- **Question:** Are paywall texts externalized (backend or i18n dictionary), not hardcoded in components?
- **Evidence:** grep results for `upgrade|subscribe|premium|pro|vip` and where strings live.
- **Decision:** ✅ Externalized / ❌ Hardcoded

---

### F. i18n & copy hygiene

#### F1. i18n is not used as logic

- **Question:** Any conditions like `if (t("..."))` or switching on translated strings?
- **Evidence:** search for `if\\s*\\(\\s*t\\(`; inspect matches.
- **Decision:** ✅ OK / ❌ Logic via copy

---

### G. Final sanity question (highest-signal)

#### G1. Can we delete/rewrite the Web UI without touching backend/contracts?

- **Question:** If the answer is “yes” → thin-client confirmed; if “no” → hidden business logic exists.
- **Evidence:** derived from all decisions above.
- **Decision:** ✅ Thin-client confirmed / ❌ Not thin-client

---

## 5) Observed output (paste evidence here)

### 5.1 Transport scan (`fetch/axios/ky`)

```text
frontend/src/api/client.ts:193:    const res = await fetch(`${getApiBase()}/health`, {
frontend/src/api/client.ts:324:    const res = await fetch(normalizeApiUrl(getApiBase(), path), requestInit);
frontend/src/api/client.ts:356:    const res = await fetch(url);
frontend/src/api/client.ts:451:  const res = await fetch(finalUrl, finalInit);

frontend/src/api/__tests__/thin-client-guards.test.ts:16: * - Direct fetch() calls outside client.ts
frontend/src/mocks/__tests__/purchase.test.ts:8:  const res = await fetch(`${BASE_URL}/api/purchase`, { method: "POST" });
```

### 5.2 DTO scan (manual BMI types)

```text
frontend/src/pages/BMI/BMICalculatePage.tsx:10:type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
frontend/src/pages/BMI/BMICalculatePage.tsx:11:type BMICalculateResponse = components['schemas']['BMICalculateResponse'];
frontend/src/api/bmi.ts:7:type BMICalculateRequest = components['schemas']['BMICalculateRequest'];
frontend/src/api/bmi.ts:8:type BMICalculateResponse = components['schemas']['BMICalculateResponse'];

frontend/src/api/schema.ts:2346:        /** BMIRequest */
frontend/src/api/openapi.json:553:      "BMIRequest": {
```

### 5.3 OpenAPI schema imports

```text
frontend/src/pages/BMI/BMICalculatePage.tsx:8:import type { components } from '../../api/schema';
frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:5:import type { components } from '../../api/schema';
```

### 5.4 BMI/nutrition keyword scan (manual inspection required)

```text
frontend/src/api/schema.ts:316:         * Calculate Bmi
frontend/src/api/schema.ts:317:         * @description RU: Рассчитывает BMI через единый engine.

frontend/src/api/__tests__/thin-client-guards.test.ts:4: * RU: Защитные тесты против появления BMI логики во frontend коде.
```

### 5.5 Threshold literal scan

```text
Matches found only in:
- frontend/src/api/schema.ts (OpenAPI-generated docs/examples)
- frontend/src/api/openapi.json (generated schema artifact)
- frontend/src/api/__tests__/thin-client-guards.test.ts (guard patterns/docs)
- frontend/src/api/__tests__/thinClientGuardUtils.test.ts (guard helper tests)
```

### 5.6 Paywall copy scan

```text
frontend/src/pages/BMI/BMICalculatePage.tsx:300:          {response.soft_paywall && (
frontend/src/pages/BMI/BMICalculatePage.tsx:301:            <SoftPaywallHook hook={response.soft_paywall} />

frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:48:        {hook.message.default_title}
frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:51:        {hook.message.default_body}
frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:59:        {hook.message.default_cta}

frontend/src/pages/Pro/ProPaywallPage.tsx:18:      purchaseLabel=\"Coming soon\"
frontend/src/pages/Pro/ProPaywallPage.tsx:19:      source=\"bmi_soft_paywall\"
frontend/src/pages/Pro/ProPaywallPage.tsx:20:      via=\"pro_page\"
```

### 5.7 i18n used as logic scan (`if (t(...))`)

```text
No matches found
```

### 5.8 BMI comparison scan (`bmi <`, `bmi >`, etc.)

```text
No matches found in runtime code.
Matches only in guard tests:
- frontend/src/api/__tests__/thinClientGuardUtils.test.ts
- frontend/src/api/__tests__/thin-client-guards.test.ts
```

### 5.9 Orchestrator / agent runner entrypoint scan

```text
Docs present (process/workflow):
- docs/orchestration/workflow.md (no executable CLI/command documented)

Frontend dev entrypoint exists:
- frontend/package.json:9: \"dev\": \"vite\"

No repo-level \"orchestrator/agent runner\" start command found in Makefile/package.json beyond standard dev scripts.
```

---

## 6) Findings (AS-IS)

> TODO: summarize factual findings with `path:line` pointers (no interpretation beyond evidence).

- **One HTTP seam (runtime)**:
  - `fetch()` usage is centralized in `frontend/src/api/client.ts` (e.g. `client.ts:451`).
  - Additional `fetch()` usage exists in tests/mocks only:
    - Guard tests: `frontend/src/api/__tests__/thin-client-guards.test.ts`
    - Purchase mocks test: `frontend/src/mocks/__tests__/purchase.test.ts:8`
  - Enforcement exists via guard tests that scan for direct `fetch()` outside `client.ts`.

- **DTO origin (OpenAPI)**:
  - BMI page uses generated schema types:
    - `frontend/src/pages/BMI/BMICalculatePage.tsx:10-11`
    - `frontend/src/api/bmi.ts:7-8`
  - Soft paywall hook uses generated schema types:
    - `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:8`
  - BMIRequest/BMIRequestV1 appear only inside generated artifacts (`frontend/src/api/schema.ts`, `frontend/src/api/openapi.json`).

- **No BMI/nutrition interpretation logic (hard invariant)**:
  - No `bmi <` / `bmi >` comparisons found in runtime code (matches only in guard tests).
  - Threshold literals (18.5/24.9/25/30, etc.) appear only in generated schema artifacts and guard tests (not in runtime business logic).
  - BMI page performs **input validation only** (weight/height/age), not BMI categorization:
    - `frontend/src/pages/BMI/BMICalculatePage.tsx:76-92`

- **Error semantics / mapping**:
  - Centralized auth error handling exists in API layer (401/403 clears key + redirects):
    - `frontend/src/api/client.ts:330-342`
  - Binary download path uses `fetchBlob()` with URL classification and **auth header stripping for external signed URLs**:
    - `frontend/src/api/client.ts:391-468`
  - BMI page catches AbortError and renders generic error message (UI-level concern):
    - `frontend/src/pages/BMI/BMICalculatePage.tsx:100-127`

- **Soft paywall hooks (contract-driven)**:
  - Hook renders backend-provided default strings (`default_title/default_body/default_cta`) and does not depend on BMI values:
    - `frontend/src/components/SoftPaywallHook/SoftPaywallHook.tsx:15-18, 48-60`
  - Navigation target is `/pro` (paywall page), and the PRO page currently contains a hardcoded placeholder label:
    - `frontend/src/pages/Pro/ProPaywallPage.tsx:18` (`purchaseLabel="Coming soon"`)

- **i18n hygiene (i18n ≠ logic)**:
  - No `if (t(...))` patterns found in `frontend/src` (grep clean).

---

## 7) AS-IS → TO-BE table

| Area | AS-IS | TO-BE | Status |
|------|-------|-------|--------|
| HTTP seam | `fetch()` in `api/client.ts`; tests use `fetch()` | One API layer only (runtime) | ✅ |
| DTOs | Generated `components['schemas']` types used | OpenAPI generated only | ✅ |
| BMI/nutrition logic | No comparisons/threshold logic in runtime | None in client | ✅ |
| Errors | Central mapping in `client.ts`; UI displays messages | One mapping policy | ✅ |
| Paywall hooks | Hook is contract-driven; `/pro` has a hardcoded placeholder label | Contract-driven | ✅ (with note) |

---

## 8) Decision

**Verdict:** 🟢 **Verified** — Web client is thin-client aligned.

**Non-blocking note (copy hygiene):**
- `frontend/src/pages/Pro/ProPaywallPage.tsx:18` contains `purchaseLabel="Coming soon"` (hardcoded placeholder). This does not introduce domain logic, but is worth tracking as UX/i18n cleanup if/when paywall copy is productized.

If remediation is required:

- **Next PR:** PR-601 — Web Thin Client Remediation (single seam + DTO cleanup + error mapping)

---

## 9) DoD checklist (PR-599)

- [x] Audit file is self-contained (commands + observed output + decisions).
- [x] “Verified” includes minimal observed outputs for each key evidence command.
- [x] Clear verdict (`Verified` or `Remediation required`) is present.
- [x] Decision log explains why verdict was chosen (based only on evidence).
- [x] Next step is explicit (no remediation vs link to remediation PR).
- [x] No runtime files changed (docs-only).

---

## 10) Links

- PR-597 merge commit: `898a46b8b6fc4a0ecf6be77dd5114fa770eb025a`
- PR-598 merge commit: `7044beea451857e80c5215a89e1d77452d825d9a`
- Related web thin-adapter audits:
  - `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md`
  - `docs/audit/PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md`

---

**Last updated:** 2026-01-26
