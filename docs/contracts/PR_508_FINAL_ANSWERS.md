# PR-508: Финальные ответы на уточняющие вопросы

**Дата:** 2026-01-09
**Цель:** Зафиксировать все факты перед финальным планом PR-508

---

## Ответы на 3 критических вопроса

### Вопрос 1: `constraints.txt` гарантированно есть в репо?

**✅ ДА, файл существует**

**Проверка:**
```bash
$ test -f constraints.txt && echo "EXISTS" || echo "NOT_EXISTS"
EXISTS
```

**Использование в CI:**
```yaml
# .github/workflows/ci.yml:130-131
python -m pip install -r requirements.txt -c constraints.txt
python -m pip install -r requirements-dev.txt -c constraints.txt
```

**Используется в:**
- ✅ `ci.yml` (backend CI) — везде
- ✅ `nightly.yml`
- ✅ `pr-coverage.yml`
- ✅ `nightly-tests.yml`
- ✅ `pr-tests.yml`
- ✅ `docker-openapi-smoke.yml`

**Вывод:** `constraints.txt` — стандарт для всех backend CI jobs.

**Рекомендация для Frontend CI:**
```yaml
# Заменить (frontend-ci.yml:67)
pip install -r requirements.txt

# На (синхронизация с backend CI)
python -m pip install -r requirements.txt -c constraints.txt
```

**✅ Это P1 (не P0), но желательно для консистентности**

---

### Вопрос 2: `make openapi` будет требовать `npm ci` или можно `npm install`?

**✅ Ответ: `npm ci` (детерминированный, как в CI)**

**Обоснование:**

**Текущее использование в CI:**
```yaml
# .github/workflows/frontend-ci.yml:48
- name: Install dependencies
  run: npm ci
```

**Почему `npm ci`, а не `npm install`:**
- ✅ Детерминированный (использует `package-lock.json` точно)
- ✅ Быстрее (не разрешает зависимости заново)
- ✅ Безопаснее (не обновляет lockfile)
- ✅ Стандарт для CI

**Решение для Makefile:**
```makefile
openapi: ## Generate OpenAPI schema (backend) and regenerate frontend types
	python3 scripts/generate_openapi.py
	cd frontend && npm ci && npm run generate-types
```

**Почему `npm ci` в Makefile:**
- Локально и в CI — одинаково
- Предсказуемо (не зависит от версии npm/node)
- Если lockfile устарел — явно упадёт (лучше, чем тихий дрейф)

**Альтернатива (если хочешь гибкость):**
```makefile
openapi: ## Generate OpenAPI schema (backend) and regenerate frontend types
	python3 scripts/generate_openapi.py
	cd frontend && npm install && npm run generate-types
```

**Но лучше `npm ci`** — консистентность с CI.

---

### Вопрос 3: В каком файле запускается прод/дев uvicorn? Всё уже на `app.main`?

**⚠️ Ответ: НЕ везде, есть legacy entrypoints**

**Проверка всех мест:**

#### ✅ Канонические (используют `app.main:app`):

1. **Dockerfile:89** (production):
   ```dockerfile
   CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Dockerfile:168** (development):
   ```dockerfile
   CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
   ```

3. **Makefile:93** (dev):
   ```makefile
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

4. **README.md:470**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. **deploy/docker-compose.production.yaml:21**:
   ```yaml
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

#### ❌ Legacy (используют `app:app` или `legacy_app`):

1. **deploy/docker-compose.staging.yaml:19**:
   ```yaml
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
   **Проблема:** Использует `app:app` → `app/__init__.py` → `legacy_app.app` (без bootstrap)

2. **setup_cli_aliases.sh:89-90**:
   ```bash
   create_alias "ppserver" "cd $PROJECT_ROOT && uvicorn app:app --reload --host 0.0.0.0 --port 8001"
   create_alias "ppserver-8000" "cd $PROJECT_ROOT && uvicorn app:app --reload --host 0.0.0.0 --port 8000"
   ```
   **Проблема:** Использует `app:app` → не канонический

3. **run_all.sh:6**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8001 --reload
   ```
   **Проблема:** Использует `app:app` → не канонический

4. **docs/deploy/PRODUCTION.md:167**:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```
   **Проблема:** Устаревшая документация

5. **ios/SHOPPING_LIST_SETUP.md:64**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```
   **Проблема:** Устаревшая документация

**Вывод:**
- ✅ **Production/Docker/CI** — везде `app.main:app` (канонический)
- ❌ **Staging docker-compose** — `app:app` (legacy)
- ❌ **Локальные скрипты** — `app:app` (legacy)
- ❌ **Документация** — частично устаревшая

**Рекомендация:**
- **PR-508 НЕ трогает** эти файлы (это не baseline, это cleanup)
- **Отдельный PR** (например, PR-512) для миграции legacy entrypoints
- **В PR-508** только документируем: "канон = `app.main:app`"

---

## Анализ Frontend CI (детальный разбор)

### P0: Генерация OpenAPI неканоническая

**Текущий код (frontend-ci.yml:69-72):**
```yaml
- name: Generate OpenAPI JSON from backend
  run: |
    cd ..
    python -c "from app import app; import json; print(json.dumps(app.openapi(), indent=2))" > frontend/src/api/openapi.json
