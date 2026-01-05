# PR-457=A Audit Questionnaire: Legacy BMI Helpers Cleanup

**Date:** 2025-01-XX  
**Status:** Pre-implementation audit  
**Scope:** Remove legacy BMI helpers from request-path, migrate `/plan` to canonical handler

---

## Контекст (обязателен в ответе)

- ✅ PR-456 уже смержен.
- ✅ BMI канон: вся логика только в `core/bmi/*`.
- ✅ PR-457 = **A**: убрать legacy BMI helpers из request-path, **без изменения поведения/контрактов**.
- ✅ Языки: RU/EN/ES.
- ✅ Acceptance Criteria фиксированы:
  - **AC1:** `/plan` больше не вызывает `calc_bmi/normalize_flags/bmi_category` (и любые legacy BMI helpers), а **делегирует в canonical handler/engine**.
  - **AC2:** есть тест, который **доказывает делегацию** + guard "no legacy bmi helpers in request-path".

---

## 1) Inventory (доказательно)

### 1.1. Таблица всех legacy BMI helpers

| Helper | Location | Call sites (file:line) | Request-path? | Action | Notes |
|--------|----------|------------------------|---------------|--------|-------|
| `calc_bmi(weight_kg, height_m)` | `legacy_app.py:1567` | `legacy_app.py:2160` (`plan_endpoint`) | ✅ Yes | **Replace** | Used only in `/plan`. Replace with canonical handler call. |
| `normalize_flags(gender, pregnant, athlete)` | `legacy_app.py:1571` | `legacy_app.py:2159` (`plan_endpoint`) | ✅ Yes | **Replace** | Used only in `/plan`. Canonical handler normalizes flags internally. |
| `bmi_category(bmi, lang, age, group)` | `bmi_core.py:71` | `legacy_app.py:2164` (`plan_endpoint`) | ✅ Yes | **Replace** | Used only in `/plan`. Canonical engine returns category. |
| `waist_risk(waist_cm, gender_male, lang)` | `legacy_app.py:1604` | None | ❌ No | **Delete** | Dead code. Not used in any request-path. |
| `calc_bmi(weight_kg, height_m)` | `app/routers/bmi_pro.py:16` | `app/routers/bmi_pro.py:20+` (Pro endpoints) | ✅ Yes | **Keep** | Pro endpoints scope (not legacy migration). Local helper acceptable. |

### 1.2. Детализация по каждому helper

**`calc_bmi` (legacy_app.py:1567):**
- **Definition:** `def calc_bmi(weight_kg: StrictFloat, height_m: float) -> float: return round(float(weight_kg) / (height_m**2), 1)`
- **Call site:** `legacy_app.py:2160` in `plan_endpoint`
- **Request-path:** ✅ Yes (`/plan`)
- **Action:** Replace with canonical handler (`bmi_calculate_handler` → `core/bmi/engine.calculate_bmi_result`)

**`normalize_flags` (legacy_app.py:1571):**
- **Definition:** `def normalize_flags(gender, pregnant, athlete) -> Dict[str, bool]`
- **Call site:** `legacy_app.py:2159` in `plan_endpoint`
- **Request-path:** ✅ Yes (`/plan`)
- **Action:** Replace with canonical handler normalization (handler normalizes `pregnant`/`athlete` flags internally)

**`bmi_category` (bmi_core.py:71):**
- **Definition:** `def bmi_category(bmi, lang, age, group) -> str`
- **Call site:** `legacy_app.py:2164` in `plan_endpoint` (via `from bmi_core import bmi_category`)
- **Request-path:** ✅ Yes (`/plan`)
- **Action:** Replace with canonical engine result (`BMICalculateResult.category`)

**`waist_risk` (legacy_app.py:1604):**
- **Definition:** `def waist_risk(waist_cm, gender_male, lang) -> str`
- **Call sites:** None (dead code)
- **Request-path:** ❌ No
- **Action:** Delete (dead code cleanup)

---

## 2) Request-path Map (1 экран)

### 2.1. Все endpoints, относящиеся к BMI/планам

