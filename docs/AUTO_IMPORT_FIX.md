# 🔧 Автоматическое исправление импортов и кода

**Дата:** 10 октября 2025
**Статус:** ✅ Production-ready
**Автор:** PulsePlate Dev Team

---

## 📋 Проблемы, которые решаем

### Импорты

- ❌ Неиспользуемые импорты (`import unused_module`)
- ❌ Дублирующиеся импорты
- ❌ Неправильный порядок импортов
- ❌ Отсутствующие зависимости
- ❌ Циклические импорты

### Качество кода

- ❌ Неопределённые переменные
- ❌ Дублирование объектов
- ❌ Устаревший синтаксис Python
- ❌ Ошибки типизации

---

## 🚀 Автоматизация уровней

### 1. IDE/Редактор (реал-тайм)

**VS Code/Cursor** — автоматические исправления при сохранении:

```json
// .vscode/settings.json уже настроен!
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

**Что происходит автоматически:**

- ✅ Удаляются неиспользуемые импорты
- ✅ Сортируются импорты по правилам
- ✅ Форматируется код
- ✅ Исправляются простые ошибки

### 2. Pre-commit hooks (перед коммитом)

**Настроено в `.pre-commit-config.yaml`:**

```bash
# Автоматически запускается при git commit
git commit -m "your message"

# Или вручную:
pre-commit run --all-files
```

**Проверки:**

- ✅ Ruff format (форматирование)
- ✅ Ruff lint (импорты, качество кода)
- ✅ Mypy (type checking)
- ✅ Bandit (безопасность)

### 3. Makefile команды (вручную)

```bash
# Полное форматирование + исправление импортов
make fmt

# Только проверка импортов
make check-imports

# Автоматическое исправление импортов
make fix-imports

# Lint проверка (только ruff check)
make lint

# Проверка типов с mypy
make mypy

# Проверка форматирования без изменений
make fmt-check

# Полная проверка качества (формат + lint + типы + покрытие + безопасность)
make check-all
```

### 4. Кастомный скрипт (глубокая проверка)

```bash
# Проверить все импорты в проекте
python scripts/check_imports.py

# Автоматически исправить
python scripts/check_imports.py --fix

# Проверить конкретную директорию
python scripts/check_imports.py --path core/
```

---

## 🎯 Конфигурация Ruff

### Включенные проверки

В `pyproject.toml` настроено:

```toml
[tool.ruff.lint]
select = [
  "E",   # pycodestyle errors
  "W",   # pycodestyle warnings
  "F",   # Pyflakes (импорты, неопределённые имена)
  "I",   # isort (порядок импортов)
  "N",   # pep8-naming (правильные имена)
  "UP",  # pyupgrade (современный Python)
  "B",   # flake8-bugbear (частые баги)
  "C4",  # flake8-comprehensions (улучшение list/dict comprehensions)
]

# Автоматически исправляемые
fixable = ["I", "F401", "UP", "C4"]
```

### Что Ruff исправляет автоматически

1. **Импорты (I, F401)**

   ```python
   # ❌ До
   import os
   import sys
   from typing import Dict
   import ast
   import unused_module  # не используется

   # ✅ После (автоматически)
   import ast
   import os
   import sys
   from typing import Dict
   ```

2. **Современный Python (UP)**

   ```python
   # ❌ До
   from typing import List, Dict
   def func(items: List[str]) -> Dict[str, int]:
       pass

   # ✅ После (Python 3.9+)
   def func(items: list[str]) -> dict[str, int]:
       pass
   ```

3. **Comprehensions (C4)**

   ```python
   # ❌ До
   result = list(map(lambda x: x * 2, items))

   # ✅ После
   result = [x * 2 for x in items]
   ```

---

## 🛠 Использование в разработке

### Workflow для нового кода

1. **Пишите код** — IDE автоматически исправляет при сохранении
2. **Перед коммитом:**

   ```bash
   make fmt              # Финальное форматирование
   make check-imports    # Проверка импортов
   ```

3. **Коммит:**

   ```bash
   git add .
   git commit -m "feat: новая фича"
   # Pre-commit hooks автоматически запустятся
   ```

### Исправление существующего кода

```bash
# 1. Исправить весь проект
make fix-imports
make fmt

# 2. Проверить результат
make lint        # ruff проверки
make mypy        # проверка типов
make fmt-check   # проверка форматирования

# 3. Запустить тесты
make test

# 4. Закоммитить
git add .
git commit -m "refactor: fix imports and formatting"
```

### Работа с Pull Request

GitHub Actions автоматически:

- ✅ Проверяет импорты
- ✅ Проверяет форматирование
- ✅ Запускает линтеры
- ✅ Блокирует merge при ошибках

---

## 📊 Примеры автоматических исправлений

### Пример 1: Неиспользуемые импорты

```python
# ❌ До
from typing import Dict, List, Optional, Tuple
import os
import sys
import json

def process_data(data: Dict) -> List:
    return list(data.values())

