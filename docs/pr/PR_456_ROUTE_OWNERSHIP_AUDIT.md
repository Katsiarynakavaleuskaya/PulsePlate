# PR-456 Route Ownership Audit (Commit 1)

**Date:** 2025-01-04
**GitHub PR:** #456
**Goal:** One path → one handler. BMI math only in `core/bmi/*`.
**Status:** Docs-only audit (no code changes)

---

## Quick conclusion (TL;DR)

- ✅ `/api/v1/bmi/calculate` → **DUPLICATE OWNERSHIP** (legacy shim + router endpoint)
- 🔄 `/api/v1/bmi` → **OWNER: legacy** (`bmi_endpoint_v1`) → **Engine: NO** (needs shim in Commit 3)
- 🔄 `/bmi` → **OWNER: legacy** (`bmi_endpoint`) → **Engine: NO** (needs shim in Commit 3)
- ⚠️ **Duplicate found:** `/api/v1/bmi/calculate` defined in both `legacy_app.py:2196` (shim) and `app/routers/bmi.py:207` (router)

**Decision:** Keep legacy shim as owner (registered first), router endpoint is redundant but harmless (FastAPI uses first match).

---

## Route map (ownership table)

| Method | Path | Owner layer | File:line | Handler | Calls canonical engine? | Status |
|--------|------|-------------|-----------|---------|------------------------|--------|
| POST | `/api/v1/bmi/calculate` | **legacy (shim)** | `legacy_app.py:2196` | `bmi_calculate_legacy()` | ✅ YES (via `bmi_calculate_handler`) | ✅ Shim (PR-454) |
| POST | `/api/v1/bmi/calculate` | router | `app/routers/bmi.py:207` | `calculate_bmi()` | ✅ YES (via `bmi_calculate_handler`) | ⚠️ **Redundant** (same handler, but router registered later) |
| POST | `/api/v1/bmi` | **legacy** | `legacy_app.py:2139` | `bmi_endpoint_v1()` | ❌ NO (uses `bmi_core` directly) | 🔄 **Needs shim** (Commit 3) |
| POST | `/bmi` | **legacy** | `legacy_app.py:2026` | `bmi_endpoint()` | ❌ NO (uses `bmi_core` directly) | 🔄 **Needs shim** (Commit 3) |
| POST | `/api/v1/bmi/pro` | router | `app/routers/bmi_pro.py:45` | `bmi_pro()` | ❌ NO (PRO endpoint, separate) | ✅ Out of scope (PR-456) |

---

## Router registration points

### FastAPI app initialization (`legacy_app.py`)

**App factory:** `legacy_app.py` (module-level `app = FastAPI(...)`)
**Router includes (order matters for FastAPI):**

1. **Line 5443:** `app.include_router(bmi_router)`
   - Router: `app/routers/bmi.py` with `prefix="/api/v1/bmi"`
   - Registers: `POST /api/v1/bmi/calculate` (via `@router.post("/calculate")`)

2. **Line 2196:** `@app.post("/api/v1/bmi/calculate")` (legacy shim)
   - **Registered at module load time** (before `include_router` calls)
   - **FastAPI uses first match** → legacy shim takes precedence

**Conclusion:** Legacy shim (`legacy_app.py:2196`) is the **actual owner** for `/api/v1/bmi/calculate` because it's registered first (at module load). Router endpoint is redundant but harmless (never reached).

---

## Duplicate path risk assessment

### `/api/v1/bmi/calculate` — DUPLICATE FOUND

**Defined in:**
1. `legacy_app.py:2196` — `@app.post("/api/v1/bmi/calculate")` → `bmi_calculate_legacy()` (shim)
2. `app/routers/bmi.py:207` — `@router.post("/calculate")` with prefix `/api/v1/bmi` → `calculate_bmi()`

**FastAPI behavior:**
- FastAPI checks routes in **registration order**
- `@app.post` decorators execute at **module import time** (before `include_router()`)
- `app.include_router(bmi_router)` executes at **runtime** (after module load)
- **Result:** Legacy shim is checked first → it matches → router endpoint never reached

**Risk level:** 🟡 **LOW** (no functional issue, but confusing ownership)

**Decision for PR-456:**
- **Option A (recommended):** Remove router endpoint `@router.post("/calculate")` in Commit 2, keep only legacy shim
- **Option B:** Keep both (harmless but redundant)

**Recommendation:** **Option A** — cleaner ownership, one handler per path.

---

## Handler call chain analysis

### `/api/v1/bmi/calculate` (current owner: legacy shim)

