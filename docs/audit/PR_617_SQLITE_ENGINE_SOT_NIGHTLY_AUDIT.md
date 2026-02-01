## Title

PR-617 — SQLite Engine SoT / Nightly Failure Audit (Dual-engine topology & DB URL isolation)

**Date:** 1 февраля 2026 года
**Owner:** @Katsiarynakavaleuskaya (+ agent)

---

## Reconciliation with original handoff (два “мира”, одна проверка фактами)

В исходном handoff было зафиксировано:

- **Hypothesis A (dual-engine topology)**: падает `tests/test_sqlite_engine_sot.py` из-за mismatch
  “fixture DB path” vs “app engine path” (на macOS часто выглядит как `/Users/...` vs
  `/private/var/folders/...`).

В реальном nightly run (GitHub Actions `21559415692`) мы наблюдали:

- **Hypothesis B (order-dependent DB state leak)**: “no such table …” в API тестах + иногда thread-affinity.

Этот audit документирует **оба** и отмечает, что подтверждено артефактами, а что пока остаётся
гипотезой/не воспроизведено на текущем `main`.

---

## Scope (жёстко ограничено)

- **В рамках этого PR:** DB engine URL Single Source of Truth (SoT) + тестовая изоляция/фикстуры, которые **обязательны** для зелёного nightly.
- **Вне scope:** любые “рефакторы по пути”, новые фичи, миграции моделей/роутеров, изменения контрактов API.

---

## Invariants (не обсуждаем, просто соблюдаем)

1. **Single Source of Truth для SQLite DB URL в тестах**
   - `tests/conftest.py::configure_sqlite_database` — SoT, выставляет `DATABASE_URL` для worker’а.
   - `core.db` обязан использовать этот URL (без “второго” engine/URL).

2. **xdist SQLite requirements**
   - Только **file-based** SQLite (не `:memory:`) для параллельного прогона.
   - Пер-worker изоляция (DB path содержит worker id).
   - `NullPool` + `check_same_thread=False` в тестах/xdist.

3. **No import-time side effects в `core/`**
   - Нельзя “фиксировать” DB URL на import-time.
   - Любые env-dependent решения — только внутри функций (у нас это уже реализовано).

---

## Audit Questions (канонические) → Observations/Answers

### Q1) Где создаётся engine? Есть ли import-time `engine = create_engine(...)`?

**Answer:** engine создаётся **лениво** в `core/db.py` через `_get_raw_engine()` и `EngineCompat(_get_raw_engine)`.

**Evidence (code):**
- `core/db.py`:
  - `_RAW_ENGINE: Optional[Engine] = None`
  - `_get_raw_engine()` создаёт engine только при первом доступе и/или когда `DATABASE_URL` изменился
  - публичный `engine = EngineCompat(_get_raw_engine)` (wrapper, но внутри — lazy)

**Risk:** если какой-либо тест/модуль меняет `DATABASE_URL` и не сбрасывает состояние `core.db`, можно получить “липкий” engine (order-dependent).

---

### Q2) Откуда берётся DB URL в app?

**Answer:** в `core/db.py` DB URL берётся из `get_database_url()` → `_build_engine_url()`:

- Если `DATABASE_URL` выставлен — берём его (env-provided).
- Иначе — дефолт `sqlite:///cache/app.db` (runtime default).

**Important nuance:** в тестах `DATABASE_URL` выставляется session-scoped fixture’ой, поэтому “дефолт” не должен использоваться в тест-рантайме.

---

### Q3) Как тест фиксирует путь fixture DB? Через какой helper строится expected_path?

**Answer:** guard-тест `tests/test_sqlite_engine_sot.py::test_sqlite_engine_url_is_single_source_of_truth`:
- Берёт `expected_url = os.environ["DATABASE_URL"]`
- Берёт `actual_url = str(core.db._RAW_ENGINE.url)` (или fallback на `core.db.engine`)
- Сравнивает **filesystem path** (`Path(...).resolve()`), игнорируя query params.

**Evidence (code):**
- `tests/test_sqlite_engine_sot.py` извлекает путь через `url.replace("sqlite:///", "")` и `Path(...).resolve()`.

---

### Q3.1) Статус Hypothesis A (dual-engine topology) на текущем состоянии репо

На текущей ветке фикса (от `main`) guard-тест проходит:

Observed output:

```text
tests/test_sqlite_engine_sot.py::test_sqlite_engine_url_is_single_source_of_truth PASSED [100%]
```

**Важно:** у нас нет артефакта, который показывал бы именно тот macOS mismatch (`/Users/...` vs
`/private/var/folders/...`) на текущем коммите. Поэтому в этом PR мы **не утверждаем**, что
тот инцидент “исчез” навсегда; мы фиксируем, что **в nightly run `21559415692` падал другой класс проблем**
и что текущая правка закрывает подтверждённый root cause B.

---

### Q4) Есть ли `get_engine()`/singleton? Как кешируется и когда сбрасывается?

