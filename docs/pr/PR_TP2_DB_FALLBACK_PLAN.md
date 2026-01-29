# PR-TP2 — DB Fallback Extraction Plan (legacy_app.py → core/db_fallback.py)

**Project:** PulsePlate
**PR:** TP2 (DB fallback extraction)
**Plan type:** Docs-only (audit-first)
**Date:** 2026-01-28
**Audit:** `docs/audit/PR_TP2_DB_FALLBACK_AUDIT.md`
**Precondition:** PR-616 merged (`51376fe88dd816977580532085c42c238bd6aa9d`)
**Risk:** HIGH (startup critical path + core.db mutation)

---

## 0) Goal / Non-goals

### Goal
Вынести DB fallback helpers из `legacy_app.py` в **новый модуль** `core/db_fallback.py`, оставив `legacy_app.py` строго **thin proxy only**, без изменения поведения.

### Non-goals (explicit)
- ❌ Изменение fallback поведения
- ❌ Изменение OpenAPI/контрактов
- ❌ DRY/beauty refactor
- ❌ Изменение DB схем/соединений/retry policy
- ❌ Любые новые runtime-features

---

## 1) Target Design (To-Be)

### 1.1 New module
- **Create:** `core/db_fallback.py` (flat module; avoids `core/db.py` vs `core/db/` package collision)

### 1.2 Symbols to move (1:1)
Из `legacy_app.py` переносим **без изменения логики**:
- `_validate_fallback_url()`
- `_check_production_constraints()`
- `_initialize_fallback_engine()`
- `_configure_session_bindings()`
- `_attempt_db_fallback()`
- `_db_fallback_active` (module-level flag)

### 1.3 Integration points (keep behavior)
- `legacy_app.py`:
  - В `lifespan()` остаётся тот же контрольный поток, но вызов идёт в `core.db_fallback._attempt_db_fallback`
  - Health endpoint продолжает возвращать degraded state **по тем же условиям**:
    - `_db_fallback_active` OR `DB_HEALTH_DEGRADED == "1"`

---

## 2) Critical Constraints (Behavioral Invariants)

Инварианты **обязательны** (копия из audit, без reinterpretation):
1) Fallback активируется только при разрешённых env-флагах
2) В production fallback запрещён, если явно не разрешён
3) Некорректный `DB_FALLBACK_URL` → идентичное поведение/ошибки/логирование
4) Fallback активируется только один раз (`_db_fallback_active`)
5) Lifespan порядок startup/shutdown не меняется
6) Guards/coverage остаются зелёными
7) Session binding работает идентично (SessionLocal/_RAW_ENGINE/engine)
8) Env vars (`DB_HEALTH_DEGRADED`, `DB_FALLBACK_URL`, `DATABASE_URL`) выставляются идентично

---

## 3) Migration Phases (3-phase plan)

### Phase 0 — Pre-flight (no code changes)
**Purpose:** предотвратить import cycle surprises и зафиксировать проверочный набор команд.
- Verify audit evidence commands (function locations, usage points)
- Verify current tests green:
  - `pytest -q tests/test_app_db_fallback_97.py -v`
  - `pytest -q tests/test_health_db.py -v` (если быстрый)
  - `pytest -q tests/test_repo_policy_guards.py`

**Exit criteria:**
- Всё зелёное на `main` и на ветке TP2 до изменений

---

### Phase 1 — Extract module (minimal move, no integration change yet)
**Steps:**
1) Create `core/db_fallback.py`
2) Move 5 functions + global flag **verbatim** (копипаст/перенос), без изменения логики
3) Ensure imports in `core/db_fallback.py` отражают текущие runtime зависимости:
   - `sqlalchemy.create_engine`
   - `core.models` / `Base.metadata.create_all` (как сейчас)
   - `core.db` symbols (SessionLocal/_RAW_ENGINE/engine/EngineCompat)
   - optional `core.metrics` lazy import (как сейчас)
4) Add module-level docstring с политикой:
   - "refactor-only; behavior frozen; startup critical path"

**Important:**
На этом этапе `legacy_app.py` ещё может продолжать использовать старые функции, если нужно для промежуточного состояния, но предпочтительнее не держать дубликаты долго — см. Phase 2.

**Exit criteria:**
- Линтер/типизация (если есть) не падают
- Unit tests не запускаем "частично" — только после Phase 2, чтобы избежать двойной истины

---

### Phase 2 — Rewire legacy_app.py to thin proxy (single source of truth)
**Steps:**
1) Replace internal calls в `legacy_app.py`:
   - `lifespan()` вызывает `core.db_fallback._attempt_db_fallback`
2) Health endpoint:
   - заменяет чтение локального `_db_fallback_active` на импорт из `core.db_fallback`
   - или использует accessor (если решим добавить) — но по текущим ограничениям **не добавляем новую абстракцию**, только прямой импорт.