| Path | File:line | Owner | Delegates to canonical? | Violations |
|------|-----------|-------|-------------------------|------------|
| `/bmi` | `legacy_app.py:2047` | `bmi_endpoint()` | ✅ Yes | None |
| `/api/v1/bmi` | `legacy_app.py:2207` | `bmi_endpoint_v1()` | ✅ Yes | None |
| `/api/v1/bmi/calculate` | `app/routers/bmi.py:207` | `calculate_bmi()` | ✅ Yes | None |
| `/plan` | `legacy_app.py:2156` | `plan_endpoint()` | ❌ **NO** | **VIOLATION:** Uses `calc_bmi`, `normalize_flags`, `bmi_category` |

### 2.2. Где нарушается канон

**`/plan` endpoint (legacy_app.py:2156-2204):**
- ❌ **Violation 1:** Calls `calc_bmi(req.weight_kg, req.height_m)` (line 2160)
- ❌ **Violation 2:** Calls `normalize_flags(req.gender, req.pregnant, req.athlete)` (line 2159)
- ❌ **Violation 3:** Calls `bmi_category(bmi, req.lang, req.age, ...)` (line 2164)

**Expected:** `/plan` should delegate to `bmi_calculate_handler` (similar to `/bmi` and `/api/v1/bmi` shims).

---

## 3) Plan for `/plan` migration (минимальный, без изменения поведения)

### 3.1. Как сделать `/plan` shim'ом

**Canonical handler to call:**
- `app.routers.bmi.bmi_calculate_handler` (same as `/bmi` and `/api/v1/bmi` shims)

**Migration steps:**
1. Convert `BMIRequest` (height in meters) to `BMICalculateRequest` (height in centimeters):
   ```python
   shim_payload = {
       "weight_kg": req.weight_kg,
       "height_cm": round(float(req.height_m) * 100.0, 1),  # Convert meters to cm
       "age": req.age,
       "gender": req.gender,
       "pregnant": req.pregnant,
       "athlete": req.athlete,
       "waist_cm": req.waist_cm,
       "lang": str(req.lang),
   }
   ```

2. Call canonical handler:
   ```python
   from app.routers.bmi import bmi_calculate_handler
   canonical_result = await bmi_calculate_handler(BMICalculateRequest.model_validate(shim_payload))
   ```

3. Extract BMI and category from canonical result:
   ```python
   bmi = canonical_result["bmi"]
   category = canonical_result["category"]  # Already None for pregnant/teen/child (canonical behavior)
   ```

4. Build legacy response format (preserve contract):
   ```python
   base = {
       "summary": "Персональный план (MVP)" if req.lang == "ru" else "Personal plan (MVP)",
       "bmi": bmi,
       "category": category,  # None for pregnant/teen/child (canonical)
       "premium": bool(req.premium),
       "next_steps": [...],  # Same as before
       "healthy_bmi": {"min": 18.5, "max": 24.9},  # Same as before
       "action": "...",  # Same as before
   }
   if req.premium:
       base["premium_reco"] = [...]  # Same as before
   ```

**Handling `category=None` for pregnant/teen/child:**
- ✅ **Canonical engine already returns `category=None`** for pregnant/teen/child groups (see `core/bmi/engine.py:416` → `_bmi_category`).
- ✅ **Legacy `/plan` already handles `category=None`** (line 2161-2164: `category = None if flags["is_pregnant"] else bmi_category(...)`).
- ✅ **No change needed** — canonical behavior matches legacy behavior.

**RU/EN/ES support:**
- ✅ Canonical handler normalizes `lang` via `core.i18n.normalize_lang`.
- ✅ Response text (`summary`, `next_steps`, `action`, `premium_reco`) already localized in `/plan` (lines 2169-2202).
- ✅ No change needed — existing localization logic preserved.

### 3.2. Контрактные поля `/plan` (нельзя менять)

**Source:** `legacy_app.py:2169-2204` and tests (`tests/test_app_comprehensive_97_final.py:107-220`)

