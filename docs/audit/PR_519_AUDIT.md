# PR-519 — Backend PRO/Premium Alias Audit

**Date:** 2026-01-12
**Status:** 🔄 Audit Phase (Qoder)
**Goal:** Map canonical PRO endpoints and deprecated premium aliases for thin proxy implementation

---

## 📋 Context from Previous PRs (Status as of 2026-01-12)

### PR-510 (legacy_app audit) — PR #515
**Status:** ✅ Docs-only PR (merged 2026-01-11)
- **Realized:** Documentation and analysis only
- **Not realized:** Code extraction (deferred to PR-511+)
- **Key finding:** `legacy_app.py` contains orchestration logic that should be extracted

### PR-517 (VIP Guard Consistency) — PR #517
**Status:** ✅ Merged (2026-01-11)
- **Realized:**
  - VIP endpoints covered by guard suite use `require_vip_tier()` consistently (legacy deprecated `/api/v1/vip/weekly-plan` is a known exception)
  - OpenAPI artifacts updated (Security scheme)
  - Tests updated (vip_headers fixture)
  - AGENTS.md updated (Security() pattern rule)

### PR-518 (VIP Guard Matrix + Test Hygiene) — PR #518
**Status:** ✅ Merged (2026-01-12)
- **Realized:**
  - VIP guard matrix created (`tests/test_vip_tier_guard_matrix.py`) — 51 tests
  - Env cleanup fixed (`VIP_MODULE_ENABLED` cleaned in teardown)
  - sys.modules mutations replaced with `monkeypatch.setattr()` (no importlib.reload)
  - AGENTS.md updated (dependency override, sys.modules, env cleanup rules)
  - Separate "no API key" test added (`test_vip_no_api_key_403.py`)

### FRONTEND_BACKEND_ALIGNMENT_AUDIT
**Status:** ❌ Not started
- **Realized:** None (all tasks marked `[ ]`)
- **Note:** This is a separate frontend-backend alignment PR (not included in recent PRs)

---

## 🔍 A. Inventory (Facts Only)

### 1. Where are PRO endpoints defined?

#### Canonical PRO Endpoints

| Endpoint | Method | Location | Handler Function | Guard |
|----------|--------|----------|------------------|-------|
| `/api/v1/pro/nutrition/targets` | POST | `app/routers/pro_nutrition_contracts.py` | `pro_nutrition_targets()` | `require_pro_tier` |
| `/api/v1/pro/nutrition/plate` | POST | `app/routers/pro_nutrition_contracts.py` | `pro_nutrition_plate()` | `require_pro_tier` |
| `/api/v1/pro/nutrition/daily` | GET | `app/routers/pro.py` | `get_daily_nutrition()` | `require_pro_tier` |
| `/api/v1/pro/meal/weekly` | POST | `app/routers/pro.py` | `generate_week_plan()` | `require_pro_tier` |

**Registration:**
- `app/routers/pro_registration.py` — `register_pro_routes()` function
- `legacy_app.py:1080` — calls `_register_pro_routes(app)`

**OpenAPI visibility (important fact):**
- OpenAPI generation runs in schema-only mode (`PULSEPLATE_OPENAPI=1`, `APP_ENV=test`, `ENVIRONMENT=test`).
- In schema-only mode `app/routers/pro_registration.py` skips importing/including `app.routers.pro` entirely.
- Result:
  - `/api/v1/pro/nutrition/targets` and `/api/v1/pro/nutrition/plate` are included (registered from `app/main.py` bootstrap).
  - `/api/v1/pro/nutrition/daily` and `/api/v1/pro/meal/weekly` exist at runtime, but remain **absent** from `frontend/src/api/openapi.json` until PR-520 remediation.

---

### 2. Where are premium endpoints?

#### Premium Endpoints in `legacy_app.py`

