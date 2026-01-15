# Shim Audit: BMI Pro Endpoint Migration

**Date:** 2026-01-15
**Purpose:** Audit existing shim pattern and plan namespace migration for `/api/v1/bmi/pro` → `/api/v1/pro/bmi`
**Context:** CodeRabbit review identified missing Pro tier guard and namespace inconsistency

---

## 🔍 Current State Audit

### 1. Existing Shim Pattern (Reference Implementation)

**File:** `app/routers/premium_week.py`

**Pattern:**
- **Canonical endpoint:** `/api/v1/pro/meal/weekly` (in `app/routers/pro.py`)
- **Deprecated alias:** `/api/v1/premium/plan/week-flexible` (in `app/routers/premium_week.py`)
- **Registration:** Both routers registered in `app/routers/pro_registration.py`
- **Guard:** Both endpoints use `require_pro_tier` dependency
- **OpenAPI:** Deprecated endpoint marked with `deprecated=True` and `x-alias-of` metadata

**Key characteristics:**
```python
@router.post(
    "/plan/week-flexible",
    response_model=WeekPlanResponse,
    dependencies=[Depends(require_pro_tier)],  # ✅ Guarded
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/meal/weekly",
        "x-migration-path": "Migrate to /api/v1/pro/meal/weekly (same contract)",
    },
)
```

**Implementation:** Full implementation in deprecated router (not a thin proxy)

---

### 2. Current BMI Pro Endpoint

**File:** `app/routers/bmi_pro.py`
**Current path:** `/api/v1/bmi/pro`
**Router prefix:** `/api/v1/bmi`
**Registration:** `legacy_app.py:5553` (with `FEATURE_BMI_PRO_ENABLED` flag)

**Issues identified:**
1. ❌ **Missing Pro tier guard** — endpoint accessible without `require_pro_tier`
2. ❌ **Wrong namespace** — should be `/api/v1/pro/bmi` (canonical Pro namespace)
3. ✅ **Uses Pro tier functions** — correct (no tier mixing)

---

### 3. Router Registration Pattern

**Location:** `legacy_app.py:5552-5553`
```python
FEATURE_BMI_PRO_ENABLED = _is_truthy(_bmi_pro_flag) if _bmi_pro_flag is not None else False
if FEATURE_BMI_PRO_ENABLED and bmi_pro_router:
    app.include_router(bmi_pro_router)
```

**Comparison with Pro routes:**
- **Pro routes:** Registered via `app/routers/pro_registration.py` (centralized)
- **BMI Pro:** Registered directly in `legacy_app.py` (inconsistent)

---

## 📋 Migration Plan (PR #535 + Follow-up)

### Phase 1: Add Guard (PR #535 — CRITICAL)

**Goal:** Close security hole (Free tier accessing Pro-only computations)

**Changes:**
1. Add `require_pro_tier` dependency to `bmi_pro` handler
2. Update tests to use `pro_headers` fixture

**Files:**
- `app/routers/bmi_pro.py` — add `Depends(require_pro_tier)`
- `tests/test_bmi_pro_*.py` — use `pro_headers` fixture

