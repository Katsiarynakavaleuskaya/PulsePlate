# PR-4: Daily/Weekly Shoplist Hardening

## 🎯 Цель

Привести endpoints `/daily` и `/weekly` к тому же стандарту, что и `/generate`:
- Единый gating (VIP_MODULE_ENABLED, VIP tier)
- Единый mapping (invalid enum → 422)
- Единый response contract (reasons + analytics)

## 📋 Изменения

### Router Refactoring (`app/routers/vip_shoplist.py`)

**Вынесены общие функции:**
- `_map_dto_to_engine_specs()` — маппинг DTO items → core IngredientSpec
- `_map_dto_to_engine_rules()` — маппинг DTO packaging rules → core PackageRule
- `_build_shoplist_response()` — сборка ответа с explainability + analytics

**Реализованы endpoints:**
- `POST /api/v1/vip/shoplist/daily` — генерация списка покупок на день
- `POST /api/v1/vip/shoplist/weekly` — генерация списка покупок на неделю

**Контракт:**
- ✅ Same gating: `require_vip_module_enabled()` + `require_vip_tier()`
- ✅ Same mapping: invalid enum → `HTTP_422_UNPROCESSABLE_CONTENT`
- ✅ Same response: `packed`/`unpacked` + `reasons`/`reason` + `analytics`

### Schemas (`app/schemas/vip_shoplist.py`)

**Добавлены DTOs:**
- `ShoplistDailyRequest` (alias для `ShoplistGenerateRequest`)
- `ShoplistWeeklyRequest` — список дней
- `ShoplistWeeklyResponse` — список ответов по дням

### Tests

**Новые тестовые файлы:**
- `tests/test_vip_shoplist_daily.py` — тесты для `/daily`
- `tests/test_vip_shoplist_weekly.py` — тесты для `/weekly`
- `tests/test_vip_shoplist_invalid_enum_422.py` — параметризованный тест на 422 для обоих endpoints

**Обновлены старые тесты:**
- `test_vip_coverage_simple.py`
- `test_vip_coverage_precise.py`
- `test_vip_coverage_fixed.py`
- `test_vip_coverage_targeted.py`
- `test_vip_coverage_working.py`

Все обновлены под новый формат API.

### Fixes

- ✅ Заменены устаревшие константы: `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT`
- ✅ Исправлены deprecation warnings

## ✅ Проверки

- [x] Все тесты проходят (33 passed)
- [x] Coverage для `app/routers/vip_shoplist.py`: **100%**
- [x] Нет warnings
- [x] Pre-commit hooks прошли
- [x] Docker build test прошёл

## 🔗 Связанные PRs

- PR-3: Router Hardening (базовая инфраструктура)
- PR-5: Contract freeze + Docs (следующий шаг)

## 📝 Примеры использования

### Daily

```bash
curl -X POST "https://api.example.com/api/v1/vip/shoplist/daily" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"}
    ],
    "packaging_rules": [
      {
        "food_id": "chicken",
        "pack_size": {"value": "500", "unit": "G"},
        "rounding": "CEIL",
        "min_packs": 1
      }
    ]
  }'
```

### Weekly

```bash
curl -X POST "https://api.example.com/api/v1/vip/shoplist/weekly" \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "days": [
      {
        "items": [
          {"food_id": "chicken", "qty": {"value": "1200", "unit": "G"}, "form": "RAW"}
        ],
        "packaging_rules": [
          {
            "food_id": "chicken",
            "pack_size": {"value": "500", "unit": "G"},
            "rounding": "CEIL",
            "min_packs": 1
          }
        ]
      }
    ]
  }'
```

## 🏗️ Архитектура

**Принцип:** Engine-first, adapter-only.

- ✅ Core (`core/shoplist_engine`) остаётся чистым, deterministic, offline
- ✅ Router (`app/routers/vip_shoplist`) — только wiring + DTO mapping
- ✅ Explainability, analytics — только в adapter layer

PR-4 эту философию **не нарушил**.
