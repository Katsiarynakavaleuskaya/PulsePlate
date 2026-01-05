# 🧭 PR-6 HANDOFF — PulsePlate / VIP Shoplist Track

**Topic:** Region/Catalog Adapter (mock-first) — enrichment без изменений core
**Date:** 31 Dec 2025
**Status:** Ready for implementation

---

## ✅ Предусловия (где мы сейчас)

- **PR-4 merged**: `/generate`, `/daily`, `/weekly` выровнены по gating+mapping+builder, explainability+analytics консистентны.
- **PR-5 merged**: contract freeze + OpenAPI annotations + iOS DTO/mapping docs.
- **Engine-first принцип подтверждён**: core shoplist engine остаётся **pure/offline/deterministic**.

---

## 🎯 Цель PR-6

Сделать **adapter-layer enrichment** (mock-first), который добавляет к результату shoplist **каталожные атрибуты** (SKU/price/aisle/pack labeling) **без изменений core** и **без реальных внешних источников**.

### Почему это отдельным PR

- Региональные цены/магазины — отдельная ось сложности.
- Нам нужен **стабильный интерфейс** для будущих Carrefour/Walmart loaders.
- Frontend/iOS должен получить понятный контракт "enrichment optional".

---

## 📦 PR-6 Контракт (public API surface)

### 1) Новая опциональная структура Enrichment

**Важно:** enrichment **не обязателен** и **не влияет на расчёт packs**.

Добавляем в response (предпочтительно backward-compatible):

#### Option A (рекомендовано): `packed[].catalog` / `unpacked[].catalog`

```json
{
  "packed": [
    {
      "food_id": "carrot",
      "packs": 1,
      "reasons": ["min_packs", "rounding"],
      "catalog": {
        "sku": "CRF-ES-000123",
        "store_id": "carrefour_es",
        "region_id": "es",
        "pack_label": "500 g bag",
        "aisle": "Vegetables",
        "price": { "value": "1.29", "currency": "EUR" }
      }
    }
  ]
}
```

#### Option B: top-level `catalog_map` (не рекомендую — усложняет фронт)

```json
"catalog_map": { "carrot": { ... } }
```

**Decision:** выбираем **Option A**, потому что:

- UI проще (не нужно join по food_id)
- не ломает engine-first (это adapter-only attach)
- backward compatible: поле optional

### 2) Входные параметры для enrichment

PR-6 только интерфейс (mock-first):

- `region_id` (optional)
- `store_id` (optional)

Можно:

- добавить как query параметры к endpoints, **или**
- добавить в request body на уровне daily/weekly/generate.

**Decision:** минимальный риск — **query params**:

- `?region_id=es&store_id=carrefour_es`
- если не переданы → enrichment пропускаем (или default mock).

### 3) Behavior rules

- Если catalog найден → добавляем `catalog`
- Если catalog не найден → `catalog` отсутствует (или `null`, но лучше отсутствует)
- Никаких ошибок для пользователя из-за отсутствия каталога (fail-soft)
- Расчёт packs/overage не меняется

---

## 🗂️ Файлы PR-6 (минимальный набор)

### 1) Сервисный слой

**NEW** `app/services/catalog_adapter.py`

Содержимое:

- протокол/интерфейс `CatalogProvider`
- mock provider `MockCatalogProvider`
- функция `enrich_shoplist_response(response, region_id, store_id) -> response`

**Никаких DB/HTTP**. Только in-memory dict.

### 2) DTO / Schemas

Обновить `app/schemas/vip_shoplist.py`:

- добавить `CatalogInfoDTO` (optional)
- расширить `PackedLineDTO` и `UnpackedLineDTO`:

  - `catalog: CatalogInfoDTO | None = None`

**NEW** (если нужно) `app/schemas/catalog.py`:

- `MoneyDTO(value: Decimal, currency: CurrencyDTO)`
- `CurrencyDTO`: `EUR`, `USD`, `BYN`, `RUB`

### 3) Router wiring

Обновить `app/routers/vip_shoplist.py`:

- добавить query params: `region_id: str | None`, `store_id: str | None`
- после `build_shoplist_response(...)` — вызвать `enrich_shoplist_response(...)`
- apply для:

  - `/generate`
  - `/daily`
  - `/weekly`
  - `/preview` (если preview возвращает те же lines)

### 4) Docs

**NEW** `docs/RegionCatalog_Adapter.md`

- что enrichment optional
- какие поля добавляем
- как будет расширяться (PR-7: loaders)

