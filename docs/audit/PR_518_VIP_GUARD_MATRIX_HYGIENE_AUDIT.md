# PR-518 — VIP Guard Matrix + Test Hygiene Audit

**Date:** 2026-01-11  
**Scope:** Test hygiene improvements + canonical VIP guard matrix  
**Goal:** Fix test pollution, sys.modules violations, and create single source of truth for VIP tier guard matrix

---

## 1) Findings (Facts Only)

### F1 — Env cleanup incomplete in `test_vip_coverage_boost.py`

**Current state:**
- `teardown_method()` cleans only `API_KEY`
- `VIP_MODULE_ENABLED` is set in `setup_method()` but not cleaned

**Evidence:**
```python
def setup_method(self):
    os.environ["VIP_MODULE_ENABLED"] = "true"
    os.environ["API_KEY"] = "test_key"

def teardown_method(self):
    os.environ.pop("API_KEY", None)  # VIP_MODULE_ENABLED not cleaned
```

**Impact:** Test pollution under xdist (env vars leak between workers).

---

### F2 — Direct `sys.modules` mutations in `test_vip_coverage_clean.py`

**Current state:**
- Direct `del sys.modules[...]` and `sys.modules[...] = ...` operations
- Violates repo policy: "sys.modules mutation forbidden; use monkeypatch"

**Evidence:**
```python
del sys.modules[mod_name]  # Line 56, 72, 77
sys.modules[mod_name] = mod_obj  # Line 54, 90
```

**Impact:** Violates repo guard policy; can cause xdist flakiness.

---

### F3 — VIP guard matrix scattered across multiple test files

**Current state:**
- `test_vip_guard_consistency.py` has 17 endpoints but focuses on guard enforcement (403 vs 2xx)
- `test_vip_api.py` has individual endpoint tests but no unified matrix
- No single canonical source for "all VIP endpoints + tier denial matrix"

**Impact:** CodeRabbit correctly flags "duplication risk" and "where is the matrix?"

---

### F4 — Dependency overrides with vip_headers (guard bypass confusion)

**Current state:**
- Some tests override `require_vip_tier` AND send `vip_headers`
- This doesn't test the guard at all

**Evidence:**
```python
app.app.dependency_overrides[api_tiers.require_vip_tier] = mock_require_vip_tier
# ... then ...
response = client.post(..., headers=vip_headers)  # Guard is bypassed!
```

**Impact:** Tests claim to test "VIP access" but actually bypass guard.

---

## 2) Proposed Remediation

### R1 — Env cleanup fix

**File:** `tests/test_vip_coverage_boost.py`

**Change:**
```python
def teardown_method(self):
    os.environ.pop("API_KEY", None)
    os.environ.pop("VIP_MODULE_ENABLED", None)  # ADD THIS
```

**DoD:** All env vars set in `setup_method` are cleaned in `teardown_method`.

---

### R2 — Replace sys.modules mutations with monkeypatch

**File:** `tests/test_vip_coverage_clean.py`

**Change:**
- Replace `del sys.modules[...]` → `monkeypatch.delitem(sys.modules, name, raising=False)`
- Replace `sys.modules[...] = ...` → `monkeypatch.setitem(sys.modules, name, value)`

**DoD:** No direct `sys.modules` mutations; all via `monkeypatch`.

---

### R3 — Create canonical VIP guard matrix test

**File:** `tests/test_vip_api.py` (add at end)

**Content:** Parametrized matrix test covering all 17 VIP endpoints:
- FREE (empty headers) → 403 + error envelope
- PRO (`TEST_KEY_PRO`) → 403 + error envelope  
- VIP (`TEST_KEY_VIP`) → 2xx

**DoD:** Single parametrized test covers all 17 endpoints with tier denial matrix.

---

### R4 — Document guard bypass pattern

**File:** `AGENTS.md`

**Add rule:**
- If test overrides `require_vip_tier` dependency → do NOT send `vip_headers` (guard is bypassed)
- If test name includes `_with_guard_bypassed` → override is intentional for business logic testing
- If test name does NOT include bypass marker → no overrides, use real keys

**DoD:** Clear policy on when dependency overrides are acceptable.

---

## 3) VIP Endpoints List (17 total)

**GET (9):**
1. `/api/v1/vip/health`
2. `/api/v1/vip/shoplist/formats`
3. `/api/v1/vip/regions`
4. `/api/v1/vip/regions/{region}/search`
5. `/api/v1/vip/regions/{region}/categories`
6. `/api/v1/vip/regions/{region}/stores`
7. `/api/v1/vip/regions/compare/{product_name}`
8. `/api/v1/vip/recipes/templates`
9. `/api/v1/vip/auto-repair/strategies`

**POST (8):**
1. `/api/v1/vip/menu/weekly/plan`
2. `/api/v1/vip/menu/weekly/repair`
3. `/api/v1/vip/shoplist/weekly`
4. `/api/v1/vip/shoplist/daily`
5. `/api/v1/vip/recipes/synthesize`
6. `/api/v1/vip/recipes/weekly`
7. `/api/v1/vip/auto-repair/weekly`
8. `/api/v1/vip/auto-repair/suggestions`

---

## 4) DoD Checklist

- [ ] Env cleanup: all vars set in setup are cleaned in teardown
- [ ] sys.modules: all mutations via monkeypatch (no direct del/assign)
- [ ] VIP guard matrix: single parametrized test in `test_vip_api.py` covers all 17
- [ ] AGENTS.md: rule added for dependency override pattern
- [ ] CI green: `make verify` passes
- [ ] No breaking changes: existing tests still pass

---

## 5) Related Documents

- `tests/test_vip_guard_consistency.py` — guard enforcement tests (keep as-is)
- `AGENTS.md` — repo-wide test policies
- `docs/ENGINEERING_LESSONS.md` — sys.modules policy