| Endpoint | Method | Line | Current Behavior | Feature Flag | Guard |
|----------|--------|------|------------------|--------------|-------|
| `/api/v1/premium/targets` | POST | - | Deprecated thin proxy → `/api/v1/pro/nutrition/targets` | None | `_get_api_key_dynamic` |
| `/api/v1/premium/plate` | POST | - | Deprecated thin proxy → `/api/v1/pro/nutrition/plate` | `FEATURE_PREMIUM_NUTRITION` | `_get_api_key_dynamic` |
| `/api/v1/premium/plan/week` | POST | - | Legacy endpoint (VIP-dependent; contract mismatch) | `VIP_MODULE_ENABLED` | `_get_api_key_dynamic` |

**Status:**
- ✅ `/api/v1/premium/targets` — deprecated thin proxy to canonical PRO targets
- ✅ `/api/v1/premium/plate` — deprecated thin proxy to canonical PRO plate (PlateRequest → PlateResponse)
- ⚠️ `/api/v1/premium/plan/week` — deprecated legacy tail; migrate clients to `week-flexible`

---

### 3. Method and request format for canonical daily

**Canonical:** `GET /api/v1/pro/nutrition/daily`

**Request format:** Query parameters (not POST body)
- `date` (required): ISO 8601 format (YYYY-MM-DD)
- `sex` (required): `"female"` | `"male"`
- `age` (required): int (10-100)
- `height_cm` (required): float (100-250)
- `weight_kg` (required): float (30-300)
- `activity` (optional): `"sedentary"` | `"light"` | `"moderate"` | `"active"` | `"very_active"` (default: `"moderate"`)
- `goal` (optional): `"loss"` | `"maintain"` | `"gain"` (default: `"maintain"`)
- `lang` (optional): `"en"` | `"ru"` | `"es"` (default: `"en"`)

**Response model:** `DailyNutritionResponse`
- `date: str`
- `segments: List[NutritionSegmentData]` (vegetables, protein, carbs, fats)
- `total_progress: float` (0.0-1.0)
- `daily_goals: DailyGoals`

**Code evidence:** `app/routers/pro.py:365-418`

---

### 4. Response shape for canonical endpoints

#### `/api/v1/pro/nutrition/targets` (POST)

**Location:** `app/routers/pro_nutrition_contracts.py`

**Current state:**
- Canonical endpoint exists: `POST /api/v1/pro/nutrition/targets`
- Implementation delegates to `legacy_app._generate_who_targets_response()` (temporary implementation dependency)

**Guard:** `require_pro_tier` (canonical PRO tier guard)

**Request model:** `WHOTargetsRequest` (from `legacy_app.py`)
- Profile fields: `sex`, `age`, `height_cm`, `weight_kg`, `activity`, `goal`
- Optional: `bodyfat`, `lang`, `life_stage`

**Response model:** `WHOTargetsResponse`
- `kcal_daily: float`
- `macros: Dict[str, float]` (protein_g, carbs_g, fat_g)
- `water_ml: float`
- `priority_micros: Dict[str, float]`
- `activity_weekly: Dict[str, float]` (optional)
- `calculation_date: str`
- `warnings: List[Dict[str, str]]`

**Handler:** `_generate_who_targets_response()` in `legacy_app.py:4523` (calls `estimate_targets_minimal()` from `app/routers/pro.py:184`)

---

#### `/api/v1/pro/nutrition/daily` (GET)

**Request:** Query parameters (see section 3)

**Response model:** `DailyNutritionResponse`
- `date: str`
- `segments: List[NutritionSegmentData]`
  - `name: str` (e.g., "Vegetables")
  - `current_value: float` (servings consumed, currently 0.0)
  - `target_value: float` (target servings)
  - `percentage: float` (0-100)
  - `color: str` (e.g., "green")
  - `icon: str` (e.g., "leaf.fill")
- `total_progress: float` (0.0-1.0)
- `daily_goals: DailyGoals`
  - `vegetables: float`
  - `protein: float`
  - `carbs: float`
  - `fats: float`

**Handler:** `get_daily_nutrition()` in `app/routers/pro.py:396`

---

#### `/api/v1/pro/meal/weekly` (POST)