# ✅ После (автоматически удалены)
from typing import Dict, List

def process_data(data: Dict) -> List:
    return list(data.values())
```

### Пример 2: Дублирование импортов

```python
# ❌ До
from app.models import User
from core.db import get_session
from app.models import User  # дубликат!

# ✅ После (автоматически)
from app.models import User
from core.db import get_session
```

### Пример 3: Неправильный порядок

```python
# ❌ До
from app.models import User
import os
from typing import Dict
import sys
from core.db import get_session

# ✅ После (автоматически)
import os
import sys
from typing import Dict

from app.models import User
from core.db import get_session
```

### Пример 4: Отсутствующие импорты

**Ruff покажет ошибку:**

```
core/metabolism.py:45:12: F821 Undefined name `calculate_bmr`
```

**Решение:**

```python
# Добавить импорт
from core.metabolism import calculate_bmr
```

---

## 🔍 Проверка типов (Mypy)

### Автоматическая проверка типов

```bash
# Проверить типы
mypy core/ app/

# Или через Makefile
make typecheck  # если добавим команду
```

### Частые проблемы и решения

**Проблема: Missing import**

```python
# ❌ Ошибка
from openai import APITimeoutError  # не найден

# ✅ Решение
# 1. Проверить установку: pip list | grep openai
# 2. Добавить в requirements.txt
# 3. Или добавить type: ignore если это известная проблема
from openai import APITimeoutError  # type: ignore
```

**Проблема: Circular import**

```python
# ❌ Ошибка
# file_a.py
from file_b import function_b

# file_b.py
from file_a import function_a  # цикл!

# ✅ Решение: использовать TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from file_a import function_a
```

---

## 🎓 Best Practices

### 1. Порядок импортов

```python
# 1. Стандартная библиотека
import os
import sys
from typing import Dict, List

# 2. Сторонние библиотеки
import numpy as np
from fastapi import FastAPI
from sqlalchemy import create_engine

# 3. Локальные модули
from core.db import get_session
from core.models import User
from app.routers import health
```

### 2. Группировка импортов

```python
# ✅ Хорошо: логическая группировка
from typing import Dict, List, Optional  # типы вместе

from core.db import get_session
from core.models import User, Product  # модели вместе

# ❌ Плохо: хаотичный порядок
from core.models import User
from typing import Dict
from core.db import get_session
from typing import List
```

### 3. Избегайте `import *`

```python
# ❌ Плохо
from core.models import *

# ✅ Хорошо: явные импорты
from core.models import User, Product, Order
```

### 4. Используйте TYPE_CHECKING для циклов

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from circular_module import CircularClass

def my_function(obj: "CircularClass") -> None:
    # Используем строку для аннотации
    pass
```

---

## 🚨 Troubleshooting

### Проблема: Ruff не находит неиспользуемые импорты

```bash
# Убедитесь, что F401 включен
ruff check --select F401 .

# Проверьте pyproject.toml
[tool.ruff.lint]
select = ["F401"]
```

### Проблема: Pre-commit зацикливается

```bash
# Очистите кеш
pre-commit clean

# Переустановите hooks
pre-commit install --install-hooks --overwrite
```

### Проблема: Mypy жалуется на типы

```bash
# Установите типы для библиотек
mypy --install-types --non-interactive

# Или добавьте в ignore
# pyproject.toml
[tool.mypy]
ignore_missing_imports = true
```

---

## 📚 Дополнительная информация

### Документация

- [Ruff Rules](https://docs.astral.sh/ruff/rules/)
- [Ruff Configuration](https://docs.astral.sh/ruff/configuration/)
- [Mypy Documentation](https://mypy.readthedocs.io/)

### Команды для справки

```bash
# Показать все доступные правила Ruff
ruff linter

# Показать информацию о конкретном правиле
ruff rule F401

# Показать что будет исправлено (dry-run)
ruff check --fix --diff .

# Игнорировать конкретное правило в файле
# В начале файла:
# ruff: noqa: F401

# Игнорировать в конкретной строке:
import unused  # noqa: F401
```

---

## ✅ Checklist для разработчика

Перед каждым коммитом:

- [ ] `make fmt` — форматирование
- [ ] `make check-imports` — проверка импортов
- [ ] `make lint` — проверка качества (ruff)
- [ ] `make mypy` — проверка типов
- [ ] `make test` — тесты проходят
- [ ] IDE не показывает ошибок
- [ ] Pre-commit hooks прошли

Быстрая полная проверка:

- [ ] `make check-all` — запускает fmt-check + lint + mypy + cov-check + security

Перед Pull Request:

- [ ] Все тесты проходят
- [ ] Coverage ≥ 97%
- [ ] Нет новых lint ошибок
- [ ] Импорты чистые и упорядоченные
- [ ] Документация обновлена

---

**Статус:** ✅ Все автоматизировано и готово к использованию!
**Поддержка:** Все инструменты настроены и работают автоматически
