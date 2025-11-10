# Type Hints Guide

## Обзор

Этот документ описывает политику и инструменты для обеспечения наличия type hints во всех функциях проекта.

## Проблема

Постоянные проблемы с missing type hints возникают из-за:
1. Отсутствия автоматической проверки в CI/CD
2. Недостаточно строгих настроек mypy и ruff
3. Отсутствия автоматического исправления

## Решение

### 1. Автоматическая проверка через Ruff

Ruff теперь проверяет type hints через правила `ANN`:
- `ANN001`: Missing type annotation for function argument
- `ANN201`: Missing return type annotation for public function
- `ANN202`: Missing return type annotation for private function
- `ANN204`: Missing return type annotation for special method
- `ANN205`: Missing type annotation for `*args`
- `ANN206`: Missing type annotation for `**kwargs`

**Настройки в `pyproject.toml`:**
```toml
[tool.ruff.lint]
select = ["E", "W", "F", "ANN"]  # Добавлен ANN для проверки аннотаций
ignore = [
    "ANN101",  # self в методах (игнорируем)
    "ANN102",  # cls в classmethod (игнорируем)
]
```

### 2. Улучшенная проверка через Mypy

Mypy теперь более строго проверяет type hints:
- `warn_no_return`: Предупреждает о функциях без return
- `check_untyped_defs`: Проверяет функции без type hints
- `disallow_untyped_defs`: Можно включить для строгой проверки

### 3. Автоматическое исправление

Скрипт `scripts/add_type_hints.py` автоматически добавляет `-> None` к функциям без return type hints.

**Использование:**
```bash
# Показать что будет изменено (dry-run)
python scripts/add_type_hints.py app/ core/ --dry-run

# Применить изменения
python scripts/add_type_hints.py app/ core/

# Обработать конкретный файл
python scripts/add_type_hints.py app/routers/foods.py
```

### 4. Pre-commit хуки

Добавлен ruff hook для проверки type hints на этапе pre-push:
- Проверяет все Python файлы
- Автоматически исправляет простые случаи
- Блокирует push при наличии проблем

## Правила

### Обязательные type hints

1. **Все публичные функции** должны иметь return type hints:
   ```python
   def public_function() -> None:  # ✅ Правильно
       pass

   def public_function():  # ❌ Неправильно
       pass
   ```

2. **Все async функции** должны иметь return type hints:
   ```python
   async def async_function() -> None:  # ✅ Правильно
       pass
   ```

3. **Функции с return значениями** должны иметь соответствующий тип:
   ```python
   def get_value() -> str:  # ✅ Правильно
       return "value"

   def get_value():  # ❌ Неправильно
       return "value"
   ```

### Исключения

1. **Тесты** (`tests/*.py`): Игнорируется `ANN201` для тестовых функций
2. **Скрипты** (`scripts/*.py`): Игнорируется `ANN201` для утилит
3. **Releases** (`releases/**/*.py`): Игнорируется `ANN201` для релизных файлов

### Рекомендации

1. **Используйте `-> None`** для функций без return:
   ```python
   def setup() -> None:
       # setup code
   ```

2. **Используйте `typing` модуль** для сложных типов:
   ```python
   from typing import List, Dict, Optional

   def process_data(items: List[str]) -> Dict[str, int]:
       # processing
   ```

3. **Используйте `collections.abc`** для абстрактных типов (Python 3.9+):
   ```python
   from collections.abc import Iterator

   def generate() -> Iterator[int]:
       yield 1
   ```

## Проверка

### Локальная проверка

```bash
# Проверка через ruff
ruff check . --select ANN

# Проверка через mypy
mypy app/ core/

# Автоматическое исправление через ruff
ruff check . --select ANN --fix
```

### CI/CD проверка

Type hints проверяются автоматически:
- **Pre-commit**: Ruff проверяет и исправляет простые случаи
- **Pre-push**: Ruff строго проверяет type hints
- **CI**: Mypy проверяет типы в полном объеме

## Миграция существующего кода

Для добавления type hints к существующему коду:

1. **Запустите скрипт автоматического исправления:**
   ```bash
   python scripts/add_type_hints.py app/ core/ --dry-run
   python scripts/add_type_hints.py app/ core/
   ```

2. **Проверьте через ruff:**
   ```bash
   ruff check . --select ANN
   ```

3. **Исправьте оставшиеся проблемы вручную**

4. **Проверьте через mypy:**
   ```bash
   mypy app/ core/
   ```

## Частые проблемы и решения

### Проблема: "Missing return type annotation"

**Решение:** Добавьте `-> None` или соответствующий тип:
```python
# Было:
def my_function():
    pass

# Стало:
def my_function() -> None:
    pass
```

### Проблема: "Missing type annotation for function argument"

**Решение:** Добавьте type hints к аргументам:
```python
# Было:
def process(data):
    return data.upper()

# Стало:
def process(data: str) -> str:
    return data.upper()
```

### Проблема: "Missing type annotation for `*args`"

**Решение:** Используйте `*args: str` или `*args: Any`:
```python
# Было:
def process(*args):
    pass

# Стало:
from typing import Any
def process(*args: Any) -> None:
    pass
```

## Дополнительные ресурсы

- [Python Type Hints PEP 484](https://www.python.org/dev/peps/pep-0484/)
- [Ruff ANN Rules](https://docs.astral.sh/ruff/rules/#flake8-annotations-ann)
- [Mypy Documentation](https://mypy.readthedocs.io/)