```

**Проблемы:**
1. ❌ `from app import app` → `app/__init__.py` → `legacy_app.app` (без bootstrap)
2. ❌ Нет `sort_keys=True` → недетерминированный JSON
3. ❌ Нет проверки синхронизации

**Решение:**
```yaml
- name: Generate OpenAPI JSON from backend (canonical)
  run: |
    cd ..
    python3 scripts/generate_openapi.py

- name: Fail if OpenAPI/types are out of sync
  run: |
    cd ..
    git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts
```

**✅ Правка #1 (обязательная):** заменить на скрипт
**✅ Правка #2 (обязательная):** добавить diff-check

---

### P1: Установка backend deps в Frontend CI

**Текущий код (frontend-ci.yml:64-67):**
```yaml
- name: Install backend dependencies
  run: |
    cd ..
    pip install -r requirements.txt
```

**Проблема:**
- Не использует `constraints.txt` (как в backend CI)
- Может установить другие версии → рассинхронизация

**Решение:**
```yaml
- name: Install backend dependencies
  run: |
    cd ..
    python -m pip install -r requirements.txt -c constraints.txt
```

**✅ Правка #3 (желательная, P1):** синхронизировать с backend CI

---

## Анализ Backend CI (куда вставить openapi-sync)

### Текущая структура (ci.yml):

```yaml
jobs:
  pr_scope_guard: ...
  lint: ...
  security: ...
  test-pr:
    needs: pr_scope_guard
    # ...
  test-main: ...
  coverage: ...
```

**Рекомендация:** Добавить `openapi-sync` после `security`, перед `test-pr`

**Почему:**
- Быстрый job (fail fast)
- Не блокирует тесты, но блокирует `test-pr` (через `needs`)
- Логически: проверка контрактов перед тестами

**Структура:**
```yaml
jobs:
  pr_scope_guard: ...
  lint: ...
  security: ...
  openapi-sync:  # ← Новый job
    needs: []  # Независимый
    # ...
  test-pr:
    needs: [pr_scope_guard, openapi-sync]  # ← Добавить зависимость
    # ...
```

---

## Финальный список файлов PR-508 (9 файлов)

### Обязательные (baseline):

1. ✅ `scripts/generate_openapi.py` (new) — единый источник генерации
2. ✅ `Makefile` (edit) — таргеты `openapi`/`openapi-check`
3. ✅ `.github/workflows/frontend-ci.yml` (edit) — 3 правки:
   - Заменить генерацию на скрипт
   - Добавить diff-check
   - Синхронизировать pip install (опционально, P1)
4. ✅ `.github/workflows/ci.yml` (edit) — добавить `openapi-sync` job
5. ✅ `docs/contracts/API_CANONICAL_MAP.md` (new) — карта endpoints
6. ✅ `docs/contracts/API_COMPAT.md` (new) — политика совместимости
7. ✅ `frontend/AGENTS.md` (edit) — правила (запрет ручных типов)
8. ✅ `frontend/src/api/openapi.json` (regen) — обновление из бэкенда
9. ✅ `frontend/src/api/schema.ts` (regen) — регенерация типов

**Итого: 9 файлов** ✅ (в лимите 15)

---

## Что НЕ входит в PR-508 (отдельные PR)

### Legacy entrypoints (не baseline):

- ❌ `deploy/docker-compose.staging.yaml` — миграция `app:app` → `app.main:app`
- ❌ `setup_cli_aliases.sh` — миграция aliases
- ❌ `run_all.sh` — миграция скрипта
- ❌ Документация (README, docs/) — обновление примеров

**Почему:**
- Это cleanup/миграция, не baseline
- PR-508 = инфраструктура (генерация + CI-гейт)
- Cleanup = отдельный PR (например, PR-512)

---

## Готовые дифы (после фидбека)

После твоего фидбека подготовлю:
1. `scripts/generate_openapi.py` (полный файл)
2. `Makefile` (точные строки для вставки)
3. `frontend-ci.yml` (3 правки с контекстом)
4. `ci.yml` (openapi-sync job + needs в test-pr)
5. Документы (API_CANONICAL_MAP.md, API_COMPAT.md)
6. `frontend/AGENTS.md` (правила)

**Жду фидбека по:**
- constraints.txt в Frontend CI (P1, но желательно)
- npm ci vs npm install в Makefile (рекомендую npm ci)
- Legacy entrypoints (не трогаем в PR-508, отдельный PR)

---

## Итоговые ответы (кратко)

| Вопрос | Ответ | Файлов | Приоритет |
|--------|-------|--------|-----------|
| 1. constraints.txt есть? | ✅ ДА | 0 (уже есть) | P1 (синхронизация) |
| 2. npm ci или install? | ✅ `npm ci` | 0 (в Makefile) | P0 (детерминированность) |
| 3. Всё на app.main? | ⚠️ НЕТ (есть legacy) | 0 (не трогаем) | P2 (отдельный PR) |

**Готов к фидбеку для финальных дифов!** 🚀