| Field | Type | Required | Source | Notes |
|-------|------|----------|--------|-------|
| `summary` | `str` | ✅ Yes | `legacy_app.py:2171,2190` | Localized: "Персональный план (MVP)" (RU) or "Personal plan (MVP)" (EN) |
| `bmi` | `float` | ✅ Yes | `legacy_app.py:2172,2191` | From canonical handler |
| `category` | `str \| None` | ✅ Yes | `legacy_app.py:2173,2192` | `None` for pregnant/teen/child (canonical) |
| `premium` | `bool` | ✅ Yes | `legacy_app.py:2174,2193` | From `req.premium` |
| `next_steps` | `List[str]` | ✅ Yes | `legacy_app.py:2175-2179,2194` | Localized array (RU/EN) |
| `healthy_bmi` | `Dict[str, float]` | ✅ Yes | `legacy_app.py:2180,2195` | `{"min": 18.5, "max": 24.9}` |
| `action` | `str` | ✅ Yes | `legacy_app.py:2181,2196` | Localized string (RU/EN) |
| `premium_reco` | `List[str]` | ❌ No (if `premium=True`) | `legacy_app.py:2184-2187,2199-2202` | Localized array (RU/EN), only if `premium=True` |

**Test evidence:**
- `tests/test_app_comprehensive_97_final.py:107-129` — RU language, `premium=False`
- `tests/test_app_comprehensive_97_final.py:131-152` — RU language, `premium=True`
- `tests/test_app_comprehensive_97_final.py:153-175` — EN language, `premium=False`
- `tests/test_app_comprehensive_97_final.py:176-197` — EN language, `premium=True`
- `tests/test_app_comprehensive_97_final.py:198-220` — Pregnant case (`category=None`)

---

## 4) Tests (обязательный дизайн)

### 4.1. Минимальный набор тестов для PR-457=A

| Test name | Type (unit/http) | What it proves | File | Key asserts |
|-----------|------------------|---------------|------|-------------|
| `test_plan_endpoint_uses_canonical_handler_via_shim` | HTTP | `/plan` delegates to canonical handler | `tests/test_legacy_bmi_shims.py` | Monkeypatch `calculate_bmi_result` → verify fixed result flows through |
| `test_plan_endpoint_preserves_contract` | HTTP | Response contract unchanged (regression) | `tests/test_legacy_bmi_shims.py` | All contract fields present, types match, localized text correct |
| `test_plan_endpoint_category_none_for_pregnant` | HTTP | `category=None` for pregnant (canonical behavior) | `tests/test_legacy_bmi_shims.py` | `category is None` when `pregnant=True` |
| `test_no_legacy_bmi_helpers_in_request_path` | Unit (AST/grep) | Guard: no legacy helpers in request-path | `tests/test_import_hygiene_guard.py` | Scan endpoints → verify no calls to `calc_bmi/normalize_flags/bmi_category` (except Pro endpoints) |

### 4.2. Как доказать делегацию (без importlib/sys.modules)

**Предпочтительный вариант (monkeypatch):**
```python
def test_plan_endpoint_uses_canonical_handler_via_shim(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    RU: Доказательный тест: /plan использует engine через handler (shim работает).
    EN: Proof test: /plan uses engine via handler (shim works).
    """
    import app.routers.bmi as bmi_router
    
    # Fixed result to verify it "flows through" the shim
    fixed_result = BMICalculateResult(
        bmi=22.5,
        category="normal",
        group="general",
        group_display="General",
        interpretation="Your BMI is within the normal range.",
        wht_ratio=None,
        waist_risk=None,
        notes=(),
        age_band="adult",
    )
    
    def _fixed_engine(**_: Any) -> BMICalculateResult:
        return fixed_result
    
    monkeypatch.setattr(bmi_router, "calculate_bmi_result", _fixed_engine)
    
    payload = {
        "weight_kg": 70.0,
        "height_m": 1.75,
        "age": 30,
        "gender": "male",
        "pregnant": "no",
        "athlete": "no",
        "lang": "en",
        "premium": False,
    }
    
    resp = client.post("/plan", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["bmi"] == 22.5  # Proves canonical handler was called
    assert data["category"] == "normal"  # Proves canonical category was used
```

**Запасной вариант (import tracing):**
- Use `unittest.mock.patch` to wrap `bmi_calculate_handler` and verify it was called with correct arguments.
- Less preferred (more fragile), but works if monkeypatch doesn't work.

---

## 5) Guard design (anti-regression)

### 5.1. Как реализовать guard "no legacy helpers in request-path"

