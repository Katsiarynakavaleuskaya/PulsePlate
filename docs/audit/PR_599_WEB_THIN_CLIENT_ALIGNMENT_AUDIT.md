# PR-599 — Web Thin Client Alignment Audit (contracts + transport)

**Date:** 2026-01-26 (America/New_York)
**Target branch:** `main`
**Source branch:** `audit/pr-599-web-thin-client-alignment`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🟡 Draft (awaiting evidence collection)

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
rg -n "(18\\.5|24\\.9|\\b25\\b|\\b30\\b|\\b0\\.9\\b|\\b0\\.85\\b|\\b0\\.95\\b|\\b0\\.8\\b)" frontend/src

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

- **Question:** Does Web contain any BMI/WHR/WHtR/bodyfat interpretation logic?
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
TODO: paste `rg -n "fetch\(|axios\(|ky\(" frontend/src` output (or "No matches found" if clean)
```

### 5.2 DTO scan (manual BMI types)

```text
TODO: paste DTO grep output (or "No matches found")
```

### 5.3 OpenAPI schema imports

```text
TODO: paste schema import grep output (sample lines)
```

### 5.4 BMI/nutrition keyword scan (manual inspection required)

```text
TODO: paste grep output (sample lines); note which are UI copy vs logic
```

### 5.5 Threshold literal scan

```text
TODO: paste grep output (or "No matches found")
```

### 5.6 Paywall copy scan

```text
TODO: paste grep output (sample lines); classify as i18n keys vs hardcoded strings
```

---

## 6) Findings (AS-IS)

> TODO: summarize factual findings with `path:line` pointers (no interpretation beyond evidence).

- **One HTTP seam**: TODO
- **DTO origin (OpenAPI)**: TODO
- **No BMI logic**: TODO
- **Error mapping**: TODO
- **Paywall hooks**: TODO
- **i18n hygiene**: TODO

---

## 7) AS-IS → TO-BE table

| Area | AS-IS | TO-BE | Status |
|------|-------|-------|--------|
| HTTP seam | TODO | One API layer only | TODO |
| DTOs | TODO | OpenAPI generated only | TODO |
| BMI/nutrition logic | TODO | None in client | TODO |
| Errors | TODO | One mapping policy | TODO |
| Paywall hooks | TODO | Contract-driven | TODO |

---

## 8) Decision

**Verdict:** TODO (choose one)

- 🟢 **Verified** — Web client is thin-client aligned.
- 🔴 **Remediation required** — violations found; implementation PR needed.

If remediation is required:

- **Next PR:** PR-601 — Web Thin Client Remediation (single seam + DTO cleanup + error mapping)

---

## 9) DoD checklist (PR-599)

- [ ] Audit file is self-contained (commands + observed output + decisions).
- [ ] “Verified” includes minimal observed outputs for each key evidence command.
- [ ] Clear verdict (`Verified` or `Remediation required`) is present.
- [ ] Decision log explains why verdict was chosen (based only on evidence).
- [ ] Next step is explicit (no remediation vs link to remediation PR).
- [ ] No runtime files changed (docs-only).

---

## 10) Links

- PR-597 merge commit: `898a46b8b6fc4a0ecf6be77dd5114fa770eb025a`
- PR-598 merge commit: `7044beea451857e80c5215a89e1d77452d825d9a`
- Related web thin-adapter audits:
  - `docs/audit/PR_586_WEB_THIN_HTTP_ADAPTER_AUDIT.md`
  - `docs/audit/PR_587_WEB_THIN_HTTP_ADAPTER_REMEDIATION_AUDIT.md`

---

**Last updated:** 2026-01-26