**Request model:** `WeekPlanRequest`
- Mode A: `targets: Optional[TargetsIn]` (complete targets dict)
- Mode B: Profile fields (fallback)
  - `sex: Optional[Literal["female", "male"]]`
  - `age: Optional[int]` (10-90)
  - `height_cm: Optional[int]` (100-220)
  - `weight_kg: Optional[int]` (30-300)
  - `activity: Optional[Literal[...]]` (default: `"moderate"`)
  - `goal: Optional[Literal["loss", "maintain", "gain"]]` (default: `"maintain"`)
- `diet_flags: List[str]` (default: `[]`)
- `lang: Language` (default: `"en"`)

**Response model:** `WeekPlanResponse`
- `daily_menus: List[Dict]`
- `weekly_coverage: Dict[str, float]`
- `shopping_list: Dict[str, float]`
- `total_cost: float`
- `adherence_score: float`

**Handler:** `generate_week_plan()` in `app/routers/pro.py:262`

---

## 🔍 B. Premium Aliases Current State

### `/api/v1/premium/targets` (POST)

**Location:** `legacy_app.py:4685`

**Current implementation:**
```python
@app.post("/api/v1/premium/targets", ...)
async def api_who_targets(payload: Dict[str, Any] = Body(...)):
    # Calls estimate_targets_minimal() directly
    # Returns same structure as PRO endpoint
```

**Status:** ✅ **Already thin proxy** (delegates to `estimate_targets_minimal()`)

**Action (PR-519):**
- Decide canonical PRO contract for targets:
  - Option A (recommended): introduce `/api/v1/pro/nutrition/targets` (POST) and make this endpoint delegate.
  - Option B: explicitly declare `/api/v1/premium/targets` as canonical (but then it is not a deprecated alias; conflicts with namespace policy).

---

### `/api/v1/premium/plate` (POST)

**Location:** `legacy_app.py:3980`

**Current implementation:**
- Feature flag: `FEATURE_PREMIUM_NUTRITION`
- Method: **POST** (not GET)
- Request: JSON body with profile fields
- **Calculates plate internally** (duplicates PRO daily logic)

**Problem:** 
- Canonical PRO daily (`/api/v1/pro/nutrition/daily`) returns `DailyNutritionResponse` (segments/total_progress).
- Premium plate returns `PlateResponse` (kcal/macros/portions/layout/meals/day_micros).
- These are **different response models** → `/api/v1/premium/plate` cannot be a thin proxy to `/api/v1/pro/nutrition/daily` without a breaking contract change.

**Decision needed:**
- Option A (recommended): create a canonical PRO endpoint with the **same contract** as `PlateRequest/PlateResponse`
  (e.g. `POST /api/v1/pro/nutrition/plate`) and make `/api/v1/premium/plate` a thin deprecated proxy to it.
- Option B: redefine canonical daily as `DailyNutritionResponse` and migrate frontend off `PlateResponse` (breaking).

---

### `/api/v1/premium/plan/week` (POST)

**Location:** `legacy_app.py:4706`

**Current implementation:**
- Feature flag: `VIP_MODULE_ENABLED`
- **Calls VIP module** (`make_weekly_menu` from `app.routers.vip`)
- **Wrong tier** — should call PRO, not VIP

**Problem:**
- Premium namespace should delegate to **PRO**, not VIP
- VIP is separate tier (higher than PRO)
- Response model mismatch:
  - `/api/v1/premium/plan/week` returns `WeeklyMenuResponse` (includes `week_summary`)
  - `/api/v1/pro/meal/weekly` returns `WeekPlanResponse` (no `week_summary`)

**Related fact:** There is already a deprecated premium-week endpoint implemented as a router:
- `POST /api/v1/premium/plan/week-flexible` in `app/routers/premium_week.py` (deprecated, PRO tier)
- This one is already aligned with the `WeekPlanRequest/WeekPlanResponse` shape used by `app/routers/pro.py`

**Decision:**
- Canonical weekly contract for PRO must be explicitly chosen:
  - Option A (recommended): keep `/api/v1/pro/meal/weekly` as canonical and make `/api/v1/premium/plan/week` a deprecated proxy that delegates + formats response into `WeeklyMenuResponse` (compat shim).
  - Option B: deprecate `/api/v1/premium/plan/week` in favor of `/api/v1/premium/plan/week-flexible` (requires frontend/client migration).