**Approach: AST-based scanning (preferred):**
- Use `ast` module to parse `legacy_app.py` and find all `@app.post/get/put/delete` decorators.
- For each endpoint function, scan for calls to `calc_bmi`, `normalize_flags`, `bmi_category`, `waist_risk`.
- Whitelist: `app/routers/bmi_pro.py` (Pro endpoints scope).

**Implementation:**
```python
def test_no_legacy_bmi_helpers_in_request_path() -> None:
    """
    RU: Guard: ни один request-path endpoint не использует legacy BMI helpers.
    EN: Guard: no request-path endpoint uses legacy BMI helpers.
    """
    import ast
    import inspect
    
    # Forbidden function names
    FORBIDDEN = {"calc_bmi", "normalize_flags", "bmi_category", "waist_risk"}
    
    # Whitelist (Pro endpoints)
    WHITELIST = {"app/routers/bmi_pro.py"}
    
    # Scan legacy_app.py
    with open("legacy_app.py", "r") as f:
        tree = ast.parse(f.read())
    
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if it's an endpoint (has @app.post/get decorator)
            if any(
                isinstance(d, ast.Call) and
                isinstance(d.func, ast.Attribute) and
                d.func.attr in {"post", "get", "put", "delete"}
                for d in node.decorator_list
            ):
                # Scan function body for forbidden calls
                for call in ast.walk(node):
                    if isinstance(call, ast.Call):
                        if isinstance(call.func, ast.Name) and call.func.id in FORBIDDEN:
                            violations.append((node.name, call.func.id, call.lineno))
    
    assert not violations, f"Legacy helpers found in request-path: {violations}"
```

**Alternative (grep-based, simpler):**
```python
def test_no_legacy_bmi_helpers_in_request_path() -> None:
    """Guard: no legacy BMI helpers in request-path endpoints."""
    import subprocess
    
    # Find all endpoint definitions
    result = subprocess.run(
        ["rg", "-n", r"@app\.(post|get|put|delete)\(.*\)", "legacy_app.py"],
        capture_output=True,
        text=True,
    )
    
    # For each endpoint, check for forbidden calls
    # (Simpler but less precise than AST)
```

**Where to store forbidden symbols:**
- Hardcode in test: `FORBIDDEN = {"calc_bmi", "normalize_flags", "bmi_category", "waist_risk"}`
- Or: `tests/test_import_hygiene_guard.py` (alongside other guard tests)

**Avoiding false positives:**
- Whitelist Pro endpoints: `app/routers/bmi_pro.py` (has local `calc_bmi`, acceptable)
- Only scan `legacy_app.py` (not `core/bmi/*` or `app/routers/bmi.py`)

### 5.2. Пример: какие строки/паттерны считаем нарушением

**Violation patterns:**
```python
# ❌ VIOLATION: Direct call to legacy helper
bmi = calc_bmi(req.weight_kg, req.height_m)

# ❌ VIOLATION: Direct call to legacy helper
flags = normalize_flags(req.gender, req.pregnant, req.athlete)

# ❌ VIOLATION: Direct call to legacy helper
category = bmi_category(bmi, req.lang, req.age, group)

# ❌ VIOLATION: Dead code call (if used)
risk = waist_risk(waist_cm, gender_male, lang)
```

**Acceptable patterns:**
```python
# ✅ OK: Call to canonical handler
canonical_result = await bmi_calculate_handler(canonical_req)

# ✅ OK: Extract from canonical result
bmi = canonical_result["bmi"]
category = canonical_result["category"]

# ✅ OK: Pro endpoints (whitelisted)
# app/routers/bmi_pro.py
def calc_bmi(...):  # Local helper, acceptable
```

---

## 6) Diff-coverage plan (минимально)

### 6.1. Какие новые строки появятся в PR-457

**File: `legacy_app.py` (plan_endpoint migration):**
- Lines ~2158-2204: Replace legacy helper calls with canonical handler shim
  - New: Import `bmi_calculate_handler`, `BMICalculateRequest`
  - New: Convert `BMIRequest` → `BMICalculateRequest` (height_m → height_cm)
  - New: Call `bmi_calculate_handler(canonical_req)`
  - New: Extract `bmi` and `category` from canonical result
  - Removed: `calc_bmi()`, `normalize_flags()`, `bmi_category()` calls

