# Soft Paywall Hook — Pre-Implementation Audit

**Date:** 2026-01-16
**Purpose:** Complete audit before implementing soft paywall hook in Free tier BMI endpoint
**Scope:** MVP hook placement, contract design, i18n strategy, testing approach

---

## Executive Summary

**Target Endpoint:** `POST /api/v1/bmi/calculate` (FREE tier, no API key required)
**Hook Placement:** Top-level optional field `soft_paywall: SoftPaywallHook | None`
**i18n Strategy:** Keys + default text (3 keys: title/body/cta)
**Implementation Layer:** Router/response mapper (NOT in core/bmi)
**Tests Required:** 2-4 contract tests + i18n parameterization

---

## A) Scope / Policy

### A1. Free Tier Endpoints (MVP Target)

**Canonical FREE tier endpoint for MVP:**
- `POST /api/v1/bmi/calculate` — BMI calculation (FREE, no API key required)
  - Location: `app/routers/bmi.py:225`
  - Response model: `BMICalculateResponse` (`app/schemas/bmi.py:356`)
  - Status: ✅ Canonical, fully implemented

**Other FREE tier endpoints (out of scope for MVP):**
- `/api/v1/foods/*` — Food database (FREE)
- `/api/v1/recipes/*` — Recipe browsing (FREE)
- `/api/v1/users/*` — User management (FREE)

**Decision:** MVP hook goes **only** into `/api/v1/bmi/calculate` to keep scope minimal.

---

### A2. Tier Gating Mechanism

**Current tier gating system:**
- Location: `app/middleware/api_tiers.py`
- Functions: `require_pro_tier()`, `require_vip_tier()`
- FREE tier: **No middleware required** (absence of guard = FREE tier)
- PRO tier: `dependencies=[Depends(require_pro_tier)]`
- VIP tier: `dependencies=[Depends(require_vip_tier)]`

**Evidence:**
- `app/routers/bmi.py:225` — no `dependencies` = FREE tier
- `app/routers/bmi_pro.py:108` — `dependencies=[Depends(require_pro_tier)]` = PRO tier

**Decision:** Hook appears on FREE tier endpoints only (no guard = FREE).

---

### A3. BMI Logic Policy

**Hard rule from AGENTS.md:**
> "BMI formulas/thresholds/constants ONLY allowed in `core/bmi/*`"

**What is considered "BMI logic" (forbidden in hook):**
- ❌ Any BMI calculation (`calc_bmi`, `_compute_bmi`)
- ❌ Any BMI category determination (`get_category`, thresholds)
- ❌ Any BMI interpretation (`interpret_bmi`, risk assessment)
- ❌ Any condition based on BMI value (e.g., "if BMI > 25, show hook")

**What is allowed in hook:**
- ✅ Simple availability check (`pro_available: bool`)
- ✅ i18n key selection (no BMI-dependent logic)
- ✅ Response field injection (pure data structure)

**Decision:** Hook builder **MUST NOT** import `core/bmi/*` or check BMI values.

---

### A4. Hook Display Conditions

**MVP rule:**
- Hook appears **always** on successful FREE tier response (status 200)
- Condition: `pro_available=true` (feature flag/env var)
- No BMI-dependent conditions (wellness-only positioning)

**Future conditions (out of scope):**
- Region-based display
- A/B testing flags
- User segment targeting

**Decision:** Simple feature flag `SOFT_PAYWALL_ENABLED` (default: `true` in dev, configurable in prod).

---

### A5. Legal/Wellness Positioning

**Wellness-only requirement:**
- No medical claims ("diagnosis", "treatment", "cure")
- No BMI-dependent messaging ("your BMI is high, upgrade")
- Focus on features, not health outcomes

**Canonical wellness phrasing:**
- "Unlock advanced features" (not "get better results")
- "Access detailed analysis" (not "improve your health")
- "See comprehensive insights" (not "fix your BMI")

**Decision:** All hook text must pass wellness-only review (no medical language).

---

## B) Contract Placement

### B1. Response Model Location

**Canonical response model:**
- File: `app/schemas/bmi.py:356`
- Class: `BMICalculateResponse`
- Current fields: `bmi`, `category`, `group`, `group_display`, `interpretation`, `wht_ratio`, `waist_risk`, `notes`, `age_band`, `visualization`, `interpretation_v1`

**Decision:** Add `soft_paywall: SoftPaywallHook | None = None` as top-level optional field.

---

### B2. Current Response Structure

**Current response style:**
- Top-level fields (no `meta` wrapper)
- Optional fields use `| None` (Pydantic v2 style)
- Nested objects for complex data (`waist_risk: WaistRiskResultSchema`, `visualization: BMIScaleV1Spec`)