**Answer:** singleton реализован как `_RAW_ENGINE` (module-level cache).
Сброс — через:

- `core.db.reset_db_for_tests()` (tests-only helper) — обнуляет `_RAW_ENGINE`, `SessionLocal`, async refs.
- В тест-фикстуре `configure_sqlite_database` есть **жёсткий reset `_RAW_ENGINE`** перед установкой `DATABASE_URL`.

**Risk:** любые тесты, которые вызывают `reset_db_for_tests()` или меняют `DATABASE_URL`, должны быть герметичны (restore env/state), иначе ломают соседние тесты в том же xdist worker.

---

### Q5) Есть ли отдельная логика “for tests” vs “for prod” и где расхождение?

**Answer:** да, частично:

- В тестах SoT = `configure_sqlite_database` → `DATABASE_URL=sqlite:///<repo>/cache/test_db_<worker>.../test_app.sqlite`.
- В runtime дефолт — `sqlite:///cache/app.db` (если env не задан).
- Для тестов/xdist `core.db._get_sqlite_poolclass()` применяет `NullPool` и `_sqlite_connect_args()` выставляет `check_same_thread=False`.

**Root issue in nightly оказалась не в dual-engine mismatch**, а в **утечке in-memory DB конфигурации** из одного unit-теста, что превращало весь worker в `sqlite:///:memory:` и приводило к “no such table” в API-тестах.

---

## What actually failed in Nightly (Observed)

### Evidence 1: Order-dependent DB state leak (GitHub Actions run 21559415692)

**Symptom observed:**

```text
FAILED tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state
sqlite3.OperationalError: no such table: nutrition_events

FAILED tests/test_simple_coverage_boost.py::TestSimpleCoverageBoost::test_users_endpoint
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread
```

**Root cause identified:** `tests/test_core_db_coverage.py::TestCoreDB::test_init_db` вызывал `db.init_db("sqlite:///:memory:")` и не восстанавливал `DATABASE_URL` + не сбрасывал `core.db` state в teardown.

**Fix (commit 1):** Добавлен `try/finally` с restore env + `reset_db_for_tests()` + `init_db()` для возврата к file-based DB.

**Local verification (после fix 1):**

```bash
pytest -q tests/test_core_db_coverage.py::TestCoreDB::test_init_db \
  tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state \
  tests/test_simple_coverage_boost.py::TestSimpleCoverageBoost::test_users_endpoint \
  tests/test_users_api.py::test_get_user_not_found
# Result: .... [100%] ✅

pytest -q -n 2 tests/test_core_db_coverage.py::TestCoreDB::test_init_db \
  tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state \
  tests/test_simple_coverage_boost.py::TestSimpleCoverageBoost::test_users_endpoint \
  tests/test_users_api.py::test_get_user_not_found
# Result: .... [100%] ✅
```

---

### Evidence 2: Fixture ordering race (table already exists)

**Symptom observed (user report + CI):**

```text
sqlite3.OperationalError: table nutrition_events already exists
```

Это происходило на setup (до самих тестов) в `core_db.init_db()` → `Base.metadata.create_all(bind=_RAW_ENGINE)`.

**Root cause identified:**

`tests/conftest.py` содержал два `autouse=True, scope="session"` fixtures без явной зависимости:

1. `_init_db_for_api_suite()` — вызывает `core_db.init_db()`
2. `configure_sqlite_database()` — выставляет per-worker `DATABASE_URL` и снова вызывает `db_module.init_db()` + redundant `Base.metadata.create_all()`

**Проблема:** pytest мог запустить их в любом порядке. Если `_init_db_for_api_suite` запустилась первой:
- `init_db()` использовал default URL (возможно shared между workers)
- Затем `configure_sqlite_database` менял URL и снова вызывал `init_db()` + redundant `create_all()`
- Два xdist workers могли одновременно выполнять `create_all()` на одном файле → race → "table already exists"

**Fix (commit 3):**
1. Добавлена явная зависимость: `_init_db_for_api_suite(configure_sqlite_database: Any)`
2. Удалён redundant `Base.metadata.create_all()` из `configure_sqlite_database`
3. Оставлена verification-only проверка (без создания таблиц)

**Ensures:**
- per-worker `DATABASE_URL` выставляется **до** любых `init_db()` вызовов
- `init_db()` запускается ровно один раз на worker
- Нет DDL race между workers

**Local verification (после fix 2):**

```bash
pytest -q tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state
# Result: . [100%] ✅

pytest -q -n 2 tests/test_nutrition_log_api.py
# Result: .......... [100%] ✅

pytest -q -n 2 tests/test_core_db_coverage.py::TestCoreDB::test_init_db tests/test_nutrition_log_api.py
# Result: ........... [100%] ✅
```

---

### Symptom

Nightly `pytest -n auto` падал на API-тестах с отсутствующими таблицами:

- `sqlite3.OperationalError: no such table: nutrition_events`
- `sqlite3.OperationalError: no such table: users`