**File: `legacy_app.py` (dead code removal):**
- Lines 1567-1568: Delete `calc_bmi()` function
- Lines 1571-1601: Delete `normalize_flags()` function
- Lines 1604-1612: Delete `waist_risk()` function
- Line 67: Remove `from bmi_core import bmi_category` import

**File: `tests/test_legacy_bmi_shims.py` (new tests):**
- New: `test_plan_endpoint_uses_canonical_handler_via_shim`
- New: `test_plan_endpoint_preserves_contract`
- New: `test_plan_endpoint_category_none_for_pregnant`

**File: `tests/test_import_hygiene_guard.py` (guard test):**
- New: `test_no_legacy_bmi_helpers_in_request_path`

### 6.2. Какими тестами будут покрыты (ветка → тест)

| Branch/Path | Test | Coverage |
|-------------|------|----------|
| `/plan` shim delegation | `test_plan_endpoint_uses_canonical_handler_via_shim` | ✅ Calls canonical handler, extracts BMI/category |
| `/plan` contract preservation | `test_plan_endpoint_preserves_contract` | ✅ All contract fields present, types match |
| `/plan` category=None for pregnant | `test_plan_endpoint_category_none_for_pregnant` | ✅ `category is None` when `pregnant=True` |
| Guard: no legacy helpers | `test_no_legacy_bmi_helpers_in_request_path` | ✅ AST/grep scan → no violations |
| Dead code removal | Existing tests (regression) | ✅ No test failures after deletion |

---

## 7) Risks & Non-goals (строго)

### 7.1. Топ-3 риска PR-457

**Risk 1: Backward compatibility (contract drift)**
- **Impact:** High
- **Mitigation:** 
  - Preserve all contract fields (`summary`, `bmi`, `category`, `premium`, `next_steps`, `healthy_bmi`, `action`, `premium_reco`)
  - Run existing regression tests (`test_plan_endpoint_*` in `test_app_comprehensive_97_final.py`)
  - Verify `category=None` behavior for pregnant/teen/child (canonical matches legacy)

**Risk 2: Hidden usage (indirect calls)**
- **Impact:** Medium
- **Mitigation:**
  - AST-based guard test scans all endpoints
  - Whitelist Pro endpoints (`app/routers/bmi_pro.py`)
  - Verify no other files import `bmi_core.bmi_category` (grep check)

**Risk 3: i18n localization (RU/EN/ES)**
- **Impact:** Low
- **Mitigation:**
  - Canonical handler normalizes `lang` via `core.i18n.normalize_lang`
  - Response text (`summary`, `next_steps`, `action`, `premium_reco`) already localized in `/plan` (no change)
  - Test with RU/EN/ES languages

### 7.2. Что точно не делаем в PR-457=A

1. ❌ Не меняем контракт `/plan` (все поля остаются прежними)
2. ❌ Не меняем локализацию (RU/EN/ES логика не трогается)
3. ❌ Не трогаем Pro endpoints (`app/routers/bmi_pro.py`)
4. ❌ Не удаляем `bmi_core.py` (может использоваться где-то еще, проверить в PR-458)
5. ❌ Не добавляем новые фичи (только миграция + cleanup)

### 7.3. Задачи для PR-458 и PR-459

**PR-458 (после PR-457):**
1. ⚠️ **`bmi_core.py` используется в других местах** (не только в `legacy_app.py`):
   - `core/bmi/risk.py:17` → `from bmi_core import compute_wht_ratio`
   - `bmi_visualization.py:12` → `from bmi_core import auto_group, bmi_category, group_display_name`
   - Множество тестов используют `bmi_core` функции
2. **Action:** Провести полный аудит использования `bmi_core.py`:
   - Определить, какие функции можно мигрировать в `core/bmi/*`
   - Определить, какие функции можно удалить (legacy)
   - Мигрировать/удалить по результатам аудита

**PR-459 (опционально):**
1. Рефакторинг `/plan` endpoint (вынести локализацию в `core/i18n`, если нужно)
2. Улучшение тестов (более детальные проверки контракта)

---

## 8) Commit Plan (обязательный, 4–6 коммитов)

### 1. `test(pr-457): add plan endpoint delegation proof test`

