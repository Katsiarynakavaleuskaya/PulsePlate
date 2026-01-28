# PR-TP2 — DB Fallback Cleanup Audit

**Project:** PulsePlate
**PR:** TP2 (DB fallback extraction)
**Audit type:** Docs-only (audit-first)
**Date:** 2026-01-28
**Based on:** CONTEXT_HANDOFF_2026-01-28.md
**Precondition:** PR-616 merged (`51376fe88dd816977580532085c42c238bd6aa9d`)

---

## 0) Scope & Constraints (Non-negotiable)

### In-scope
- Идентификация и описание DB fallback логики, **находящейся в `legacy_app.py`**
- Анализ зависимостей, сайд-эффектов и порядка инициализации
- Выбор целевого модуля для выноса fallback helpers (решение принимается в PLAN, не здесь)
- Формализация инвариантов поведения (что нельзя сломать)
- Фиксация текущих тестов и требований к тестированию

### Explicit out-of-scope
- ❌ Изменение fallback поведения
- ❌ Изменение OpenAPI / контрактов
- ❌ Оптимизация, DRY, "красивый рефактор"
- ❌ Любые новые runtime-фичи
- ❌ Изменения DB схемы, соединений или политики retry
- ❌ Решение о target module (принимается в PLAN)

---

## 1) Текущее положение (As-Is)

### 1.1 Файл-источник
- `legacy_app.py`
- Роль файла по канону: **thin proxy only**
  → наличие DB fallback логики = технический долг (устраняется в TP2)

### 1.2 Обнаруженные элементы DB fallback

#### Functions
1. `_validate_fallback_url()`
   - Назначение: валидация значения `DB_FALLBACK_URL`
   - Зависимости: env vars (`os.getenv`), `logger`
   - Side-effects: исключения при некорректных значениях
   - Критично: **gatekeeper** для production constraints

2. `_check_production_constraints()`
   - Назначение: проверка разрешённости fallback в prod
   - Зависимости: env flags (`ALLOW_DB_PERSISTENT_FALLBACK`, `ALLOW_DB_INMEMORY_FALLBACK`)
   - Критично: **gatekeeper** логики fallback
   - Side-effects: логирование, исключения

3. `_initialize_fallback_engine()`
   - Назначение: создание fallback DB engine
   - Зависимости:
     - `sqlalchemy.create_engine`
     - `core.models` (import для `Base.metadata`)
     - `core.models.Base.metadata.create_all`
   - Потенциальный риск: дубли engine / lifecycle mismatch
   - Side-effects: создание SQLAlchemy engine, инициализация схемы

4. `_configure_session_bindings()`
   - Назначение: биндинг SessionLocal / метрик
   - Зависимости:
     - `core.db` (SessionLocal, _RAW_ENGINE, engine, EngineCompat)
     - `core.metrics` (опционально, lazy import)
     - `os.environ` (установка `DB_HEALTH_DEGRADED`, `DB_FALLBACK_URL`)
   - Side-effects: влияет на global DB state (SessionLocal, engine), env vars, метрики
   - Критично: **центральная точка мутации** глобального состояния

5. `_attempt_db_fallback()`
   - Назначение: оркестрация fallback-перехода
   - Зависимости: все вышеперечисленные функции
   - Критично: **центральная точка поведения**
   - Side-effects: полный fallback-переход (engine, session, env, метрики)

#### Globals
6. `_db_fallback_active`
   - Тип: module-level flag (`bool`)
   - Назначение: индикатор активного fallback состояния
   - Использование: health endpoints проверяют этот флаг
   - Риск: import-order / race-condition / test isolation
   - Side-effects: глобальное состояние модуля

#### Usage
7. Используется в `lifespan()` context manager
   - Влияние: startup / shutdown lifecycle приложения
   - Риск: порядок инициализации vs dependency graph
   - Контекст: FastAPI lifespan event handler (startup phase)
   - Вызов: `lifespan()` → `init_db()` → при ошибке → `_attempt_db_fallback()`

8. Используется в health endpoint (`legacy_app.py:1193`)
   - Проверка: `if _db_fallback_active or os.getenv("DB_HEALTH_DEGRADED") == "1"`
   - Назначение: возврат degraded state для health checks

---

## 2) Dependency Map

### Internal
- `core.db`
  - `SessionLocal` (sessionmaker instance, мутируется через `.configure()` или пересоздаётся)
  - `_RAW_ENGINE` (module-level variable, мутируется напрямую)
  - `engine` (EngineCompat wrapper, мутируется напрямую)
  - `EngineCompat` (класс-обёртка)
  - **Риск:** Direct module mutation (HIGH)
- `core.models`
  - `Base.metadata` (SQLAlchemy metadata, используется для `create_all()`)
  - **Риск:** Import-time side effects (MEDIUM)
  - **Требование:** `core.models` должен быть импортирован до `Base.metadata.create_all()`
- `core.metrics`
  - `metrics_client` (optional, lazy import)
  - **Риск:** Optional dependency, no-op on failure (LOW)