**Evidence (CI log, GitHub Actions run `21559415692`):**

Observed output (3 lines):

```text
E   sqlite3.OperationalError: no such table: nutrition_events
FAILED tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state
FAILED tests/test_users_api.py::test_get_user_not_found - assert 503 == 404
```

Также в том же прогоне присутствовал симптом thread-affinity:

```text
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.
```

### Why this looks like “dual-engine topology”

С точки зрения поведения это похоже на “app смотрит в другую базу без схемы”.
Однако guard `tests/test_sqlite_engine_sot.py` по сути проверяет соответствие `DATABASE_URL` ↔ `_RAW_ENGINE.url`, и локально он был зелёный.

Фактическая причина в nightly оказалась **order-dependent leak** внутри одного worker’а.

---

## Root cause (найдено)

### Primary root cause

`tests/test_core_db_coverage.py::TestCoreDB::test_init_db`:
- делал `db.reset_db_for_tests()`
- вызывал `db.init_db("sqlite:///:memory:")`
- **не восстанавливал** `DATABASE_URL`/состояние `core.db` после теста

В xdist это критично, потому что session-scoped фикстуры (`configure_sqlite_database`) уже не перезапускаются в рамках данного worker’а, и остальные тесты в этом worker’е продолжали работать на in-memory DB без требуемых таблиц (или с несогласованным состоянием сессий/engine).

### Secondary impacts

- API тесты (`tests/test_nutrition_log_api.py`, `tests/test_users_api.py`) ожидают, что схема уже создана в file-based DB, которую готовит `configure_sqlite_database`.
- После утечки in-memory DB: таблицы `nutrition_events`/`users` отсутствовали → 503/OperationalError.

---

## Fix (минимальный, без расширения scope)

Исправление сделано в `tests/test_core_db_coverage.py::TestCoreDB::test_init_db`:

- сохраняем `original_db_url = os.environ.get("DATABASE_URL")`
- выполняем тестовую in-memory инициализацию, как и раньше
- в `finally`:
  - `db.reset_db_for_tests()` (жёсткий сброс engine/sessionmaker)
  - возвращаем `DATABASE_URL`
  - вызываем `db.init_db()` чтобы вернуть DB в состояние, ожидаемое API-тестами/фикстурами

**Цель:** гарантировать, что тест, который временно уводит DB в `:memory:`, не ломает остальные тесты в том же worker’е.

---

## Local verification (Observed)

### Regression reproduction subset

Команда:

```bash
pytest -q \
  tests/test_core_db_coverage.py::TestCoreDB::test_init_db \
  tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state \
  tests/test_simple_coverage_boost.py::TestSimpleCoverageBoost::test_users_endpoint \
  tests/test_users_api.py::test_get_user_not_found
```

Observed output:

```text
....                                                                     [100%]
```

### Order-dependence check (подозреваемый → жертва и обратно)

Команда (подозреваемый → жертва):

```bash
pytest -q \
  tests/test_core_db_coverage.py::TestCoreDB::test_init_db \
  tests/test_nutrition_log_api.py
```

Observed output:

```text
...........                                                              [100%]
```

Команда (обратно):

```bash
pytest -q \
  tests/test_nutrition_log_api.py \
  tests/test_core_db_coverage.py::TestCoreDB::test_init_db
```

Observed output:

```text
...........                                                              [100%]
```

### Same subset under xdist

Команда:

```bash
pytest -q -n 2 \
  tests/test_core_db_coverage.py::TestCoreDB::test_init_db \
  tests/test_nutrition_log_api.py::TestNutritionLogAPI::test_meal_log_updates_adherence_state \
  tests/test_simple_coverage_boost.py::TestSimpleCoverageBoost::test_users_endpoint \
  tests/test_users_api.py::test_get_user_not_found
```

Observed output:

```text
....                                                                     [100%]
```

### Fast suite

Команда:

```bash
make test-fast
```

Observed output (tail):

```text
exit_code: 0
```

---

## DoD mapping (из исходного handoff)

1. ✅ Nightly symptom (“no such table …”) объяснён и локально закрыт минимальным патчем.
2. ✅ Локально зелёные ключевые репро-тесты + `make test-fast`.
3. ✅ Import-time engine creation **не обнаружено** (engine lazy); проблема была в утечке состояния из теста.
4. ✅ Guard на SoT (`tests/test_sqlite_engine_sot.py`) остаётся релевантным; теперь ещё и устранили order-dependent leak.
5. ⏳ (опционально) После открытия PR обновить этот файл: PR-617 (CI: <https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/617/checks>).

---

## Notes / Follow-ups (если всплывут)

- Если после фикса nightly всё ещё покажет `sqlite3.ProgrammingError ... thread`:
  - это обычно признак **какого-то прямого `create_engine("sqlite:///:memory:")` без `check_same_thread=False`** в другом тесте/коде.
  - тогда отдельным мини-аудитом собрать callsites `create_engine(` (в repo их мало) и герметизировать конкретный тест.
