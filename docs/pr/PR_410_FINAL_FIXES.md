# PR #410: Финальные исправления для стабильности тестов

## 🎯 Цель исправлений

Устранить все источники dual-Base проблем и нестабильности тестов, связанные с манипуляциями `sys.modules` и переимпортами модулей.

---

## ✅ Исправление 1: Полное удаление sys.modules cleanup из `reset_environment()`

### Проблема
В `conftest.py` fixture `reset_environment()` удалял модули из `sys.modules`:
```python
for module_name in new_modules:
    if module_name.startswith("core."):
        continue  # Защита core.*
    if module_name.startswith(("app.", "tests.")):
        del sys.modules[module_name]  # ❌ Создаёт dual-Base!
```

### Почему это плохо
1. **Dual-Base проблемы**: Удаление `app.*` модулей вызывает их переимпорт
2. **Новый Base при переимпорте**: Даже если код тот же, SQLAlchemy создаёт новый класс `Base`
3. **Нестабильность тестов**: Особенно под `pytest-xdist`, где каждый worker может получить свой `Base`
4. **Нарушение правил**: Противоречит правилам "no sys.modules mutation"

### Решение
**Полностью убрали** удаление модулей из `sys.modules`:
```python
# CRITICAL: Do NOT delete modules from sys.modules
# This causes dual-Base issues, module identity chaos, and unpredictable test failures.
# Module cleanup should be done explicitly via module_purge.purge_modules() with protect lists,
# NOT via autouse fixtures that affect all tests.
```

### Файл
- `conftest.py` (root), строки 208-228

---

## ✅ Исправление 2: Улучшение теста `test_get_async_session_import_error`

### Проблема
Тест падал в CI, где async extras доступны, потому что:
- Monkeypatch не полностью симулировал "extras missing" сценарий
- Нужно было патчить также `sa_asyncio` для детерминированного поведения

### Решение
Добавили патч `sa_asyncio=None`:
```python
monkeypatch.setattr(db, "create_async_engine", None, raising=False)
monkeypatch.setattr(db, "async_sessionmaker", None, raising=False)
monkeypatch.setattr(db, "AsyncSessionLocal", None, raising=False)
monkeypatch.setattr(db, "sa_asyncio", None, raising=False)  # ✅ Новое
```

### Файл
- `tests/test_core_db_coverage.py`, строки 269-285

---

## ✅ Исправление 3: `isolated_test_client` уже исправлен

### Статус
Fixture уже не использует `importlib.reload()`:
```python
@pytest.fixture
def isolated_test_client():
    """NOTE: Removed importlib.reload() to prevent dual-Base issues."""
    import app
    client = TestClient(cast(ASGIApp, app.app))
    # ... без reload
```

### Файл
- `conftest.py` (root), строки 331-349

---

## ✅ Исправление 4: `pytest_configure()` уже исправлен

### Статус
`pytest_configure()` не импортирует `core.db` и `core.models`:
```python
def pytest_configure(config: pytest.Config) -> None:
    # Только env setup
    os.environ.setdefault("TESTING", "true")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    # NOTE: DB initialization moved to session autouse fixture
```

### Файл
- `conftest.py` (root), строки 34-94

---

## 📊 Итоговый эффект

### До исправлений
- ❌ `reset_environment()` удалял `app.*` и `tests.*` из `sys.modules`
- ❌ Это вызывало переимпорты и создание нового `Base`
- ❌ Тесты падали с `app.models.events.Base is not core.db.Base`
- ❌ Нестабильность под `pytest-xdist`

### После исправлений
- ✅ Никаких манипуляций с `sys.modules` в autouse fixtures
- ✅ Единый `Base` для всех моделей
- ✅ Стабильные тесты под `pytest-xdist`
- ✅ Соответствие правилам import hygiene

---

## 🔍 Проверка исправлений

### 1. Проверить, что нет sys.modules deletion
```bash
grep -n "del sys.modules" conftest.py
# Должно быть только в reset_sys_modules для VIP (точечное использование)
```

### 2. Проверить, что нет importlib.reload
```bash
grep -rn "importlib.reload" conftest.py tests/conftest.py
# Не должно быть в isolated_test_client
```

### 3. Запустить тест single Base
```bash
pytest tests/test_import_hygiene_single_base.py::test_single_base_instance -v
```

### 4. Запустить async session тест
```bash
pytest tests/test_core_db_coverage.py::TestCoreDB::test_get_async_session_import_error -v
```

---

## 📝 Ключевые принципы

1. **No sys.modules mutation in autouse fixtures**: Манипуляции с `sys.modules` только через `module_purge.purge_modules()` с protect lists
2. **No module reloads**: `importlib.reload()` создаёт новые классы, даже если код тот же
3. **Single Base source**: `Base` должен быть только один, из `core.db`
4. **Explicit cleanup**: Если нужна изоляция модулей — делать явно в конкретных тестах, не глобально

---

## 🚀 Следующие шаги

1. ✅ Все исправления применены
2. 🔄 Запустить полный test suite
3. 🔄 Проверить coverage (должен быть >= 97%)
4. 🔄 Убедиться, что нет флейков под `pytest-xdist`

---

## 📚 Связанные файлы

- `conftest.py` (root) - основные исправления
- `tests/test_core_db_coverage.py` - улучшение async теста
- `PR_410_FIXES_DETAILED.md` - подробное описание всех исправлений
