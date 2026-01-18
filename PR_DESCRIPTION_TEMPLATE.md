# PR Title (squash title)

```
feat(bmi): add PRO WHR endpoint (hip_cm) and keep FREE contract unchanged
```

# PR Description (первые 20 строк)

```markdown
## Summary

Adds PRO-tier BMI endpoint with WHR (Waist-to-Hip Ratio) calculation while preserving FREE contract unchanged.

**Tier policy:**
- **FREE** `/api/v1/bmi/calculate`: ignores `hip_cm` and returns `whr=null/omitted`
- **PRO**: new `/api/v1/pro/bmi/calculate` accepts `hip_cm` and returns `whr`

**Schemas:**
- FREE models unchanged (`BMICalculateRequest/Response`)
- PRO models added (`BMICalculateProRequest/Response`)

**Artifacts:**
- OpenAPI JSON + TS types regenerated (openapi-typescript)

**Non-goals:**
- No hip input in web UI in this PR (FREE UI intentionally omits)

**Includes audit doc:** `docs/audit/BACKEND_HIP_WHR_AUDIT.md`

---

## Changes

### Backend
- Split FREE vs PRO schemas in `app/schemas/bmi.py`
- Added `/api/v1/pro/bmi/calculate` endpoint with `require_pro_tier` guard
- FREE endpoint explicitly passes `hip_cm=None` to engine
- Engine: `_compute_whr` with fail-soft error handling

### Tests
- WHR endpoint tests moved to PRO endpoint
- FREE endpoint asserts absence of `whr` field
- Guard test updated: `required_fields` includes `whr`, `notes`, `age_band`
- Overflow test corrected: validates engine fail-soft behavior

### Frontend
- Comment updated: `hip_cm` intentionally omitted on FREE tier UI

### Docs
- `AGENTS.md`: added tier policy rule for new metrics/features

---

## DoD Checklist

- [x] FREE endpoint ignores `hip_cm` and never returns `whr`
- [x] PRO endpoint accepts `hip_cm?` and returns `whr?`
- [x] OpenAPI determinism: `make openapi && make openapi-check` green
- [x] Guard coverage: `required_fields` includes `whr`, `notes`, `age_band`
- [x] Tests: WHR tests use PRO path; FREE asserts `whr` absence
- [x] Frontend comment updated
- [x] AGENTS.md policy rule added
- [ ] **Coverage gap:** Missing lines in `app/routers/bmi.py` (373-374,390,397,402-403,419-421) and `core/bmi/engine.py` (203) — **needs tests before merge**

---

## Related

- Addresses tier policy violation identified in PR #554 review
- Implements backend-first approach from `BACKEND_HIP_WHR_AUDIT.md`
```
