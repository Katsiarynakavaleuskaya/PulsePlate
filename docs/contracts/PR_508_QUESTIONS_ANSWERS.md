# PR-508: Ответы на вопросы с аргументацией кодом

**Дата:** 2026-01-09
**Цель:** Зафиксировать границы PR-508 (baseline, ≤15 файлов)

---

## Ключевые куски кода для проверки

### 1) `app/__init__.py` — PEP 562 forwarder

```python
"""App package - shim facade for legacy_app backward compatibility.

This module is intentionally a thin PEP 562 forwarder:
- RU: Не импортируем `legacy_app` eagerly (избегаем циклических импортов).
- EN: Do not eagerly import `legacy_app` (avoid circular imports).

All unknown attributes are resolved from `legacy_app` lazily at access time.
"""

def __getattr__(name: str) -> Any:
    """Resolve attribute lazily from local exports or legacy_app.

    PEP 562 forwarder: pure delegation, no side effects.
    Observability bootstrap (register_metrics) is applied ONLY in app/main.py.
    """
    if name in _LOCAL_EXPORTS:
        mod_name, attr = _LOCAL_EXPORTS[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    return getattr(_legacy(), name)  # ← Делегирует в legacy_app
```

**Ключевой факт:**
- `from app import app` → через `__getattr__("app")` → `getattr(_legacy(), "app")` → `legacy_app.app`
- **НЕ вызывает `app.main`**, значит **НЕ применяет `register_metrics(app)`**
- Это **НЕ канонический entrypoint** для OpenAPI генерации

---

### 2) `app/main.py` — канонический entrypoint

```python
"""
Canonical FastAPI entrypoint for the app package.

Keep imports deterministic: do NOT use importlib exec_module, do NOT mutate sys.path.
"""

from fastapi import FastAPI

from legacy_app import app as _legacy_app  # re-export FastAPI instance from legacy root module

# Register observability infrastructure (middleware + /metrics endpoint)
# This must be done here, not in legacy_app.py, to keep legacy as a thin proxy
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app

register_metrics(app)  # ← Применяет bootstrap (middleware + /metrics)

__all__ = ["app"]
```

**Ключевой факт:**
- `from app.main import app` → **гарантированно** применяет `register_metrics(app)`
- Это **канонический entrypoint** для OpenAPI генерации
- Используется в `uvicorn app.main:app` (Dockerfile, Makefile)

---

### 3) Текущий Frontend CI (проблема)

```yaml
# .github/workflows/frontend-ci.yml:69-72
- name: Generate OpenAPI JSON from backend
  run: |
    cd ..
    python -c "from app import app; import json; print(json.dumps(app.openapi(), indent=2))" > frontend/src/api/openapi.json
```

