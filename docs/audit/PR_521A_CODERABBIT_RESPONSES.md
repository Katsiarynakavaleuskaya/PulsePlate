# PR-521A — CodeRabbit Response Templates

**Date:** 2026-01-12
**Purpose:** Ready-to-use responses for CodeRabbit comments

---

## 🔴 Critical: PlateResponse Type Fix (FIXED)

**CodeRabbit Comment:**
> `frontend/src/api/premium/plate.ts` — тип должен быть OpenAPI `PlateResponse`, не `PlateApiResponse`

**Status:** ✅ **FIXED** in this PR

**Response:**
> ✅ Fixed — replaced `PlateApiResponse` with OpenAPI-generated `components["schemas"]["PlateResponse"]` and updated downstream usage (`hooks.ts` alias `ApiPlateResponse`). This removes the duplicated manual type and aligns with frontend AGENTS rule: use OpenAPI types from `schema.ts`.

---

## 🟠 Major: test_pro_contracts_bootstrap.py (Out of Scope)

**CodeRabbit Comment:**
> `tests/test_pro_contracts_bootstrap.py` — использовать `client.app`, не `import app; app.app`

**Response:**
> Agree; test should use `client.app`. Out of scope for this frontend-only PR — I'll address in a follow-up backend/contracts PR.

---

## ⚠️ Outside diff: legacy_app.py macros coercion (Out of Scope)

**CodeRabbit Comment:**
> `legacy_app.py` macros coercion "leave as-is" → default 0

**Response:**
> Makes sense — leaving non-numeric macros can violate `PlateResponse` and lead to 500. Out of scope for this PR; I'll handle in a dedicated legacy-contract hardening PR (with tests) to avoid mixing behavior changes with contract wiring.

---

## 🟡 Docs nit: "follow after" → "follow" (Out of Scope)

**CodeRabbit Comment:**
> Docs wording: "follow after" → "follow"

**Response:**
> Ack — will tweak wording ("follow after" → "follow") in the docs PR where this template lives, to keep PR scope clean.

---

## 📋 PR Scope Clarification

**If CodeRabbit asks about scope:**

**Response:**
> This PR is strictly frontend-only (4 files: `targets.ts`, `plate.ts`, `client.ts`, `targets-integration.test.ts`). Backend changes, test improvements, and docs fixes are tracked in separate PRs to maintain clean scope boundaries.

---

**Last updated:** 2026-01-12
**Status:** Ready for PR review
