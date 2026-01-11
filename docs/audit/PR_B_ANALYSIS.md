# PR-B — Детальный анализ перед реализацией

**Дата:** 2026-01-11
**Цель:** Заменить `_require_api_key_strict` → `require_vip_tier` на 17 endpoints + тесты

---

## 1) Анализ маппинга key→tier (`api_tiers.py`)

### Test Keys
- `TEST_KEY_PRO = "test_pro_key"` → PRO tier
- `TEST_KEY_VIP = "test_vip_key"` → VIP tier (также дает PRO)
- **НЕТ `TEST_KEY_FREE`**

### Логика `_validate_api_key_tier()` (dev mode)
1. Если `api_key == TEST_KEY_VIP` → `True` (для любого tier)
2. Если `api_key == TEST_KEY_PRO` и `required_tier == PRO` → `True`
3. Если `ALLOW_ANONYMOUS_API_KEYS=true` → любой ключ → `True`
4. Иначе → `False`

### Стратегия для FREE tier в тестах
- `require_vip_tier()` — это **feature-gate**, не auth-gate
- Отсутствие ключа (`x_api_key = None`) → **403** "VIP access required"
- Неверный/недостаточный tier → **403** `"API key does not have VIP tier access. Upgrade to VIP to access this feature."`
- **Вывод:** Для FREE tier корректно использовать **пустые headers** (без `X-API-Key`), что даст 403

### Решение для FREE tier (каноничное)
**Выбранный вариант:** FREE tier = **пустые headers** (`{}`), без `X-API-Key` заголовка.

**Rationale:**
- VIP guard (`require_vip_tier`) — feature-gate: отсутствие ключа тоже даёт 403
- Это соответствует контракту: FREE tier не требует API ключа
- Не требует monkeypatch или создания `TEST_KEY_FREE`
- FREE и PRO оба получают 403 на VIP endpoints (ожидаемо)

---

## 2) Анализ паттернов guard в `vip.py`

### Паттерн A: `dependencies=[Depends(_require_api_key_strict)]` (16 endpoints)
- `/health` (GET)
- `/menu/weekly/repair` (POST)
- `/shoplist/weekly` (POST)
- `/shoplist/daily` (POST)
- `/shoplist/formats` (GET)
- `/regions` (GET)
- `/regions/{region}/search` (GET)
- `/regions/{region}/categories` (GET)
- `/regions/{region}/stores` (GET)
- `/regions/compare/{product_name}` (GET)
- `/recipes/synthesize` (POST)
- `/recipes/weekly` (POST)
- `/recipes/templates` (GET)
- `/auto-repair/weekly` (POST)
- `/auto-repair/suggestions` (POST)
- `/auto-repair/strategies` (GET)

**Замена:** `dependencies=[Depends(require_vip_tier)]` (минимальный дифф, без изменения сигнатуры)

### Паттерн B: `_api_key: str = Depends(_require_api_key_strict)` (1 endpoint)
- `/menu/weekly/plan` (POST)

**Замена:** `_vip: Annotated[str, Depends(require_vip_tier)]` (меняем сигнатуру)

---

## 3) Анализ POST endpoints: что мокать

### Echo mode (не требуют мока) — 3 endpoints
1. `/menu/weekly/repair` — возвращает echo сразу
2. `/recipes/synthesize` — возвращает echo сразу
3. `/auto-repair/suggestions` — возвращает echo сразу

**Мок не нужен:** endpoint сразу возвращает 200 с echo response.

### Требуют мока — 5 endpoints

#### 1. `/menu/weekly/plan` (POST)
- **Внутренний вызов:** `_safe_call_with_adapter("make_weekly_menu", **request_dict)`
- **Мок target:** `app.routers.vip._safe_call_with_adapter`
- **Мок возвращает:** `{"status": "success", "menu": {"days": []}}`
- **Payload:** `{"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain"}`

