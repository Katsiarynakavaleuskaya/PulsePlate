# PR-521: iOS OpenAPI Generation Decision

**Date:** 2026-01-12
**Question:** Will iOS use OpenAPI generation or manual Swift models?

---

## Current State (Facts)

**iOS Implementation:**
- Uses manual Swift models (`struct` with `Codable`)
- Manual API client (`APIClient.swift` with `URLSession`)
- No OpenAPI generation found in codebase
- `ios/AGENTS.md` mentions "Keep API changes synchronized with backend schema updates" but no generation

**Evidence:**
- `docs/IOS_API_INTEGRATION.md` shows manual Swift structs
- No `openapi-generator` or similar tools in `ios/`
- No generated Swift files from OpenAPI

---

## Decision (Now)

**iOS is manual today.**
- Uses manual Swift models (`Codable`) and manual `APIClient` (`URLSession`).
- No OpenAPI generator tooling or generated Swift code is present in `ios/`.

**Implication:** iOS does not depend on OpenAPI for codegen today.

## Future Option (Not assumed)

OpenAPI-based generation for iOS is a possible future improvement, but it is **not** a current dependency and must not be used as justification for changing schema visibility.

## OpenAPI Visibility Policy (Why `include_in_schema=False` is NOT used)

Even though iOS is manual today, the web frontend **does** consume OpenAPI (type generation from `openapi.json`), and external consumers are unknown.

Therefore, deprecated premium aliases must remain in the OpenAPI schema for now (with `deprecated: true` + vendor extensions).

**Rationale:**
- Web frontend generates types from OpenAPI (`openapi.json` → `schema.ts`).
- External OpenAPI consumers are unknown.
- iOS is manual today (does not depend on OpenAPI), but schema removal is still unsafe due to the above.

---

## Action Items

**For PR-521B:**
- Use vendor extensions only (safe for both scenarios)
- Document assumption: iOS may use OpenAPI generation in future

**Future (if needed):**
- Confirm with iOS team: manual-only or future generation?
- If manual-only confirmed → can add `include_in_schema=False` in separate PR
- If generation planned → vendor extensions remain the safe choice

---

**Last updated:** 2026-01-12
**Status:** Assumption made for PR-521B (vendor extensions only)
