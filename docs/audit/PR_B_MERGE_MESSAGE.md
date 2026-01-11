# PR-B Merge Message (Squash & Merge)

## Title
```text
feat(vip): enforce VIP tier guard consistency + OpenAPI security scheme
```

## Body
```text
Move tier dependencies from Header() to Security(APIKeyHeader) to keep OpenAPI clean and prevent per-operation header parameters.

Changes:
- Update require_vip_tier() and require_pro_tier() to use Security(api_key_header) instead of Header(None)
- Regenerate OpenAPI artifacts (openapi.json, schema.ts) - credentials now modeled as security scheme
- Update VIP coverage tests to use vip_headers fixture (valid VIP key) - tests now correctly pass tier guard
- Add guard-order test ensuring 403 (tier gate) wins over 422 (validation)
- Fix deprecated /api/v1/vip/weekly-plan to handle dict plan results (no AttributeError)
- Update AGENTS.md with Security() pattern rules and OpenAPI sync guidance
- Remove unused _require_api_key_strict() function from vip.py

Scope: ~28 files changed due to one logical change affecting multiple layers:
- Backend auth layer (Header → Security)
- OpenAPI artifacts (required by CI sync job)
- VIP tests (behaviorally affected by tier enforcement)
- Documentation (AGENTS.md + audit notes)

No unrelated refactors or mass updates included.

Fixes: VIP endpoints now consistently enforce tier-based access control
Related: PR-A (docs-only governance), PR-C (VIP alignment - follow-up)
```