#### 2. `/shoplist/weekly` (POST)
- **Внутренние вызовы:** `aggregate_ingredients(request)` → `round_to_packages(aggregated)` → `format_export(shopping_list, ...)`
- **Мок target:** `app.routers.vip.format_export` (последний в цепочке)
- **Мок возвращает:** `[]` (пустой список, форматтер уже вернул готовый формат)
- **Payload:** `{"days": []}`

#### 3. `/shoplist/daily` (POST)
- **Внутренние вызовы:** аналогично `/shoplist/weekly`
- **Мок target:** `app.routers.vip.format_export`
- **Мок возвращает:** `[]`
- **Payload:** `{"day_plan": {}}`

#### 4. `/recipes/weekly` (POST)
- **Внутренний вызов:** `_safe_call_with_adapter("synthesize_recipes_for_week", week_plan, recipes_per_day)`
- **Мок target:** `app.routers.vip._safe_call_with_adapter`
- **Мок возвращает:** `{"monday": [{"recipe_id": "test", "name": "Test Recipe"}]}`
- **Payload:** `{"week_plan": {}, "recipes_per_day": 1}`

#### 5. `/auto-repair/weekly` (POST)
- **Внутренние вызовы:** `auto_repair_week_plan(...)` или `engine.auto_repair_week_plan(...)`
- **Мок target:** `app.routers.vip.auto_repair_week_plan` (функция, не engine)
- **Мок возвращает:** `{"status": "repaired", "repaired_plan": {}, "original_plan": {}, "changes_made": [], "remaining_gaps": []}`
- **Payload:** `{"week_plan": {}, "targets": {}}`

---

## 4) GET endpoints: path params

### С path params (4 endpoints)
1. `/regions/{region}/search` → `region="es"`, query param `query="test"`
2. `/regions/{region}/categories` → `region="es"`
3. `/regions/{region}/stores` → `region="es"`
4. `/regions/compare/{product_name}` → `product_name="milk"`

### Без path params (5 endpoints)
- `/health`
- `/shoplist/formats`
- `/regions`
- `/recipes/templates`
- `/auto-repair/strategies`

---

## 5) Тест-фикстуры (требуемые)

### `headers_for_tier(tier: str) -> dict[str, str]`
```python
@pytest.fixture
def headers_for_tier():
    """Return headers dict for tier.

    For FREE tier, returns empty dict (no API key header) - FREE = no key required.
    For PRO/VIP, returns X-API-Key header with respective test key.
    """
    def _get_headers(tier: str) -> dict[str, str]:
        if tier == "VIP":
            return {"X-API-Key": TEST_KEY_VIP}
        elif tier == "PRO":
            return {"X-API-Key": TEST_KEY_PRO}
        elif tier == "FREE":
            return {}  # No API key header - FREE tier doesn't require a key
        else:
            raise ValueError(f"Unknown tier: {tier}")
    return _get_headers
```

**Rationale:**
- FREE tier = пустые headers (без `X-API-Key`) → 403 на VIP endpoints
- PRO tier = `TEST_KEY_PRO` → 403 на VIP endpoints
- VIP tier = `TEST_KEY_VIP` → 2xx на VIP endpoints
- Не требует monkeypatch или создания `TEST_KEY_FREE`

---

## 6) Минимальные payloads для POST (явные, без автогенерации)

| Endpoint | Payload |
|----------|---------|
| `/menu/weekly/plan` | `{"sex": "male", "age": 30, "height_cm": 175, "weight_kg": 70, "activity": "moderate", "goal": "maintain"}` |
| `/menu/weekly/repair` | `{"week_plan": {}}` |
| `/shoplist/weekly` | `{"days": []}` |
| `/shoplist/daily` | `{"day_plan": {}}` |
| `/recipes/synthesize` | `{"ingredients": []}` |
| `/recipes/weekly` | `{"week_plan": {}, "recipes_per_day": 1}` |
| `/auto-repair/weekly` | `{"week_plan": {}, "targets": {}}` |
| `/auto-repair/suggestions` | `{"week_plan": {}, "targets": {}}` |