### External
- Environment variables:
  - `DB_FALLBACK_URL` (fallback SQLite URL, default: `sqlite:///:memory:`)
  - `ALLOW_DB_PERSISTENT_FALLBACK` (production fallback gate, default: unset/false)
  - `ALLOW_DB_INMEMORY_FALLBACK` (non-prod in-memory gate, default: unset/false)
  - `DB_HEALTH_DEGRADED` (health check marker, устанавливается при fallback)
  - `DATABASE_URL` (primary DB URL, переопределяется в non-prod fallback)
  - `ENVIRONMENT` / `APP_ENV` (environment detection)
- `sqlalchemy`
  - `create_engine` (engine creation)
  - **Риск:** Standard library usage (LOW)

### Implicit
- Import order (`legacy_app.py` загружается рано в startup sequence)
- Lifespan execution timing (fallback вызывается в startup phase)
- Global state (`_db_fallback_active` module-level flag)
- Test isolation (параллельные тесты могут конфликтовать через global state)

---

## 3) Risk Analysis

### 3.1 Side-effects
- **Глобальный флаг `_db_fallback_active`**
  - Мутируется в `_configure_session_bindings()`
  - Читается в health endpoint
  - Риск: race conditions в параллельных тестах
- **Session/engine rebinding**
  - `core.db.SessionLocal.configure()` или пересоздание
  - `core.db._RAW_ENGINE = engine`
  - `core.db.engine = EngineCompat(engine)`
  - Риск: нарушение существующих сессий, если они уже созданы
- **Метрики (если включены)**
  - `metrics_client.increment("db_fallback_active", tags=...)`
  - Опционально, lazy import, no-op on failure
  - Риск: минимальный (опциональная зависимость)

### 3.2 Import Order
- **Текущий порядок в `legacy_app.py`:**
  1. `from core.db import get_session, init_db` (line 91)
  2. `import core.models` (line 527, внутри `_initialize_fallback_engine`)
  3. `from core.models import Base` (line 528)
- **Перенос функций может:**
  - изменить момент инициализации (если импорты переносятся)
  - сломать ожидания `lifespan()` (если порядок вызовов меняется)
- **Критично:** `core.models` должен быть импортирован до `Base.metadata.create_all()`

### 3.3 Environment Sensitivity
- **Поведение строго зависит от env vars:**
  - Production detection: `env_name not in {"", "local", "dev", "development", "staging", "test", "ci"}`
  - Fallback gates: `ALLOW_DB_PERSISTENT_FALLBACK`, `ALLOW_DB_INMEMORY_FALLBACK`
  - Fallback URL: `DB_FALLBACK_URL` (default: `sqlite:///:memory:`)
- **Ошибки конфигурации должны:**
  - вести себя **идентично текущему поведению**
  - логировать те же сообщения
  - поднимать те же исключения

### 3.4 Test Fragility
- **Возможные флапы:**
  - при параллельном запуске (xdist) через global state (`_db_fallback_active`)
  - при повторной инициализации lifespan (если тесты переиспользуют app instance)
- **Текущие тесты:**
  - `tests/test_app_db_fallback_97.py` (6 test cases, изолированные)
  - `tests/test_health_db.py` (indirect usage)
- **Требование:** тесты должны оставаться детерминированными после переноса

---

## 4) Behavioral Invariants (Must Not Break)

1. **Fallback активируется только при разрешённых env-флагах**
   - Production: требует `ALLOW_DB_PERSISTENT_FALLBACK=1` + persistent URL
   - Non-production: требует `ALLOW_DB_INMEMORY_FALLBACK=1` или IO error
   - In-memory fallback запрещён в production (всегда)

2. **В production fallback запрещён, если явно не разрешён**
   - Без `ALLOW_DB_PERSISTENT_FALLBACK=1` → поднимается original error
   - In-memory URL в production → поднимается original error

3. **Поведение при некорректном `DB_FALLBACK_URL` — без изменений**
   - Validation логика должна быть идентичной
   - Error messages должны совпадать

4. **Fallback может активироваться только один раз**
   - `_db_fallback_active` флаг предотвращает повторную активацию
   - После успешного `init_db()` флаг сбрасывается

5. **Lifespan не должен:**
   - менять порядок startup/shutdown
   - вызывать fallback повторно
   - нарушать dependency graph

6. **Guards и coverage остаются зелёными**
   - `pytest -q tests/test_repo_policy_guards.py` должен проходить
   - Coverage ≥97% (total + diff-coverage)

7. **Session binding должно работать идентично**
   - `core.db.SessionLocal` должен быть сконфигурирован
   - `core.db.engine` должен указывать на fallback engine
   - Существующие сессии должны продолжать работать

8. **Environment variables устанавливаются идентично**
   - `DB_HEALTH_DEGRADED=1` при активном fallback
   - `DB_FALLBACK_URL` устанавливается (non-prod) или только для internal use (prod)
   - `DATABASE_URL` переопределяется в non-prod fallback

---

## 5) Candidate Target Modules (To Decide in PLAN)

### Option A — `core/db/fallback.py`
**Плюсы**
- Логическая близость к DB слою
- Явное место для engine/session логики
- Соответствует архитектуре: DB concerns в `core/db/`