**No existing patterns:**
- No `meta` object
- No `extras` object
- No `links` object

**Decision:** Follow existing pattern — top-level optional field `soft_paywall`.

---

### B3. Backward Compatibility

**Pydantic v2 compatibility:**
- Adding optional top-level field (`field: Type | None = None`) is **backward compatible**
- Clients ignore unknown fields by default
- OpenAPI schema includes optional fields

**Evidence from codebase:**
- `visualization: BMIScaleV1Spec | None = None` — added without breaking changes
- `interpretation_v1: BMIInterpretationV1Schema | None = None` — added without breaking changes

**Decision:** Adding `soft_paywall: SoftPaywallHook | None = None` is safe (backward compatible).

---

### B4. OpenAPI/Contract Tests

**OpenAPI generation:**
- Location: `scripts/generate_openapi.py`
- Output: `frontend/src/api/openapi.json`, `frontend/src/api/schema.ts`
- Determinism test: `tests/test_openapi_determinism.py`

**Contract tests:**
- `tests/test_bmi_schemas.py` — schema validation tests
- `tests/test_bmi_calculate_endpoint.py` — endpoint contract tests

**Decision:** Must update OpenAPI schema (run `make openapi`) and add contract test.

---

### B5. Naming Convention

**Current naming patterns:**
- Top-level fields: `snake_case` (`wht_ratio`, `waist_risk`, `age_band`)
- Nested objects: `PascalCase` classes (`WaistRiskResultSchema`, `BMIScaleV1Spec`)

**Decision:** Use `soft_paywall: SoftPaywallHook | None` (consistent with existing pattern).

---

## C) i18n & Text Strategy

### C1. i18n Storage

**Location:** `core/i18n.py`
- Dictionary: `TRANSLATIONS: dict[str, dict[str, str]]`
- Languages: `"ru"`, `"en"`, `"es"`
- Function: `t(lang: Language, key: str, **kwargs: Any) -> str`

**Decision:** Add 3 keys to `TRANSLATIONS` dict:
- `soft_paywall.title`
- `soft_paywall.body`
- `soft_paywall.cta`

---

### C2. API Keys vs Ready Text

**Current pattern in responses:**
- **Ready text:** `category: str` (localized string, e.g., "Normal weight")
- **i18n keys:** `interpretation_v1.risk_flags: tuple[str, ...]` (keys like `"bmi.interpretation.risk.extreme_value"`)

**Mixed approach:**
- Some fields return ready text (`category`, `interpretation`)
- Some fields return i18n keys (`interpretation_v1.*`)

**Decision:** Hook returns **both**:
- `i18n_key: str` (e.g., `"soft_paywall.title"`)
- `default_text: str` (e.g., `"Unlock Advanced Features"`)

**Rationale:** Clients can use `default_text` immediately (no i18n lookup required), but can also use `i18n_key` for custom translations.

---

### C3. Source of Truth

**Current approach:**
- Backend is source of truth for i18n keys
- Frontend/iOS use backend keys for consistency
- Default text provided for fallback

**Decision:** Backend provides both keys and defaults (clients can override if needed).

---

### C4. Response Format

**Decision:** Return both `i18n_key` and `default_text`:

```python
class SoftPaywallHook(BaseModel):
    title_i18n_key: str = "soft_paywall.title"
    title_default: str = Field(..., description="Default title text")
    body_i18n_key: str = "soft_paywall.body"
    body_default: str = Field(..., description="Default body text")
    cta_i18n_key: str = "soft_paywall.cta"
    cta_default: str = Field(..., description="Default CTA text")
    target: Literal["pro_paywall"] = "pro_paywall"
    available: bool = True
```

---

### C5. Language Selection

**Current language handling:**
- Request field: `lang: Language = Field(default="en", ...)` in `BMICalculateRequest`
- Normalization: `core.i18n.normalize_lang()` (handles `en-US`, `ru-RU`, etc.)
- Fallback: `"en"` for unknown languages

**Decision:** Use `req.lang` from request (already normalized to `"ru"|"en"|"es"`).

---

## D) Availability / CTA Target

### D1. Pro Availability Check

**MVP approach:**
- Feature flag: `SOFT_PAYWALL_ENABLED` (env var, default: `true`)
- Simple boolean: `pro_available = os.getenv("SOFT_PAYWALL_ENABLED", "true").lower() in ("true", "1", "yes", "on")`

**Future (out of scope):**
- Database subscription check
- Billing integration
- Regional availability

