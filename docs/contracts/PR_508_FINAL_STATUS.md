# PR-508: Финальный статус и следующий PR

**Дата:** 2026-01-10
**Статус:** ✅ Детерминизм достигнут, готово к коммитам

---

## ✅ Детерминизм подтверждён

### Результаты проверки

```bash
$ make openapi && shasum ... && make openapi && shasum ...
a7694fd69b11faf8158e03f4b06c7374b6c9c5711bd76bfc58db4ea96c0de4bd  openapi.json
d98e7411692ab92e455b50741c199c2d54642092a9fb663894fbed76b70428a0  schema.ts
a7694fd69b11faf8158e03f4b06c7374b6c9c5711bd76bfc58db4ea96c0de4bd  openapi.json
d98e7411692ab92e455b50741c199c2d54642092a9fb663894fbed76b70428a0  schema.ts
```

**Оба файла стабильны между запусками.**

### Тест детерминизма

```bash
$ pytest -xvs tests/test_openapi_determinism.py
============================== 1 passed in 3.82s ===============================
```

**Тест проходит.**

---

## 🔧 Применённые исправления

### 1. Режим генерации OpenAPI без SQLAlchemy

**Проблема:** SQLAlchemy модели загружались дважды при генерации OpenAPI, вызывая ошибку "Table already defined".

**Решение:**
- `scripts/generate_openapi.py`: устанавливает `PULSEPLATE_OPENAPI=1` **перед** импортом app
- `legacy_app.py`: условный импорт роутеров (`premium_week`, `pro`), которые импортируют SQLAlchemy модели

**Код:**
```python
# scripts/generate_openapi.py
os.environ["PULSEPLATE_OPENAPI"] = "1"  # BEFORE importing app
from app.main import app

# legacy_app.py
OPENAPI_MODE = os.getenv("PULSEPLATE_OPENAPI") == "1"
if not OPENAPI_MODE:
    from app.routers.premium_week import router as premium_week_router
    from app.routers.pro import router as pro_router
else:
    premium_week_router = None
    pro_router = None
```

### 2. Убрана нормализация schema.ts

**Проблема:** `normalize_schema_ts.py` ломал синтаксис TypeScript файла.

**Решение:** Удалён из пайплайна, используется `--alphabetize` в `openapi-typescript`.

### 3. Зафиксирована версия openapi-typescript

**Проблема:** Плавающая версия (`^7.9.1`) могла давать разные результаты.

**Решение:** `"openapi-typescript": "7.9.1"` (без `^`) + `--alphabetize` флаг.

### 4. Рекурсивная нормализация OpenAPI

**Проблема:** Порядок ключей в словарях/списках был недетерминированным.

**Решение:** `normalize_openapi_schema()` рекурсивно сортирует все структуры.

---

## 📋 Текущее состояние файлов

### `scripts/generate_openapi.py` (строки 80-121)

```python
def main() -> int:
    # Enable schema-only mode to avoid SQLAlchemy model double-loading
    os.environ["PULSEPLATE_OPENAPI"] = "1"

    # Hard pin environment and feature flags
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("FEATURE_PREMIUM_WEEK_ENABLED", "false")
    os.environ.setdefault("FEATURE_BMI_PRO_ENABLED", "false")
    os.environ.setdefault("BUSINESS_MODULE_ENABLED", "false")
    os.environ.setdefault("ENABLE_TEST_ROUTES", "1")

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

    # PULSEPLATE_OPENAPI=1 must be set BEFORE importing app
    from app.main import app

    schema = app.openapi()
    schema = normalize_openapi_schema(schema)

    out_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0
```

### `Makefile` (строки 293-301)

```makefile
openapi: ## Generate OpenAPI schema and regenerate FE types (deterministic)
	PYTHONPATH=. python3 scripts/generate_openapi.py
	cd frontend && npm install --no-audit --no-fund && npm run generate-types

openapi-check: ## Verify OpenAPI + generated FE types are committed (fails on diff)
	PYTHONPATH=. python3 scripts/generate_openapi.py
	cd frontend && npm install --no-audit --no-fund && npm run generate-types
	git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts
```

**Единственный путь генерации:** `scripts/generate_openapi.py` → `npm run generate-types`

---

## 🚀 Следующий PR: VIP/Product schemas (PR-509)

### Проблема

В `schema.ts` многие VIP/product endpoints имеют:
```typescript
"application/json": { [key: string]: unknown }
```

Это означает, что в роутерах используется `dict[str, Any]` вместо Pydantic `response_model`.

### План PR-509

1. **Найти endpoints с `unknown` типами:**
   ```bash
   grep -n "unknown" frontend/src/api/schema.ts | grep -E "vip|product|region|store"
   ```

2. **Создать Pydantic схемы:**
   - `app/schemas/vip_product.py`:
     - `RegionDTO`
     - `StoreDTO`
     - `CategoryDTO`
     - `RegionProductDTO`
     - `ProductSearchResponse`

3. **Обновить роутеры:**
   - Заменить `dict[str, Any]` на `response_model=RegionProductDTO`
   - Убедиться, что все поля типизированы

4. **Регенерировать:**
   ```bash
   make openapi
   ```

5. **Проверить:**
   - `schema.ts` больше не содержит `unknown` для этих endpoints
   - Типы стали usable для фронтенда

### Оценка

- **Файлов:** ~5-7 (схемы + роутеры)
- **Сложность:** Средняя (нужно понять структуру данных)
- **Зависимости:** PR-508 должен быть merged

---

## ✅ Готово к коммитам

Все три источника дрейфа устранены:
1. ✅ SQLAlchemy double-loading — исправлено через `PULSEPLATE_OPENAPI=1`
2. ✅ `normalize_schema_ts.py` — удалён из пайплайна
3. ✅ Версия `openapi-typescript` — зафиксирована + `--alphabetize`

**Детерминизм подтверждён, тест проходит, готово к merge.**