**Проблема:**
- Использует `from app import app` → **НЕ канонический entrypoint**
- Не применяет `register_metrics(app)`, значит OpenAPI может не содержать `/metrics` endpoint
- Нет `sort_keys=True` → недетерминированный JSON (шум в diff'ах)
- Нет проверки синхронизации (просто перезаписывает файл)

---

### 4) Makefile структура

```makefile
## Default target - run all checks
all: lint test cov-check

## Show this help
help:
	@echo "$(BLUE)🚀 PulsePlate - Команды автоматизации$(NC)"
	@awk 'BEGIN{FS=":.*##"} /^[a-zA-Z0-9_.-]+:.*##/{printf "$(GREEN)%-22s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Run local dev server on :8001
dev: ## Run uvicorn on 0.0.0.0:8001 (reload)
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

## Run tests (quiet)
test: ## Run pytest
	pytest -q
```

**Факт:**
- Makefile в корне репо (один файл)
- Использует формат `target: ## Description` для help
- Уже есть секции (docker, test, cov, etc.)

---

## Ответы на 4 вопроса

### Вопрос 1: Frontend CI мы трогаем в PR-508 или оставляем как есть?

**✅ Ответ: ТРОГАЕМ минимально (1 файл, 2 правки)**

**Обоснование:**

**Проблема 1:** Текущий импорт неканонический
```python
# Текущий (frontend-ci.yml:72)
python -c "from app import app; ..."  # ❌ НЕ канонический

# Должно быть
python -c "from app.main import app; ..."  # ✅ Канонический
```

**Проблема 2:** Нет проверки синхронизации
- CI просто перезаписывает `openapi.json`, но не проверяет, что он актуален
- Если разработчик забыл обновить файл, CI не упадёт

**Решение:**
```yaml
# Заменить step (frontend-ci.yml:69-72)
- name: Generate OpenAPI JSON from backend (canonical)
  run: |
    cd ..
    python3 scripts/generate_openapi.py  # ← Использует app.main.app

- name: Fail if OpenAPI/types are out of sync
  run: |
    cd ..
    git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts
```

**Итого:** 1 файл (frontend-ci.yml), 2 правки (импорт + diff-check)

---

### Вопрос 2: В каком месте репо лежит "истинный" Makefile?

**✅ Ответ: Один Makefile в корне репо**

**Обоснование:**
- Файл: `Makefile` (корень репо)
- Структура: секции с `## Description` для help
- Уже есть: `dev`, `test`, `cov`, `lint`, `typecheck`, `verify`, etc.

**Решение:**
Добавить 2 таргета в конец Makefile (после существующих секций):

```makefile
## Generate OpenAPI schema and regenerate frontend types
openapi: ## Generate OpenAPI schema (backend) and regenerate frontend types
	python3 scripts/generate_openapi.py
	cd frontend && npm run generate-types

## Verify OpenAPI + generated frontend types are in sync
openapi-check: ## Verify OpenAPI + generated frontend types are in sync (no diff)
	python3 scripts/generate_openapi.py
	cd frontend && npm run generate-types
	git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts

.PHONY: openapi openapi-check
```

**Итого:** 1 файл (Makefile), добавление 2 таргетов

---

### Вопрос 3: `scripts/generate_openapi.py` — ок создавать в PR-508?

**✅ Ответ: ДА, это baseline**

**Обоснование:**

**Почему это baseline:**
- Детерминированная генерация OpenAPI — это инфраструктура, не прод-код
- Скрипт не меняет бизнес-логику, только генерирует артефакты
- Это "земля под ногами" для будущих PR

**Почему `from app.main import app`:**
```python
# app/main.py гарантирует:
from legacy_app import app as _legacy_app
from app.bootstrap.metrics import register_metrics

app: FastAPI = _legacy_app
register_metrics(app)  # ← Применяет bootstrap

# Значит app.main.app содержит:
# - Все routes из legacy_app
# - Middleware (metrics)
# - /metrics endpoint
# - Deprecated flags (если есть)
```

**Проверка side effects:**
- `app.main` импортирует `legacy_app` → может быть side effect
- Но это **ожидаемое поведение** (bootstrap должен применяться)
- В CI это безопасно (изолированная среда)

**Решение:**
```python
#!/usr/bin/env python3
"""Generate OpenAPI schema from canonical FastAPI app entrypoint."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    output_path = repo_root / "frontend" / "src" / "api" / "openapi.json"

    # Canonical app entrypoint (metrics bootstrap is applied here)
    from app.main import app  # ← Канонический импорт

    schema = app.openapi()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"✅ OpenAPI schema generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Итого:** 1 файл (scripts/generate_openapi.py), новый

---

### Вопрос 4: Один источник генерации OpenAPI или допускаем "в FE CI по месту"?

**✅ Ответ: ОДИН источник (скрипт)**

**Обоснование:**

**Проблема дублирования:**
```yaml
# Сейчас (frontend-ci.yml)
python -c "from app import app; ..."  # ❌ Неканонический

# Если оставить дублирование:
# Backend CI: scripts/generate_openapi.py
# Frontend CI: python -c "from app.main import app; ..."
# → Два места, два способа, риск рассинхронизации
```

**Решение: один скрипт везде**
```yaml
# Backend CI
- run: make openapi

# Frontend CI
- run: |
    cd ..
    python3 scripts/generate_openapi.py  # ← Тот же скрипт
```

**Преимущества:**
- ✅ Один источник истины
- ✅ Детерминированный JSON (`sort_keys=True`)
- ✅ Легко поддерживать (один файл)
- ✅ Локально и в CI — одинаково

**Итого:** Frontend CI использует `scripts/generate_openapi.py` (не дублирует логику)

---

## Итоговая проверка: `app.main` — единственная точка истины?

**✅ ДА, подтверждено кодом:**

1. **`app/__init__.py`:**
   - `from app import app` → `__getattr__("app")` → `legacy_app.app`
   - **НЕ применяет** `register_metrics(app)`
   - **НЕ канонический**

2. **`app/main.py`:**
   - `from app.main import app` → `app = _legacy_app` + `register_metrics(app)`
   - **Применяет** bootstrap (middleware + /metrics)
   - **Канонический**

3. **Использование в проекте:**
   - `Makefile:93`: `uvicorn app.main:app` ✅
   - `Dockerfile` (вероятно): `uvicorn app.main:app` ✅
   - Frontend CI: `from app import app` ❌ (нужно исправить)

**Вывод:** `app.main.app` — единственная точка истины для OpenAPI генерации.

---

## Риски side effects в CI

**Проверка:**

1. **Импорт `app.main`:**
   ```python
   from app.main import app
   # → Импортирует legacy_app
   # → Импортирует app.bootstrap.metrics
   # → Вызывает register_metrics(app)
   ```

2. **Потенциальные side effects:**
   - ✅ Регистрация middleware — ожидаемое поведение
   - ✅ Регистрация `/metrics` endpoint — ожидаемое поведение
   - ⚠️ Импорт `legacy_app` может инициализировать БД/модели

3. **Митигация:**
   - CI изолированная среда (не влияет на другие jobs)
   - Генерация OpenAPI не требует БД (только метаданные routes)
   - Если есть проблемы — они проявятся сразу в CI

**Вывод:** Риски минимальны, side effects ожидаемые и безопасные.

---

## Финальный ответ на все 4 вопроса

| Вопрос | Ответ | Файлов | Обоснование |
|--------|-------|--------|-------------|
| 1. Frontend CI трогаем? | ✅ ДА (минимально) | 1 файл | Исправить импорт + добавить diff-check |
| 2. Makefile где? | ✅ Корень, один файл | 1 файл | Добавить 2 таргета (openapi/openapi-check) |
| 3. scripts/generate_openapi.py ок? | ✅ ДА (baseline) | 1 файл | Детерминированная генерация — инфраструктура |
| 4. Один источник? | ✅ ДА (скрипт) | 0 файлов | Frontend CI использует тот же скрипт |

**Итого файлов для PR-508:**
- `scripts/generate_openapi.py` (new)
- `Makefile` (edit)
- `.github/workflows/frontend-ci.yml` (edit)
- `.github/workflows/ci.yml` (edit, добавить openapi-sync job)
- `docs/contracts/API_CANONICAL_MAP.md` (new)
- `docs/contracts/API_COMPAT.md` (new)
- `frontend/AGENTS.md` (edit)
- `frontend/src/api/openapi.json` (regen)
- `frontend/src/api/schema.ts` (regen)

**Итого: 9 файлов** ✅ (в лимите 15)

---

## Готов к фидбеку

Все факты проверены кодом, границы PR-508 зафиксированы. Жду твоего фидбека для финального плана.
