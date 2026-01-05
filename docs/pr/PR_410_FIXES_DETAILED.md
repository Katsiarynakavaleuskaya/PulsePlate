# Подробное описание исправлений PR #410

## 1. Исправление импорта в `alembic/env.py`

### Проблема
Линтер показывал предупреждение: `"context" — неизвестный символ импорта`

### Решение
Импорт `from alembic import context` корректен. Это предупреждение линтера можно игнорировать, так как `alembic` устанавливается как зависимость и доступен в runtime.

### Код
```python
from alembic import context  # Корректный импорт, предупреждение линтера можно игнорировать
```

### Почему это важно
- `alembic` — стандартная библиотека для миграций SQLAlchemy
- Импорт работает корректно в runtime
- Предупреждение линтера не критично, но можно добавить `# type: ignore` если нужно

---

## 2. Удаление инициализации БД из `pytest_configure()` в root `conftest.py`

### Проблема
`pytest_configure()` выполнялся до всех тестов и делал:
- Импорт `core.db` и `core.models`
- Вызов `init_db()`
- Это создавало `Base` раньше, чем нужно, и могло конфликтовать с последующими переимпортами

### Решение
Убрали всю логику инициализации БД из `pytest_configure()`, оставили только:
- Установку env переменных
- Настройку `DATABASE_URL`
- Очистку старых файлов БД

### Было
```python
def pytest_configure(config: pytest.Config) -> None:
    # ... env setup ...
    import core.db as core_db
    import core.models
    from core.models import User
    core_db.init_db()  # ❌ Создаёт Base слишком рано
```

### Стало
```python
def pytest_configure(config: pytest.Config) -> None:
    # ... env setup ...
    # NOTE: DB initialization moved to session autouse fixture (_init_db_for_api_suite)
    # This prevents dual-Base issues from module reloads and ensures stable Base identity
```

### Почему это важно
- `pytest_configure()` выполняется очень рано, до всех fixtures
- Если потом модули переимпортируются (через `reload` или удаление из `sys.modules`), может появиться второй `Base`
- Перенос в session fixture гарантирует, что БД инициализируется один раз, после настройки окружения

---

## 3. Удаление `importlib.reload()` для `core.models` и `app`

### Проблема
В `pytest_configure()` был код:
```python
if "core.models" in sys.modules:
    importlib.reload(sys.modules["core.models"])  # ❌ Создаёт новый Base!
else:
    import core.models

if "app" in sys.modules:
    importlib.reload(sys.modules["app"])  # ❌ Может переимпортировать модели с новым Base!
```

### Почему это плохо
1. `reload(core.models)` перезагружает модуль и может создать новый класс `Base`
2. Если `app.models` уже импортированы с первым `Base`, а потом `core.models` перезагружается → получаем два разных `Base`
3. Это приводит к ошибке: `app.models.events.Base is not core.db.Base`

### Решение
Убрали все `reload()` вызовы:
```python
# Просто импортируем без reload
import core.models  # noqa: F401
```

### Почему это важно
- SQLAlchemy `DeclarativeBase` создаёт класс при первом импорте
- `reload()` создаёт новый класс, даже если код тот же
- Это нарушает принцип "single source of truth" для `Base`
- Без reload все модули используют один и тот же `Base` из `core.db`

---

## 4. Защита всех `core.*` модулей от удаления из `sys.modules`

### Проблема
В `reset_environment()` fixture был код:
```python
for module_name in new_modules:
    if module_name.startswith(("app.", "core.", "tests.")):
        del sys.modules[module_name]  # ❌ Удаляет core.db и core.models!
```

### Почему это плохо
1. Удаление `core.db` из `sys.modules` → при следующем импорте создаётся новый `Base`
2. Если `app.models` уже импортированы с первым `Base`, а `core.db` переимпортирован → dual-Base
3. `SessionLocal` может стать `None`, если модуль удалён до инициализации

### Решение
Защитили все `core.*` модули:
```python
# CRITICAL: Do not delete core.* modules from sys.modules
# This causes dual-Base issues and breaks Base identity across tests
for module_name in new_modules:
    # Protect ALL core.* modules from deletion (prevents dual-Base)
    if module_name.startswith("core."):
        continue  # ✅ Не удаляем core.* модули
    if module_name.startswith(("app.", "tests.")):
        try:
            del sys.modules[module_name]
        except KeyError:
            pass
```

### Почему это важно
- `core.db` содержит канонический `Base` — он должен быть единственным
- Удаление `core.*` из `sys.modules` ломает identity `Base` между тестами
- Это критично для `pytest-xdist`, где каждый worker должен использовать один `Base`
- Защита всех `core.*` гарантирует стабильность не только `core.db`, но и других core модулей

---

## 5. Удаление `importlib.reload()` из `isolated_test_client`

### Проблема
Fixture делал:
```python
@pytest.fixture
def isolated_test_client():
    import importlib
    import app

    importlib.reload(app)  # ❌ Перезагружает app, может переимпортировать модели
    client = TestClient(app.app)

    try:
        yield client
    finally:
        importlib.reload(app)  # ❌ Ещё раз перезагружает
```

### Почему это плохо
- `reload(app)` может переимпортировать `app.models` с новым `Base`
- Это создаёт dual-Base проблему
- Не нужно для изоляции тестов — `dependency_overrides.clear()` достаточно