---

## ✅ Тест-кейсы PR-6 (минимум, но железо)

### 1) Unit tests на adapter

**NEW** `tests/test_catalog_adapter_mock.py`

Кейсы:

1. `test_enrich_adds_catalog_when_food_id_found`
2. `test_enrich_is_fail_soft_when_not_found`
3. `test_enrich_does_not_mutate_core_fields`

   - packs/reasons/analytics должны совпасть "до/после enrichment"

### 2) Router integration tests (только 1–2)

**NEW** `tests/test_vip_shoplist_enrichment_optional.py`

Кейсы:

1. `test_generate_success_without_region_store_has_no_catalog_fields`
2. `test_generate_success_with_region_store_attaches_catalog`

Опционально:

- для weekly: проверить, что enrichment применяется ко всем days (1 тест)

---

## 🧱 Инварианты (не нарушаем ни при каких условиях)

### Engine-first invariants

- core engine не меняем
- deterministic output (при одинаковых входах)
- Decimal-only
- no I/O, no env, no time/random

### Adapter invariants

- enrichment **не влияет** на packs/analytics/reasons
- enrichment fail-soft: нет каталога → не ошибка
- gating остаётся прежним (VIP module + tier)

### OpenAPI invariants

- `catalog` поле optional
- примеры в Swagger обновить (минимум один)
- iOS DTO нужно обновить в docs (но можно **в PR-7**, если хотим сохранить PR маленьким)

---

## 🔐 Security Notes (PR-6)

- Никаких реальных store API ключей
- Никаких внешних HTTP вызовов
- Enrichment не должен раскрывать PII
- Не допускаем "catalog injection" в unsafe fields (всё статическое/валидируемое)

---

## 📣 Marketing & GTM (PR-6)

- Это основа "региональных цен" (ES/US) — ключевая фича VIP.
- Даже mock enrichment уже даёт UI-возможности:

  - "aisle grouping"
  - "price estimate"
  - "pack label" (человеческий вид)
- Подготовка к PR-7: Carrefour/Walmart loaders без ломки контракта.

---

## 🧾 Decision Log (фиксируем)

1. Enrichment — **adapter-only**, core не трогаем.
2. `catalog` прикрепляется **inline** к lines (`packed/unpacked`) как optional.
3. Вход для enrichment — query params `region_id/store_id` (минимальный риск).
4. Mock-first: никакого API/DB.

---

## ✅ Next Actions (как стартовать PR-6)

1. Создать ветку: `feat/region-catalog-adapter-mock`
2. Добавить `CatalogInfoDTO` + optional `catalog` поля в vip_shoplist schemas
3. Добавить `app/services/catalog_adapter.py` с mock provider
4. Подключить enrichment в router после build response
5. Написать 2 тест файла (unit + 1 integration)
6. Обновить docs `docs/RegionCatalog_Adapter.md`
7. Проверить CI (coverage не падает)

---

## 📋 Implementation Checklist

- [ ] Create `app/schemas/catalog.py` with `MoneyDTO`, `CurrencyDTO`
- [ ] Add `CatalogInfoDTO` to `app/schemas/vip_shoplist.py`
- [ ] Extend `PackedLineDTO` and `UnpackedLineDTO` with optional `catalog` field
- [ ] Create `app/services/catalog_adapter.py` with `CatalogProvider` protocol
- [ ] Implement `MockCatalogProvider` with in-memory catalog data
- [ ] Implement `enrich_shoplist_response()` function
- [ ] Update `app/routers/vip_shoplist.py` to accept `region_id` and `store_id` query params
- [ ] Wire enrichment into `/generate`, `/daily`, `/weekly` endpoints
- [ ] Write unit tests in `tests/test_catalog_adapter_mock.py`
- [ ] Write integration tests in `tests/test_vip_shoplist_enrichment_optional.py`
- [ ] Create `docs/RegionCatalog_Adapter.md` documentation
- [ ] Update OpenAPI examples in Swagger
- [ ] Verify backward compatibility (no catalog = no catalog field)
- [ ] Verify coverage ≥ 97%
- [ ] Verify all tests pass

---

## 🔗 Related PRs

- **PR-3**: Router hardening (gating, error handling)
- **PR-4**: Daily/Weekly endpoint standardization
- **PR-5**: Contract freeze + OpenAPI alignment + iOS DTOs
- **PR-7** (future): Real catalog loaders (Carrefour/Walmart)

---

**Ready for implementation** ✅