---

## 7) Порядок реализации (канонический)

### Commit 1: Guard replacement
1. Добавить import: `from app.middleware.api_tiers import require_vip_tier`
2. Заменить все `dependencies=[Depends(_require_api_key_strict)]` → `dependencies=[Depends(require_vip_tier)]`
3. Заменить `_api_key: str = Depends(_require_api_key_strict)` → `_vip: Annotated[str, Depends(require_vip_tier)]`
4. Добавить `from typing import Annotated` если нужно

### Commit 2: Cleanup
1. Проверить: `rg "_require_api_key_strict" app/routers/vip.py` → должно быть 0
2. Удалить функцию `_require_api_key_strict()` (lines 403-434)
3. Проверить: `rg '_require_api_key|_get_configured_api_key|_extract_api_key'` → если используется только в удаленной функции, удалить

### Commit 3: Tests
1. Создать `tests/test_vip_guard_consistency.py`
2. Добавить fixture `headers_for_tier` (FREE = пустые headers, PRO/VIP = с ключом)
3. Параметризованные тесты для GET (9 endpoints)
4. Параметризованные тесты для POST (8 endpoints)
5. Моки для POST endpoints, требующих моков (5 endpoints)

---

## 8) Критические моменты

### A) FREE tier strategy
- **Решение:** FREE tier = **пустые headers** (`{}`), без `X-API-Key` заголовка
- **Rationale:** VIP guard (`require_vip_tier`) — feature-gate: отсутствие ключа тоже даёт 403, что корректно для FREE tier
- **Ожидаемое поведение:** FREE и PRO оба получают 403 на VIP endpoints (это правильно, так как VIP = feature-gate)

### B) Dependency vs signature pattern
- **Паттерн A (dependencies):** Меняем только dependency, сигнатура не меняется
- **Паттерн B (signature):** Меняем параметр в сигнатуре
- **Важно:** Не смешивать паттерны — используем то, что уже есть

### C) POST payload validation
- **Риск:** `{}` может пройти JSON валидацию, но упасть на KeyError внутри endpoint
- **Решение:** Использовать явные минимальные payloads (не автогенерация)

### D) Моки для стабильности
- **Цель:** VIP POST = строго 2xx
- **Стратегия:** Мокать самый верхний вызов в endpoint (или последний в цепочке)
- **Важно:** Возвращаемая структура должна соответствовать ожиданиям endpoint

---

## 9) DoD Checklist

- [ ] Все 17 endpoints используют `require_vip_tier`
- [ ] `_require_api_key_strict` удален (если orphan)
- [ ] Тесты: FREE/PRO → 403, VIP → 2xx
- [ ] Моки для POST endpoints (5 endpoints)
- [ ] CI green (lint/typecheck/tests/diff-cov)
- [ ] Нет breaking changes (response shape для VIP не меняется)

---

## 10) Monkeypatch targets (точные)

| Endpoint | Monkeypatch Target | Mock Return |
|----------|-------------------|-------------|
| `/menu/weekly/plan` | `app.routers.vip._safe_call_with_adapter` | `{"status": "success", "menu": {"days": []}}` |
| `/shoplist/weekly` | `app.routers.vip.format_export` | `[]` |
| `/shoplist/daily` | `app.routers.vip.format_export` | `[]` |
| `/recipes/weekly` | `app.routers.vip._safe_call_with_adapter` | `{"monday": [{"recipe_id": "test", "name": "Test"}]}` |
| `/auto-repair/weekly` | `app.routers.vip.auto_repair_week_plan` | `{"status": "repaired", "repaired_plan": {}, "original_plan": {}, "changes_made": [], "remaining_gaps": []}` |

---

## Готово к реализации

Анализ завершен. Все 17 endpoints классифицированы, паттерны замены определены, моки идентифицированы.
