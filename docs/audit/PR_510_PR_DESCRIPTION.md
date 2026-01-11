# PR-510 — Legacy App Audit (Analysis Only)

## Summary

This PR introduces a canonical audit of `legacy_app.py` and OpenAPI generation to establish a contract-first baseline for PR-511A/511B refactoring.

**Status:** Analysis-only (no runtime or behavior changes)

## Audit Evidence

See: [`docs/audit/PR_510_AUDIT_EVIDENCE_PACK.md`](./PR_510_AUDIT_EVIDENCE_PACK.md)

## Key Findings

1. **Import-time orchestration:** `legacy_app.py` performs app creation and router registration at module level
2. **Public OpenAPI exposure:** `/openapi.json` is publicly accessible → security boundary required
3. **Canonical normalization contract:** OpenAPI determinism via sorted paths/methods, not registration order
4. **Schema-only gaps:** VIP/BMI Pro/Business/Test routers lack schema-only guards (ORM import risk)
5. **VIP default behavior:** `VIP_MODULE_ENABLED` defaults to `True` → premium_week router imports ORM models

## Outcomes

- Identified import-time side-effects and orchestration logic in `legacy_app.py`
- Confirmed public OpenAPI schema exposure (no auth on `/openapi.json`)
- Defined canonical OpenAPI normalization contract (sorted order, not registration order)
- Fixed scope boundaries for follow-up PRs (PR-511A: extraction, PR-511B: guards)

## Next Steps

- **PR-511A:** Extract orchestration (app factory + registration module) — no behavior changes
- **PR-511B:** Unified schema-only guards & public schema hygiene (security boundary)

## Files Changed

- `docs/audit/PR_510_legacy_app_audit.md` — Detailed endpoint and router analysis
- `docs/audit/PR_510_AUDIT_EVIDENCE_PACK.md` — Canonical audit artifact with code evidence

## Related

- PR-508: OpenAPI determinism baseline (merged)
- PR-511A: Legacy app orchestration extraction (planned)
- PR-511B: Schema-only unified guards (planned)
