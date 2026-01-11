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

### Проблема для FREE key
- `"invalid_key"` → `_validate_api_key_tier("invalid_key", VIP)` вернет `False`
- `require_vip_tier()` сначала проверяет наличие ключа (403 если None), затем tier (403 если не VIP)
- **Вывод:** `"invalid_key"` даст 403, но это будет "tier denial", не "unknown key" — это ок для тестов

### Решение для FREE key
**Вариант A (рекомендуемый):** Использовать `TEST_KEY_PRO` для FREE тестов, но с monkeypatch:
- Monkeypatch `_validate_api_key_tier` чтобы `TEST_KEY_PRO` с `required_tier=VIP` возвращал `False` (это уже так)
- Для FREE tier: использовать любой ключ, который НЕ `TEST_KEY_VIP` и НЕ `TEST_KEY_PRO`
- Или создать `TEST_KEY_FREE = "test_free_key"` и monkeypatch маппинг

**Выбранный вариант:** Использовать `TEST_KEY_PRO` для FREE тестов (он уже не дает VIP доступ), но лучше создать явный `TEST_KEY_FREE` через monkeypatch для ясности.

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

### `api_key_for_tier(tier: str) -> str`
```python
@pytest.fixture
def api_key_for_tier(monkeypatch: pytest.MonkeyPatch):
    """Return API key for tier, with monkeypatch for FREE tier."""
    def _get_key(tier: str) -> str:
        if tier == "VIP":
            return TEST_KEY_VIP
        elif tier == "PRO":
            return TEST_KEY_PRO
        elif tier == "FREE":
            # Create a valid FREE key via monkeypatch
            TEST_KEY_FREE = "test_free_key"
            # Monkeypatch _validate_api_key_tier to recognize FREE key
            original = app.middleware.api_tiers._validate_api_key_tier
            def patched_validate(key: str, required: SubscriptionTier) -> bool:
                if key == TEST_KEY_FREE and required == SubscriptionTier.VIP:
                    return False  # FREE key doesn't grant VIP
                return original(key, required)
            monkeypatch.setattr("app.middleware.api_tiers._validate_api_key_tier", patched_validate)
            return TEST_KEY_FREE
        else:
            raise ValueError(f"Unknown tier: {tier}")
    return _get_key
```

**Упрощение:** Можно использовать `TEST_KEY_PRO` для FREE тестов (он уже не дает VIP), но лучше явный FREE key для ясности.

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
3. Проверить: `rg "_require_api_key\(|_get_configured_api_key|_extract_api_key"` → если используется только в удаленной функции, удалить

### Commit 3: Tests
1. Создать `tests/test_vip_guard_consistency.py`
2. Добавить fixture `api_key_for_tier`
3. Параметризованные тесты для GET (9 endpoints)
4. Параметризованные тесты для POST (8 endpoints)
5. Моки для POST endpoints, требующих моков (5 endpoints)

---

## 8) Критические моменты

### A) FREE key strategy
- **Проблема:** Нет `TEST_KEY_FREE`, `"invalid_key"` может дать неожиданное поведение
- **Решение:** Использовать `TEST_KEY_PRO` для FREE тестов (он уже не дает VIP) или создать `TEST_KEY_FREE` через monkeypatch
- **Выбор:** Использовать `TEST_KEY_PRO` для FREE (проще, работает)

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