**Risk:** Low (adds enforcement, doesn't change contract)

---

### Phase 2: Namespace Migration (Follow-up PR — Non-breaking)

**Goal:** Move canonical endpoint to `/api/v1/pro/bmi` with backward-compatible shim

**Strategy:** Follow `premium_week.py` pattern

#### Step 1: Create Canonical Pro Router

**Option A (Recommended):** Move `bmi_pro.py` router to Pro namespace

```python
# app/routers/bmi_pro.py
router = APIRouter(prefix="/api/v1/pro", tags=["pro"])  # Changed from /api/v1/bmi

@router.post("/bmi", response_model=BMIProResponse)  # Changed from /pro
def bmi_pro(...):
    ...
```

**Option B:** Create new `app/routers/pro_bmi.py` and keep `bmi_pro.py` as shim

**Recommendation:** **Option A** (simpler, follows existing pattern)

#### Step 2: Add Deprecated Shim Endpoint

**In same file (`bmi_pro.py`) or separate shim router:**

```python
# Deprecated alias for backward compatibility
@router.post(
    "/api/v1/bmi/pro",  # Old path (no prefix, absolute path)
    response_model=BMIProResponse,
    dependencies=[Depends(require_pro_tier)],
    deprecated=True,
    openapi_extra={
        "x-alias-of": "/api/v1/pro/bmi",
        "x-migration-path": "Migrate to /api/v1/pro/bmi (same contract)",
    },
)
def bmi_pro_legacy_alias(req: BMIProRequest) -> BMIProResponse:
    """[DEPRECATED] Use /api/v1/pro/bmi instead."""
    return bmi_pro(req)  # Delegate to canonical handler
```

**Note:** If router prefix is `/api/v1/pro`, need separate router for `/api/v1/bmi/pro` shim.

#### Step 3: Registration

**Option A:** Register shim in `legacy_app.py` (like current `bmi_pro_router`)

**Option B:** Create `app/routers/bmi_pro_shim.py` and register separately

**Recommendation:** **Option B** (cleaner separation, easier to remove later)

---

## 🗺️ File Structure After Migration

```text
app/routers/
├── bmi_pro.py          # Canonical: /api/v1/pro/bmi (Pro namespace)
└── bmi_pro_shim.py     # Deprecated: /api/v1/bmi/pro (backward compat)
```

**OR (simpler):**

```text
app/routers/
└── bmi_pro.py          # Contains both:
                        # - Canonical: /api/v1/pro/bmi
                        # - Shim: /api/v1/bmi/pro (via separate router instance)
```

---

## 🔒 Guard Enforcement

**Both endpoints must be guarded:**

```python
from app.middleware.api_tiers import require_pro_tier
from fastapi import Depends

@router.post("/bmi", dependencies=[Depends(require_pro_tier)])
def bmi_pro(...):
    ...

@shim_router.post("/pro", dependencies=[Depends(require_pro_tier)])
def bmi_pro_legacy_alias(...):
    ...
```

**Verification:**
- Tests without Pro key → 403/401
- Tests with Pro key → 200
- OpenAPI shows both endpoints with security scheme

---

## 📝 Implementation Checklist

### PR #535 (Remediation — Guard Only)

- [ ] Add `require_pro_tier` to `bmi_pro` handler
- [ ] Update tests to use `pro_headers` fixture
- [ ] Verify guard works (403 without key, 200 with key)
- [ ] No namespace changes (keep `/api/v1/bmi/pro`)

### Follow-up PR (Namespace Migration)

- [ ] Move canonical endpoint to `/api/v1/pro/bmi`
- [ ] Create shim endpoint `/api/v1/bmi/pro` (deprecated)
- [ ] Both endpoints guarded with `require_pro_tier`
- [ ] Update OpenAPI metadata (`x-alias-of`, `deprecated=True`)
- [ ] Update tests (test both paths)
- [ ] Update frontend/client code to use canonical path
- [ ] Add deprecation logging (optional, for monitoring)

---

## 🧪 Test Strategy

### Guard Tests

```python
def test_bmi_pro_requires_pro_tier(client: TestClient):
    """Test that /api/v1/bmi/pro requires Pro tier key."""
    response = client.post("/api/v1/bmi/pro", json={...})
    assert response.status_code == 403  # or 401

def test_bmi_pro_with_pro_key(client: TestClient, pro_headers: dict):
    """Test that /api/v1/bmi/pro works with Pro key."""
    response = client.post("/api/v1/bmi/pro", json={...}, headers=pro_headers)
    assert response.status_code == 200
```

### Shim Tests (After Migration)

```python
def test_bmi_pro_shim_works(client: TestClient, pro_headers: dict):
    """Test that deprecated /api/v1/bmi/pro still works."""
    response = client.post("/api/v1/bmi/pro", json={...}, headers=pro_headers)
    assert response.status_code == 200
    # Verify response matches canonical endpoint

def test_bmi_pro_canonical_works(client: TestClient, pro_headers: dict):
    """Test that canonical /api/v1/pro/bmi works."""
    response = client.post("/api/v1/pro/bmi", json={...}, headers=pro_headers)
    assert response.status_code == 200
```

---

## 🔗 Related Patterns

### VIP Shim Example

**File:** `app/routers/vip.py:696-760`

**Pattern:**
- Canonical: `/api/v1/vip/menu/weekly/plan`
- Deprecated: `/api/v1/vip/weekly-plan`
- **Difference:** Both in same router (no separate shim router)

### Premium Week Shim Example

**File:** `app/routers/premium_week.py:175-310`

**Pattern:**
- Canonical: `/api/v1/pro/meal/weekly` (in `pro.py`)
- Deprecated: `/api/v1/premium/plan/week-flexible` (in `premium_week.py`)
- **Difference:** Separate routers, registered via `pro_registration.py`

---

## 📊 Decision Matrix

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Same router, two endpoints** | Simple, no extra files | Mixing canonical + deprecated | ✅ **Best for PR #535** (guard only) |
| **Separate shim router** | Clean separation | More files, registration complexity | ✅ **Best for follow-up** (namespace migration) |
| **Move to pro_registration.py** | Consistent with Pro routes | Requires refactoring registration | ⚠️ **Future improvement** (not for PR #535) |

---

## 🎯 Recommended Implementation Order

### PR #535 (Now — Guard Only)

1. Add `require_pro_tier` to existing `/api/v1/bmi/pro`
2. Update tests
3. **No namespace changes** (keep backward compatibility)

### Follow-up PR (After #535 Merge)

1. Create canonical `/api/v1/pro/bmi` endpoint
2. Add shim `/api/v1/bmi/pro` (deprecated, delegates to canonical)
3. Update OpenAPI metadata
4. Update frontend/client code
5. Add migration guide

---

## 🔍 Verification Commands

### After PR #535 (Guard Only)

```bash
# Verify guard works
pytest tests/test_bmi_pro_*.py -k "guard" -v

# Verify no namespace changes
rg "/api/v1/bmi/pro" app/routers/bmi_pro.py
rg "/api/v1/pro/bmi" app/routers/bmi_pro.py  # Should be empty
```

### After Follow-up (Namespace Migration)

```bash
# Verify canonical endpoint exists
rg "/api/v1/pro/bmi" app/routers/bmi_pro.py

# Verify shim endpoint exists
rg "/api/v1/bmi/pro" app/routers/bmi_pro.py  # or bmi_pro_shim.py

# Verify both are guarded
rg "require_pro_tier" app/routers/bmi_pro*.py

# Verify OpenAPI metadata
rg "x-alias-of|deprecated" app/routers/bmi_pro*.py
```

---

**Last updated:** 2026-01-15
**Status:** Ready for implementation (Phase 1 in PR #535, Phase 2 in follow-up)