```
HTTP Request
  ↓
legacy_app.py:2196 (@app.post)
  ↓
bmi_calculate_legacy() [shim]
  ↓
app/routers/bmi.py:101 (bmi_calculate_handler)
  ↓
core/bmi/engine.py:calculate_bmi_result() ✅ CANONICAL
```

**Status:** ✅ **Canonical path** (engine is source of truth)

---

### `/api/v1/bmi` (current owner: legacy)

```
HTTP Request
  ↓
legacy_app.py:2139 (@app.post)
  ↓
bmi_endpoint_v1()
  ↓
bmi_core.bmi_category() ❌ LEGACY (not canonical)
bmi_core.auto_group() ❌ LEGACY
calc_bmi() ❌ LEGACY (duplicate)
```

**Status:** ❌ **Needs shim** (Commit 3)

---

### `/bmi` (current owner: legacy)

```
HTTP Request
  ↓
legacy_app.py:2026 (@app.post)
  ↓
bmi_endpoint()
  ↓
calc_bmi() ❌ LEGACY (duplicate)
bmi_core.* ❌ LEGACY
```

**Status:** ❌ **Needs shim** (Commit 3)

---

## Legacy function usage analysis

### `calc_bmi()` (legacy_app.py:1547)

**Definition:** `legacy_app.py:1547`
**Used in:**
- `legacy_app.py:2029` — `/bmi` endpoint
- `legacy_app.py:2092` — `plan_endpoint` (not BMI-related)
- `legacy_app.py:2146` — `/api/v1/bmi` endpoint

**Canonical replacement:** `core/bmi/engine._compute_bmi()`
**Decision:** Remove after shimming `/api/v1/bmi` and `/bmi` (Commit 4)

---

### `healthy_bmi` threshold (legacy_app.py:2099)

**Definition:** `legacy_app.py:2099` — `{"min": 18.5, "max": 24.9}`
**Used in:**
- `legacy_app.py:2112` — `plan_endpoint` response
- `legacy_app.py:2127` — `plan_endpoint` response

**Canonical replacement:** Use engine thresholds (if needed)
**Decision:** Check if `plan_endpoint` is BMI-related. If not, keep for now (out of scope).

---

## Import dependencies (anti-cycle check)

### Router → Engine
- ✅ `app/routers/bmi.py:37` → `from core.bmi.engine import ...` (safe, no cycles)

### Legacy → Router
- ✅ `legacy_app.py:2208` → `from app.routers.bmi import bmi_calculate_handler` (local import, safe)

### Legacy → Core
- ✅ `legacy_app.py:67` → `from bmi_core import bmi_category` (legacy module, will be removed)

**Status:** ✅ **No import cycles detected**

---

## Follow-ups (PR-456 Commit 2+)

### Commit 2: Router cleanup
- Remove `_get_lang_from_request()` → use `core.i18n.normalize_lang`
- **Decision needed:** Remove redundant `@router.post("/calculate")` or keep?

### Commit 3: Legacy `/api/v1/bmi` → shim
- Transform `bmi_endpoint_v1()` into thin proxy to `bmi_calculate_handler`
- Use local imports (anti-cycle)

### Commit 4: Remove legacy duplicates
- Remove `calc_bmi()` after shimming endpoints
- Remove `is_athlete` parsing logic (legacy_app.py:2180-2187)
- Remove `healthy_bmi` if not used elsewhere

### Commit 5: Tests hardening
- Update `tests/test_app_bmi_v1.py` (expect shim behavior)
- Remove tests for `_get_lang_from_request` (function deleted)

### Commit 6: Guard artifacts & final polish
- Whitelist build artifacts (`.tox/`, `.mypy_cache/`, `__pycache__/`)
- PR-456 handoff documentation

---

## Security Notes

- **Route collisions:** `/api/v1/bmi/calculate` has duplicate handlers (low risk, FastAPI uses first match)
- **BMI math outside core:** `/api/v1/bmi` and `/bmi` still use `bmi_core` directly (risk of divergence)
- **Commit 1 is safe:** No code changes, only documentation

---

## Marketing & GTM

Route ownership audit = **foundation for consistent BMI behavior** across all clients (web/iOS). One source of truth (`core/bmi/engine`) → fewer bug reports, higher trust, easier ASO ("accuracy and consistency").

---

## Next Actions

1. ✅ **Commit 1 (this):** Route ownership audit (docs-only) — **DONE**
2. 🔄 **Commit 2:** Router cleanup (remove `_get_lang_from_request`, decide on router endpoint)
3. 🔄 **Commit 3:** Legacy `/api/v1/bmi` → shim
4. 🔄 **Commit 4:** Remove legacy duplicates
5. 🔄 **Commit 5:** Tests hardening
6. 🔄 **Commit 6:** Guard artifacts & final polish
