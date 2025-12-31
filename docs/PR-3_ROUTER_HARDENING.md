# PR-3: Router Layer Hardening

## 🎯 Цель

Цементировать все error paths в VIP shoplist router, чтобы:
- Все ошибки возвращали контролируемые, предсказуемые ответы
- Никаких 500 из-за маппинга/валидации
- Четкая таблица 422/404/401/403 поведения

## 📋 Что уже покрыто тестами

### ✅ Pydantic Validation (422)

1. **Invalid unit** → 422 (валидируется на уровне DTO, не доходит до `_map_unit`)
2. **Invalid rounding** → 422 (валидируется на уровне DTO, не доходит до `_map_rounding`)
3. **Invalid form** → 422 (валидируется на уровне DTO, не доходит до `_map_form`)
4. **min_packs=0** → 422 (Pydantic `ge=1` constraint)
5. **Empty food_id** → 422 (Pydantic `min_length=1`)
6. **Negative quantity** → 422 (Pydantic `ge=0`)

### ✅ Feature Flag & Auth (404/403)

7. **VIP module disabled** → 404 (`require_vip_module_enabled`)
8. **Missing API key** → 403 (legacy_app handling)
9. **Invalid API key tier** → 403 (PRO key for VIP endpoint)

### ✅ Edge Cases (200)

10. **Empty items list** → 200 (valid, returns empty result)
11. **Missing items field** → 200 (defaults to `[]`)

## 🔧 Что можно улучшить в роутере (опционально)

### 1. Улучшить сообщения об ошибках маппинга

**Текущее состояние:**
- `_map_unit`, `_map_rounding`, `_map_form` уже возвращают 422 с понятными сообщениями
- Но эти функции **не вызываются** для invalid literals (Pydantic валидирует раньше)

**Рекомендация:**
- Оставить как есть (Pydantic валидация достаточна)
- Или добавить кастомные валидаторы в DTO для более дружелюбных сообщений

### 2. Улучшить обработку пустых payload

**Текущее состояние:**
- `items: list[ShoplistItemDTO] = Field(default_factory=list)` → пустой список валиден
- Это **правильное поведение** (edge case обработан)

**Рекомендация:**
- Оставить как есть (200 с пустым результатом — валидный ответ)

### 3. Добавить валидацию на уровне бизнес-логики

**Текущее состояние:**
- Contract-check для packed items без rules → 500 (уже есть в PR-1)
- Все маппинги защищены try/except → 422

**Рекомендация:**
- Все уже покрыто ✅

## 📊 Таблица Error Codes

| Сценарий | Status Code | Источник | Тест |
|----------|-------------|----------|------|
| Invalid unit (DTO) | 422 | Pydantic | `test_generate_invalid_unit_returns_422` |
| Invalid rounding (DTO) | 422 | Pydantic | `test_generate_invalid_rounding_returns_422` |
| Invalid form (DTO) | 422 | Pydantic | `test_generate_invalid_form_returns_422` |
| min_packs=0 | 422 | Pydantic | `test_generate_min_packs_zero_returns_422` |
| Empty food_id | 422 | Pydantic | `test_generate_empty_food_id_returns_422` |
| Negative quantity | 422 | Pydantic | `test_generate_negative_quantity_returns_422` |
| VIP module disabled | 404 | Router | `test_generate_vip_module_disabled_returns_404` |
| Missing API key | 403 | legacy_app | `test_generate_missing_api_key_returns_403` |
| Invalid API key tier | 403 | legacy_app | `test_generate_invalid_api_key_tier_returns_403` |
| Packed item without rule | 500 | Router contract-check | `test_generate_raises_when_packed_item_missing_rule` (PR-1) |
| Empty items list | 200 | Valid edge case | `test_generate_empty_items_list_returns_200` |
| Missing items field | 200 | Default factory | `test_generate_missing_items_field_returns_200_with_empty_result` |

## ✅ Готовность к мерджу

- [x] Все error paths покрыты тестами
- [x] Нет неконтролируемых 500 (кроме contract violation, который явно обработан)
- [x] Pydantic валидация работает корректно
- [x] Feature flag и auth проверки работают
- [x] Edge cases обработаны

## 📝 Коммит-месседж

```text
test(vip): add router hardening tests for error paths (PR-3)

- Add comprehensive negative test cases (422/404/403)
- Cover Pydantic validation errors
- Cover feature flag and auth errors
- Cover edge cases (empty lists)
- Document error code matrix
```