**Decision:** Simple env var check for MVP.

---

### D2. CTA Target

**Decision:** Abstract target `"pro_paywall"` (not route/URL).

**Rationale:**
- Clients handle routing (iOS: `NavigationLink`, Web: router)
- Backend doesn't know client routing structure
- Abstraction allows clients to implement custom paywall flows

**Format:**
```python
target: Literal["pro_paywall"] = "pro_paywall"
```

---

### D3. Deep Links / URLs

**Decision:** ❌ No URLs/deep links in MVP.

**Rationale:**
- Routing is client responsibility
- URLs would couple backend to client structure
- Abstraction (`target: "pro_paywall"`) is sufficient

---

### D4. Unavailable Reason

**Decision:** ❌ Not needed for MVP.

**Rationale:**
- MVP assumes `pro_available=true` (feature flag)
- If unavailable, hook is simply `None` (not included in response)
- Future: can add `disabled_reason` if needed

---

## E) Telemetry / Analytics

### E1. Event Schema

**Current state:** No event schema found in codebase.

**Decision:** ❌ No telemetry in MVP hook.

**Rationale:**
- Telemetry is client responsibility (iOS/Web track events)
- Backend hook is data-only (no behavior tracking)
- Can add telemetry fields later if needed

---

### E2. Impression/Click Events

**Decision:** ❌ Not included in MVP.

**Rationale:**
- Events are client-side (Firebase, Amplitude, etc.)
- Backend hook doesn't track user interactions
- Keep hook minimal (data structure only)

---

### E3. Telemetry in Public Responses

**Decision:** ❌ No telemetry fields in public API responses.

**Rationale:**
- Telemetry is internal (not part of public contract)
- Clients handle analytics separately
- Keep response clean (wellness-focused)

---

### E4. Versioning

**Decision:** ❌ No versioning in MVP.

**Rationale:**
- Hook structure is simple (unlikely to change)
- If breaking changes needed, add new field (`soft_paywall_v2`)
- Versioning adds complexity without benefit for MVP

---

## F) Implementation Boundaries

### F1. Hook Formation Layer

**Allowed layers:**
- ✅ Router layer (`app/routers/bmi.py`)
- ✅ Response mapper/adapter (helper function in router)
- ❌ NOT in `core/bmi/*` (BMI logic layer)

**Decision:** Create helper function in router:

```python
# app/routers/bmi.py

def _build_soft_paywall_hook(lang: Language) -> SoftPaywallHook | None:
    """Build soft paywall hook if enabled."""
    if not _is_soft_paywall_enabled():
        return None
    return SoftPaywallHook(
        title_i18n_key="soft_paywall.title",
        title_default=t(lang, "soft_paywall.title"),
        body_i18n_key="soft_paywall.body",
        body_default=t(lang, "soft_paywall.body"),
        cta_i18n_key="soft_paywall.cta",
        cta_default=t(lang, "soft_paywall.cta"),
        target="pro_paywall",
        available=True,
    )
```

---

### F2. BMI Logic Risk

**Guard against BMI logic:**
- ❌ No imports from `core/bmi/*` in hook builder
- ❌ No BMI value checks (`if bmi > 25`)
- ❌ No category checks (`if category == "overweight"`)

**Decision:** Hook builder is **pure function** (lang → hook, no BMI dependencies).

---

### F3. Guard Test

**Decision:** Add guard test:

```python
# tests/test_no_bmi_logic_in_paywall.py

def test_soft_paywall_builder_does_not_import_bmi_core():
    """Guard: soft paywall builder must not import core/bmi."""
    import app.routers.bmi as bmi_router
    import inspect

    # Check that _build_soft_paywall_hook doesn't import core/bmi
    source = inspect.getsource(bmi_router._build_soft_paywall_hook)
    assert "from core.bmi" not in source
    assert "import core.bmi" not in source
```

---

## G) Tests & CI

### G1. Test Types

**Current test types:**
- Contract tests: `tests/test_bmi_schemas.py`
- Endpoint tests: `tests/test_bmi_calculate_endpoint.py`
- Integration tests: `tests/test_bmi_pro_simple.py`

**Decision:** Add 2-4 tests:
1. Schema validation test (hook structure)
2. Endpoint response test (hook included when enabled)
3. i18n parameterization test (ru/en/es)
4. Guard test (no BMI logic)

---

### G2. Test Location

**Decision:** Add to existing test files:
- Schema test: `tests/test_bmi_schemas.py` (add `TestSoftPaywallHook`)
- Endpoint test: `tests/test_bmi_calculate_endpoint.py` (add hook assertion)
- i18n test: New file `tests/test_soft_paywall_i18n.py` (parameterized)
- Guard test: New file `tests/test_no_bmi_logic_in_paywall.py`

