# PR-521A — Sourcery Response Templates

**Date:** 2026-01-12
**Purpose:** Ready-to-use responses for Sourcery comments

---

## Overall Comment Response

**Sourcery Comment:**
> Overall suggestions: add path constants, fix PlateResponse type, add plate tests

**Response:**
> Thanks! This PR focuses on frontend client migration from deprecated `/api/v1/premium/*` to canonical `/api/v1/pro/nutrition/*` endpoints. Backend route templates are unchanged, so metrics label resolution and server-side alerts are unaffected. Shared constants for PRO nutrition paths are introduced (used by client, mocks and tests), and the plate API generic now uses the OpenAPI-generated `PlateResponse`. Integration tests assert `getPlate` hits the canonical path and validate the request/response contract.

---

## Comment 1: createPremiumEndpoint naming

**Sourcery Comment:**
> `createPremiumEndpoint` is used with `/pro/...` paths — consider renaming or moving module

**Response:**
> Agree the naming is a bit confusing. This module lives under `premium/*` as a deprecated client layer while we migrate to canonical `/api/v1/pro/*` routes. I'll keep `createPremiumEndpoint` unchanged in this PR to avoid scope creep, but I'll add a small inline note + shared path constant to make the intent explicit. A dedicated `createProEndpoint`/module move can follow once all premium callers are migrated.

---

## Comment 2: Path constants

**Sourcery Comment:**
> Extract endpoint paths as constants

**Response:**
> ✅ Done — added `PRO_NUTRITION_TARGETS_PATH` and `PRO_NUTRITION_PLATE_PATH` constants in `client.ts` and exported for shared usage. In `targets.ts/plate.ts` I intentionally keep the literal strings for now because the test harness mocks `client.ts` and we previously hit an `undefined` path regression; once the mock module boundary is cleaned up we can safely switch to importing the constants everywhere (follow-up PR if needed).

---

## Comment 3: PlateResponse type fix

**Sourcery Comment:**
> Use OpenAPI `PlateResponse` instead of manual `PlateApiResponse`

**Response:**
> ✅ Fixed — `getPlate` now uses OpenAPI `PlateResponse` from `schema.ts` (`components['schemas']['PlateResponse']`). Updated `plate.ts`, `index.ts`, `hooks.ts`, and `client.ts` to use the generated schema type.

---

## Comment 4: Add plate tests

**Sourcery Comment:**
> Add integration test for `getPlate` endpoint

**Response:**
> ✅ Added — extended `targets-integration.test.ts` with a `Plate API Integration` section that asserts `getPlate` hits `PRO_NUTRITION_PLATE_PATH` and validates the request/response contract.

---

## Comment 6: Use path constants in tests

**Sourcery Comment:**
> Use exported PRO path constants in test expectations instead of string literals

**Response:**
> ✅ Applied — tests now assert against exported `PRO_NUTRITION_TARGETS_PATH` and `PRO_NUTRITION_PLATE_PATH` constants to prevent drift.

---

## Comment 7: Use path constants in mockUrl

**Sourcery Comment:**
> Use PRO path constants in `mockUrl` for consistency

**Response:**
> ✅ Applied — `mockUrl` now uses `PRO_NUTRITION_*_PATH` constants to avoid drift.

---

## Comment 8: Update types.test.ts to OpenAPI PlateResponse

**Sourcery Comment:**
> `types.test.ts` still validates legacy `PlateApiResponse` — should validate OpenAPI `PlateResponse` contract

**Response:**
> ✅ Updated — `types.test.ts` now validates OpenAPI `PlateResponse` contract (replaced legacy `PlateApiResponse` expectations). This ensures test coverage aligns with the canonical OpenAPI schema.

---

## Comment 5: Mock routing for both paths

**Sourcery Comment:**
> Support both premium and pro paths in mockUrl for backward compatibility

**Response:**
> Skipped for now — this PR migrates the only callers of `/api/v1/premium/{targets,plate}`. If other legacy callers are discovered, we can add alias support in a follow-up PR. Keeping mock routing strict to the canonical paths encourages migration.

---

**Last updated:** 2026-01-12
**Status:** Ready for PR review