### Решение
Убрали reload, используем только `dependency_overrides.clear()`:
```python
@pytest.fixture
def isolated_test_client():
    """Fixture for creating isolated TestClient instances with clean app state.

    NOTE: Removed importlib.reload() to prevent dual-Base issues.
    Instead, create a fresh TestClient and clear dependency_overrides in teardown.
    """
    import app

    client = TestClient(cast(ASGIApp, app.app))

    try:
        yield client
    finally:
        client.close()
        # Clear dependency overrides to reset state (no reload needed)
        if hasattr(app.app, "dependency_overrides"):
            app.app.dependency_overrides.clear()
```

### Почему это важно
- `reload()` не нужен для изоляции — FastAPI `dependency_overrides` достаточно
- Избегаем переимпорта моделей и dual-Base
- Код проще и предсказуемее

---

## 6. Обновление `_init_db_for_api_suite` fixture в `tests/conftest.py`

### Проблема
Fixture инициализировал БД, но не импортировал модели:
```python
@pytest.fixture(autouse=True, scope="session")
def _init_db_for_api_suite() -> None:
    from core.db import init_db
    init_db()  # ❌ Модели могут быть не зарегистрированы с Base
```

### Решение
Добавили явный импорт `core.models`:
```python
@pytest.fixture(autouse=True, scope="session")
def _init_db_for_api_suite() -> None:
    """
    CRITICAL: Import core.models here to ensure models are registered with the canonical Base
    before any tests run. This prevents dual-Base issues.
    """
    import core.db as core_db
    import core.models  # noqa: F401  # ✅ Обеспечивает регистрацию моделей с Base

    # Initialize DB if not already initialized
    core_db.init_db()
```

### Почему это важно
- Модели должны быть импортированы до `init_db()`, чтобы зарегистрироваться с `Base.metadata`
- Если модели импортируются позже, они могут использовать другой `Base` (dual-Base)
- Явный импорт в session fixture гарантирует порядок: модели → Base → init_db

---

## 7. Удаление `SessionLocal.configure(bind=None)` из teardown

### Проблема
В `configure_sqlite_database` fixture был код:
```python
# In teardown:
if db_module_reloaded.SessionLocal is not None:
    db_module_reloaded.SessionLocal.configure(bind=None)  # ❌ Ломает SessionLocal!
```

### Почему это плохо
- `configure(bind=None)` убирает привязку к engine
- После этого `SessionLocal()` не может создать сессию
- API тесты в teardown пытаются использовать `SessionLocal()` → получают ошибку

### Решение
Убрали `configure(bind=None)`, достаточно dispose engine:
```python
# NOTE: Do not clear SessionLocal binding - it breaks API tests that expect
# SessionLocal to be available in teardown. Engine disposal is sufficient cleanup.
```

### Почему это важно
- API тесты ожидают, что `SessionLocal` доступен в teardown для очистки данных
- `dispose()` engine достаточно для cleanup — не нужно трогать `SessionLocal`
- Это гарантирует, что API тесты могут безопасно использовать `SessionLocal` в teardown

---

## 8. Динамический импорт `SessionLocal` в API тестах

### Проблема
Импорт на уровне модуля:
```python
from core.db import SessionLocal  # ❌ Кэширует значение на момент импорта

class TestNutritionLogAPI:
    def teardown_method(self):
        if SessionLocal is None:  # Проверяет старое значение!
            raise AssertionError(...)
```

### Почему это плохо
- При импорте модуля `SessionLocal` может быть `None` (БД ещё не инициализирована)
- Python кэширует это значение в переменной модуля
- Даже если позже `_init_db_for_api_suite` установит `SessionLocal`, переменная в тесте останется `None`

### Решение
Динамический импорт в teardown:
```python
# Убрали импорт на уровне модуля
# from core.db import SessionLocal  # ❌ Убрали

class TestNutritionLogAPI:
    def teardown_method(self):
        # Импортируем динамически - получаем текущее значение
        from core.db import SessionLocal  # ✅ Получаем актуальное значение

        if SessionLocal is None:
            raise AssertionError(...)
```

### Почему это важно
- Динамический импорт получает актуальное значение `SessionLocal` на момент teardown
- Гарантирует, что проверка идёт после инициализации БД
- Fail-fast подход: если `SessionLocal` всё ещё `None` → это реальный баг, который нужно исправить

---

## Итоговый эффект всех исправлений

### До исправлений
- ❌ Dual-Base проблемы (`app.models.events.Base is not core.db.Base`)
- ❌ `SessionLocal` становится `None` в API тестах
- ❌ Нестабильные тесты из-за переимпортов
- ❌ Проблемы с `pytest-xdist` (каждый worker создавал свой `Base`)

### После исправлений
- ✅ Единый `Base` для всех моделей
- ✅ Стабильный `SessionLocal` в API тестах
- ✅ Предсказуемый порядок инициализации
- ✅ Работает с `pytest-xdist` (все workers используют один `Base`)
- ✅ Чистая архитектура без reloads и sys.modules манипуляций

---

## Ключевые принципы, которые мы соблюли

1. **Single Source of Truth**: `Base` должен быть только один, из `core.db`
2. **No Module Reloads**: Переимпорт модулей создаёт новые классы, даже если код тот же
3. **Protect Core Modules**: `core.*` модули не должны удаляться из `sys.modules`
4. **Explicit Initialization**: БД инициализируется явно в session fixture, не в `pytest_configure`
5. **Dynamic Imports When Needed**: Для значений, которые меняются после импорта модуля, используем динамический импорт