---

### G3. i18n Parameterization

**Current i18n test pattern:**
- `tests/test_i18n_bmi_visualization.py` — parameterized by lang

**Decision:** Use pytest parameterization:

```python
@pytest.mark.parametrize("lang", ["ru", "en", "es"])
def test_soft_paywall_i18n_keys_exist(lang: Language):
    """Test that all i18n keys exist for all languages."""
    from core.i18n import t, TRANSLATIONS
    assert "soft_paywall.title" in TRANSLATIONS[lang]
    assert "soft_paywall.body" in TRANSLATIONS[lang]
    assert "soft_paywall.cta" in TRANSLATIONS[lang]
```

---

### G4. Coverage Requirements

**Current requirements:**
- Total coverage: ≥97% (`make cov-check`)
- Diff coverage: ≥97% (`make diff-cov`)

**Decision:** Ensure all new code is covered (hook builder, schema, tests).

---

## H) Docs & AGENTS.md

### H1. Contract Documentation

**Canonical location:** `docs/contracts/`

**Decision:** Create `docs/contracts/SOFT_PAYWALL_HOOK.md` with:
- Schema definition
- i18n keys
- Usage examples
- Client integration guide

---

### H2. OpenAPI Update

**Decision:** ✅ Must update OpenAPI schema.

**Process:**
1. Add `SoftPaywallHook` schema to `app/schemas/bmi.py`
2. Add `soft_paywall` field to `BMICalculateResponse`
3. Run `make openapi` (generates `frontend/src/api/openapi.json`)
4. Commit generated files

---

### H3. AGENTS.md Update

**Decision:** Add section to `AGENTS.md`:

```markdown
## Soft Paywall Hook Policy (Hard Rule)

**Invariant:** Soft paywall hooks must be formed in router/adapter layer only, never in `core/bmi/*`.

**Enforcement:**
- Hook builders must not import `core/bmi/*`
- Hook builders must not check BMI values or categories
- Hook is pure data structure (lang → hook, no domain logic)

**Allowed:**
- Hook formation in `app/routers/*` (router layer)
- i18n key lookup via `core.i18n.t()`
- Feature flag checks (env vars)

**Forbidden:**
- Any BMI logic in hook builder
- Any imports from `core/bmi/*` in hook builder
- BMI-dependent hook display conditions
```

---

## Decision Log

- [x] **Endpoint MVP:** `POST /api/v1/bmi/calculate` (FREE tier)
- [x] **Placement:** `soft_paywall: SoftPaywallHook | None` (top-level optional field)
- [x] **Keys:** 3 keys (`soft_paywall.title`, `soft_paywall.body`, `soft_paywall.cta`) + default text
- [x] **Availability:** Env var `SOFT_PAYWALL_ENABLED` (default: `true`)
- [x] **Tests:** 4 tests (schema, endpoint, i18n, guard)
- [x] **Implementation Layer:** Router helper function (`app/routers/bmi.py`)
- [x] **i18n Strategy:** Keys + default text (both in response)
- [x] **Language:** From request `lang` field (normalized via `core.i18n.normalize_lang()`)

---

## Next Actions

1. **Create schema:** `SoftPaywallHook` in `app/schemas/bmi.py`
2. **Add i18n keys:** 3 keys to `core/i18n.py` (ru/en/es)
3. **Implement hook builder:** `_build_soft_paywall_hook()` in `app/routers/bmi.py`
4. **Wire hook into response:** Add to `BMICalculateResponse` in handler
5. **Add tests:** 4 tests (schema, endpoint, i18n, guard)
6. **Update OpenAPI:** Run `make openapi` and commit generated files
7. **Update docs:** Create `docs/contracts/SOFT_PAYWALL_HOOK.md`
8. **Update AGENTS.md:** Add soft paywall hook policy section

---

## Security Notes

- ✅ No external URLs/deep links
- ✅ No personal data in hook text
- ✅ No BMI-dependent conditions (wellness-only)
- ✅ No telemetry in public responses

---

## Marketing & GTM

- ✅ Wellness-only phrasing (no medical claims)
- ✅ Feature-focused messaging ("unlock features", not "fix health")
- ✅ Ready-to-use CTA object (clients don't need to write text)
- ✅ Consistent branding (i18n keys ensure same message across clients)

---

**Audit Status:** ✅ Complete
**Ready for Implementation:** Yes
**Estimated Effort:** 2-4 hours (schema + hook builder + tests + docs)