**Риски**
- Import cycles (`core.db` ↔ fallback) — нужно проверить
- Более строгие требования к init order
- Требует создания новой структуры директорий

### Option B — `app/utils/db_fallback.py`
**Плюсы**
- Изоляция от core (меньше риск import cycles)
- Проще контролировать lifecycle
- Следует паттерну TP1 (helpers в `app/utils/`)

**Риски**
- Размывание ответственности слоя `app`
- DB fallback — это core infrastructure, не adapter utility
- Менее явное разделение concerns

### Option C — Добавить в существующий `core/db.py`
**Плюсы**
- Нет новых файлов
- Вся DB логика в одном месте

**Риски**
- `core/db.py` уже большой (916 lines)
- Смешивает initialization с fallback логикой
- Сложнее тестировать изолированно

> ❗ **Решение принимается в PR-TP2 PLAN, не здесь.**
> Аудит только фиксирует варианты и их trade-offs.

---

## 6) Test Strategy (Audit-level)

- **Зафиксировать текущие тесты, покрывающие fallback:**
  - `tests/test_app_db_fallback_97.py` (6 test cases)
  - `tests/test_health_db.py` (indirect usage)
- **Добавить (или подтвердить наличие):**
  - tests на single-activation (проверка, что fallback активируется только один раз)
  - tests на env gating (production vs non-production constraints)
  - tests на lifespan integration (проверка, что lifespan вызывает fallback корректно)
  - tests на session binding (проверка, что SessionLocal/engine настроены после fallback)
- **Никаких новых сценариев**, только фиксация поведения
- **Требование:** все существующие тесты должны проходить после переноса

---

## 7) Audit Conclusion

### 6.1. Behavior Preservation

| Constraint | Current Behavior | Must Preserve |
|------------|------------------|---------------|
| **Production in-memory rejection** | Raises original error | ✅ Exact same error |
| **Production persistent fallback** | Requires `ALLOW_DB_PERSISTENT_FALLBACK=1` | ✅ Exact same validation |
| **Non-production fallback** | Allows in-memory or IO errors | ✅ Exact same logic |
| **Session binding** | Mutates `core.db.SessionLocal`, `_RAW_ENGINE`, `engine` | ✅ Exact same mutations |
| **Environment variables** | Sets `DB_HEALTH_DEGRADED`, `DB_FALLBACK_URL` | ✅ Exact same env vars |
| **Metrics** | Optional lazy import, no-op on failure | ✅ Exact same pattern |
| **Global flag** | `_db_fallback_active` module-level flag | ✅ Preserve visibility |

### 6.2. Import Order Dependencies

| Dependency | Order | Rationale |
|------------|-------|------------|
| `core.models` import | Before `Base.metadata.create_all` | SQLAlchemy metadata must be initialized |
| `core.db` import | Before session binding | SessionLocal must exist to configure |

### 6.3. Test Compatibility

| Test File | Current Import | Required Change |
|-----------|----------------|-----------------|
| `tests/test_app_db_fallback_97.py` | `import app; app._attempt_db_fallback(...)` | `from core.db.fallback import _attempt_db_fallback` |
| `tests/test_health_db.py` | Indirect via health endpoint | No change (endpoint still works) |

---

## 8) References

- **Policy:** `AGENTS.md` (legacy_app.py policy section)
- **TP1 Audit:** `docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md`
- **TP1 Plan:** `docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md`
- **Context Handoff:** `docs/CONTEXT_HANDOFF_2026-01-28.md`
- **Backlog Ledger:** `docs/roadmap/BACKLOG_LEDGER.md` (PR-TP2 entry)
- **DB Fallback Tests:** `tests/test_app_db_fallback_97.py`
- **Core DB Module:** `core/db.py`
- **README:** `README.md` (Database fallback behavior section)

---

## 9) Evidence Collection

### 11.1. Function Locations

```bash
# Verify function locations
rg -n "^def _validate_fallback_url|^def _check_production_constraints|^def _initialize_fallback_engine|^def _configure_session_bindings|^def _attempt_db_fallback" legacy_app.py
```

**Observed:**
- `_validate_fallback_url`: line 445
- `_check_production_constraints`: line 473
- `_initialize_fallback_engine`: line 516
- `_configure_session_bindings`: line 546
- `_attempt_db_fallback`: line 617

### 11.2. Usage Points

```bash
# Verify usage in lifespan
rg -n "_attempt_db_fallback|_validate_fallback_url|_check_production_constraints|_initialize_fallback_engine|_configure_session_bindings" legacy_app.py
```

**Observed:**
- `lifespan()`: line 681 (calls `_attempt_db_fallback`)
- Health endpoint: line 1193 (checks `_db_fallback_active`)

### 11.3. Test Coverage

```bash
# Verify test file exists
ls -la tests/test_app_db_fallback_97.py
pytest -q tests/test_app_db_fallback_97.py -v
```

**Observed:**
- Test file exists: `tests/test_app_db_fallback_97.py`
- 6 test cases covering all major branches

---

**Audit status:** ✅ Completed
**Next step:** Create `docs/pr/PR_TP2_DB_FALLBACK_PLAN.md`