**Intent:** Add proof test to verify `/plan` delegates to canonical handler (before migration).

**What NOT included:**
- No code changes to `/plan` endpoint
- No deletion of legacy helpers

**Tests touched:**
- `tests/test_legacy_bmi_shims.py` — new test `test_plan_endpoint_uses_canonical_handler_via_shim`

**Risk:** Low (test-only, no production code changes)

---

### 2. `refactor(pr-457): migrate /plan endpoint to canonical handler`

**Intent:** Replace legacy helper calls in `/plan` with canonical handler shim.

**What NOT included:**
- No deletion of legacy helpers (yet)
- No guard test (yet)

**Tests touched:**
- Existing regression tests should pass (no changes needed)

**Risk:** Medium (request-path change, but contract preserved)

---

### 3. `test(pr-457): add plan endpoint contract preservation tests`

**Intent:** Add regression tests to verify `/plan` contract is preserved after migration.

**What NOT included:**
- No code changes

**Tests touched:**
- `tests/test_legacy_bmi_shims.py` — new tests `test_plan_endpoint_preserves_contract`, `test_plan_endpoint_category_none_for_pregnant`

**Risk:** Low (test-only)

---

### 4. `refactor(pr-457): remove legacy BMI helpers (calc_bmi, normalize_flags, waist_risk)`

**Intent:** Delete dead code: `calc_bmi()`, `normalize_flags()`, `waist_risk()` from `legacy_app.py`.

**What NOT included:**
- No removal of `bmi_core.py` (check in PR-458)
- No guard test (yet)

**Tests touched:**
- Existing tests should pass (no direct calls to deleted functions)

**Risk:** Low (dead code removal, no request-path impact)

---

### 5. `test(pr-457): add guard test for no legacy BMI helpers in request-path`

**Intent:** Add guard test to prevent reintroduction of legacy BMI helpers in request-path.

**What NOT included:**
- No code changes

**Tests touched:**
- `tests/test_import_hygiene_guard.py` — new test `test_no_legacy_bmi_helpers_in_request_path`

**Risk:** Low (test-only)

---

### 6. `refactor(pr-457): remove bmi_category import from legacy_app.py`

**Intent:** Remove unused import `from bmi_core import bmi_category` (no longer used after migration).

**What NOT included:**
- No deletion of `bmi_core.py` (check in PR-458)

**Tests touched:**
- Existing tests should pass

**Risk:** Low (unused import removal)

---

## 9) Final check (коротко)

### AC1 (делегация /plan)

**Status:** ⚠️ **FAIL** (до PR-457)

**Что остаётся сделать:**
1. ✅ Мигрировать `/plan` endpoint к `bmi_calculate_handler` (Commit 2)
2. ✅ Удалить вызовы `calc_bmi`, `normalize_flags`, `bmi_category` из `/plan` (Commit 2)
3. ✅ Убедиться, что контракт сохранён (Commit 3, тесты)

**После PR-457:** ✅ **PASS**

---

### AC2 (tests: delegation proof + guard)

**Status:** ⚠️ **FAIL** (до PR-457)

**Что остаётся сделать:**
1. ✅ Добавить `test_plan_endpoint_uses_canonical_handler_via_shim` (Commit 1)
2. ✅ Добавить `test_no_legacy_bmi_helpers_in_request_path` (Commit 5)
3. ✅ Убедиться, что guard test зелёный после миграции

**После PR-457:** ✅ **PASS**

---

## Summary

**PR-457=A Scope:**
- ✅ Migrate `/plan` endpoint to canonical handler
- ✅ Remove legacy helpers: `calc_bmi`, `normalize_flags`, `waist_risk`
- ✅ Remove unused import: `from bmi_core import bmi_category`
- ✅ Add delegation proof test
- ✅ Add guard test for "no legacy helpers in request-path"

**Expected outcome:**
- ✅ All request-path endpoints delegate to canonical handler
- ✅ No legacy BMI helpers in request-path
- ✅ Contract preserved (backward compatible)
- ✅ Guard test prevents regression

**Next steps:**
- PR-458: Check if `bmi_core.py` can be deleted
- PR-459 (optional): Further refactoring/improvements

---

**Audit completed:** 2025-01-XX  
**Ready for implementation:** ✅ Yes