---

## 🔍 C. Risks/Invariants

### Anti-duplication
- ✅ `/api/v1/premium/targets` — deprecated thin proxy to `/api/v1/pro/nutrition/targets` (no duplication)
- ✅ `/api/v1/premium/plate` — deprecated thin proxy to `/api/v1/pro/nutrition/plate` (no duplication)
- ⚠️ `/api/v1/premium/plan/week` — deprecated legacy tail (VIP-dependent; contract mismatch); migrate clients to `week-flexible`

### Guards (intentional divergence)
- Canonical PRO endpoints use `require_pro_tier` (tier guard).
- Deprecated premium aliases remain legacy-guarded via `_get_api_key_dynamic` (API_KEY equality / dev-only leniency).
- Premium aliases are **not required** to be auth-equivalent to canonical PRO routes in PR-519.
  Guard alignment is a separate product/infra decision (do not “fix” this accidentally in PR-520/521).

### Dependency direction (temporary)
- `app/routers/pro_nutrition_contracts.py` delegates to `legacy_app` implementations via late imports.
- This is a temporary dependency to stabilize contracts quickly; extraction into `app/services/*` or `core/*` is out of scope for PR-519.

### OpenAPI determinism
- Must not break schema-only mode (`PULSEPLATE_OPENAPI=1`)
- Must not change router registration order
- Namespace policy conflict to resolve in PR-519/PR-520:
  - Repo policy says deprecated `/api/v1/premium/*` aliases should be **hidden from OpenAPI by default**
    (to prevent frontend generating types for the wrong paths).
  - Today, OpenAPI includes `/api/v1/premium/*` while excluding most canonical PRO endpoints due to schema-only mode.
  - Plan: first make canonical PRO endpoints OpenAPI-safe + included; then hide `/api/v1/premium/*`.

### Feature flags
- Canonical PRO endpoints: always available (gated by PRO tier only)
- Premium aliases: may be gated by feature flags, but **better**: remove feature flags, keep only deprecated wrapper

### Frontend compatibility
- Minimal diff required
- No "improvements" — only thin proxy delegation
- Maintain same response shape (for backward compatibility)

---

## 📊 D. Audit Artifacts

### Table: Canonical PRO Endpoints

| Canonical Path | Method | Handler Function | Request Model | Response Model | Line |
|----------------|--------|------------------|---------------|----------------|------|
| `/api/v1/pro/nutrition/targets` | POST | `pro_nutrition_targets()` | `WHOTargetsRequest` | `WHOTargetsResponse` | `app/routers/pro_nutrition_contracts.py` |
| `/api/v1/pro/nutrition/plate` | POST | `pro_nutrition_plate()` | `PlateRequest` | `PlateResponse` | `app/routers/pro_nutrition_contracts.py` |
| `/api/v1/pro/nutrition/daily` | GET | `get_daily_nutrition()` | Query params (date, sex, age, height_cm, weight_kg, activity, goal, lang) | `DailyNutritionResponse` | `app/routers/pro.py:396` |
| `/api/v1/pro/meal/weekly` | POST | `generate_week_plan()` | `WeekPlanRequest` | `WeekPlanResponse` | `app/routers/pro.py:262` |

---

### Table: Premium Aliases → Should Do

| Premium Alias | Method | Current Behavior | Should Do | Status |
|---------------|--------|------------------|-----------|--------|
| `/api/v1/premium/targets` | POST | Deprecated thin proxy → `pro/nutrition/targets` | ✅ Keep thin proxy, keep legacy guard | ✅ OK |
| `/api/v1/premium/plate` | POST | Deprecated thin proxy → `pro/nutrition/plate` | ✅ Keep thin proxy, keep legacy guard | ✅ OK |
| `/api/v1/premium/plan/week` | POST | VIP-dependent legacy tail | ✅ Deprecate + migrate to `week-flexible` | ⚠️ Deferred |

---

### Decision on `plate` (POST → GET conversion)