3) Remove the extracted function bodies and `_db_fallback_active` from `legacy_app.py`
   - `legacy_app.py` остаётся thin-proxy: роутинг/инициализация/вызов helper'ов, без DB fallback реализации.

**Exit criteria:**
- В репо существует ровно 1 реализация fallback логики: `core/db_fallback.py`
- `legacy_app.py` не содержит fallback function definitions и flag

---

### Phase 3 — Tests alignment + guard re-validation (behavior parity)
**Steps:**
1) Update tests that directly import from `legacy_app.py`:
   - `tests/test_app_db_fallback_97.py`: перепривязка к `core.db_fallback`
   - ensure test setup/teardown resets `_db_fallback_active` in the new module as it did previously
2) Ensure health tests still pass (indirect usage)
3) Run full targeted checks (см. Section 5)

**Exit criteria:**
- Existing test suite remains deterministic (xdist-safe)
- No new behavior introduced
- Guards/coverage unchanged or improved

---

## 4) Import Order / Cycle Mitigation

### 4.1 Known sensitive edges
- `core.db` <-> `core.db_fallback` риск циклов:
  - fallback модуль будет импортировать `core.db` для мутирования SessionLocal/_RAW_ENGINE/engine
  - `core.db` **не должен** импортировать `core.db_fallback` на import-time

### 4.2 Rule (hard)
- `core/db.py` не импортирует `core/db_fallback.py` на module import level.
- `legacy_app.py` импортирует fallback функции **локально** или на module-level только если проверено отсутствие циклов.

### 4.3 Implementation tactic (planned)
- Если цикл появляется: перевести импорт `from core.db import ...` внутри функций в `core/db_fallback.py` (function-scope), сохраняя поведение.
- Это допустимо как "refactor-only" при условии: error types/messages unchanged.

---

## 5) Verification Checklist (commands)

### 5.1 Core checks
- `pytest -q tests/test_repo_policy_guards.py`
- `pytest -q tests/test_app_db_fallback_97.py -v`
- `pytest -q tests/test_health_db.py -v`

### 5.2 Coverage
- Run canonical coverage command (project standard)
- Confirm:
  - total coverage ≥ current threshold
  - diff-coverage ≥ 97%

### 5.3 Smoke import cycle checks
- Import app entrypoints:
  - `python -c "import legacy_app"` (or module equivalent)
  - `python -c "from core.db import SessionLocal; import core.db_fallback"`

---

## 6) Rollback Plan (if anything breaks)

### Trigger conditions
- Import cycle introduced (runtime ImportError)
- Tests become non-deterministic (xdist flakes)
- Any behavioral delta detected (errors/messages differ)

### Rollback steps
1) Revert Phase 2 rewiring (restore calls in `legacy_app.py`) while keeping new module as "unused"
2) Or hard revert entire PR branch to pre-TP2 baseline if cycle is deep
3) Keep audit + plan docs (still valid evidence)

---

## 7) DoD (Definition of Done)

### Functional parity
- ✅ All invariants preserved (Section 2)
- ✅ No changes in OpenAPI / contracts
- ✅ Fallback behavior parity validated by existing tests (and any required adjustments)

### Codebase hygiene
- ✅ `legacy_app.py` contains no DB fallback implementations (thin proxy only)
- ✅ Single source of truth: `core/db_fallback.py`

### Quality gates
- ✅ Guards green
- ✅ Coverage thresholds met (total + diff)
- ✅ No forbidden patterns introduced (sys.modules mutation, `builtins.__import__` patching)

### Docs & Process
- ✅ BACKLOG_LEDGER: TP2 moved to "In Progress" → "Merged" on completion
- ✅ Add/update AGENTS.md rule:
  - "DB fallback implementation must live in `core/db_fallback.py`; legacy_app.py thin-proxy only"
  - "Tests referencing fallback must import from core.db_fallback, not legacy_app.py"
  - (only if this policy isn't already documented)

---

## 8) Decision Log (Plan-level)

- **Target module:** `core/db_fallback.py` (flat module; avoids `core/db.py` vs `core/db/` collision)
- **Amendment (CI import collision):** Original target `core/db/fallback.py` (package) rejected because introducing `core/db/` (package) alongside `core/db.py` (file) causes Python to resolve `core.db` as the package in CI; tests then see `SessionLocal is None` and fail. **New target:** `core/db_fallback.py` (flat module); removed `core/db/` package and guard exception.
- **Approach:** 3-phase extraction with rewiring + tests alignment
- **Risk posture:** preserve behavior; avoid module/package collision (AGENTS.md rule: never add `core/<name>/` when `core/<name>.py` exists)

---

**Plan status:** ✅ Ready for implementation (after review)
**Next step:** Start coding TP2 in branch, strictly following phases.