**Problem:** Premium plate (`PlateResponse`) and PRO daily (`DailyNutritionResponse`) are different contracts.

**Solution (Option A — recommended):**
1. Keep `/api/v1/premium/plate` as-is for clients (POST + `PlateResponse`)
2. Create canonical `POST /api/v1/pro/nutrition/plate` with the same request/response models
3. Make `/api/v1/premium/plate` a deprecated thin proxy to `/api/v1/pro/nutrition/plate`
4. After frontend migration, hide `/api/v1/premium/*` from OpenAPI

**Implementation:**
```python
@app.post("/api/v1/premium/plate", deprecated=True, ...)
async def api_premium_plate(req: PlateRequest):
    return await api_pro_plate(req)  # delegate to canonical PRO plate handler
```

**Alternative (Option B — breaking change):**
- Change premium plate to GET
- Frontend must migrate immediately
- **Not recommended** (breaks backward compatibility)

---

### Parity Tests Plan

**Parity tests must compare like-for-like contracts (same request/response models).**
Proposed staging:

**Phase 1 (PR-519):** add canonical handlers + parity tests for what is actually proxyable.
**Phase 2 (PR-520):** OpenAPI visibility gates (canonical visible, deprecated hidden).

**Implemented (PR-519):**
- `tests/test_pro_premium_contract_parity.py`:
  - parity: `/api/v1/premium/targets` ↔ `/api/v1/pro/nutrition/targets`
  - parity: `/api/v1/premium/plate` ↔ `/api/v1/pro/nutrition/plate`
  - OpenAPI: `/api/v1/premium/plan/week-flexible` is `deprecated: true`

**Explicit non-goal (PR-519):**
- No parity for `/api/v1/premium/plan/week` ↔ PRO weekly (contract mismatch + VIP dependency).

---

## 🎯 E. Implementation (PR-519)

### Implemented

- Added canonical PRO contract routes:
  - `POST /api/v1/pro/nutrition/targets`
  - `POST /api/v1/pro/nutrition/plate`
- Converted deprecated premium aliases into thin proxies:
  - `POST /api/v1/premium/targets` → delegates to canonical PRO targets
  - `POST /api/v1/premium/plate` → delegates to canonical PRO plate
- Kept `/api/v1/premium/plan/week` as deprecated legacy tail; sanctioned bridge remains `week-flexible`.

---

### Notes

- The canonical PRO routes are registered from `app/main.py` bootstrap to ensure they are visible in schema-only OpenAPI mode.
- PRO contract implementation currently delegates to `legacy_app` internals (temporary).

---

## 📝 F. DoD Checklist (PR-519)

- [x] Canonical PRO targets route exists: `POST /api/v1/pro/nutrition/targets`
- [x] Canonical PRO plate route exists: `POST /api/v1/pro/nutrition/plate`
- [x] Deprecated premium targets delegates to canonical PRO targets (legacy-guarded)
- [x] Deprecated premium plate delegates to canonical PRO plate (legacy-guarded)
- [x] Parity tests added for targets+plate (same request/response models)
- [x] Guard divergence documented (premium aliases are legacy-guarded by design)
- [ ] `make verify` passes

---

## 🔗 G. Related Documents

- `docs/audit/FRONTEND_BACKEND_ALIGNMENT_AUDIT.md` — frontend migration plan (PR-521)
- `docs/contracts/PRODUCT_TIER_MAP.md` — tier mapping contract
- `docs/contracts/PRODUCT_TIER_REMEDIATION_PLAN.md` — remediation roadmap
- `app/routers/pro.py` — canonical PRO endpoints
- `app/routers/pro_registration.py` — PRO router registration

---

---

## 📋 H. Critical Finding (Resolved): Canonical `pro/nutrition/targets`

**Status:** ✅ Resolved in PR-519 implementation

**Resolution:**
- Added canonical `POST /api/v1/pro/nutrition/targets`.
- Converted `POST /api/v1/premium/targets` into a deprecated thin proxy.

---

**Last updated:** 2026-01-12
**Next step:** Run `make verify` before claiming readiness.
