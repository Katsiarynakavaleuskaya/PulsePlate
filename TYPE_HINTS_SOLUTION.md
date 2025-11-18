# ✅ Решение проблемы с missing type hints

## Проблема

Постоянные проблемы с отсутствующими type hints возникали из-за:

1. Отсутствия автоматической проверки в CI/CD
2. Недостаточно строгих настроек mypy и ruff
3. Отсутствия автоматического исправления

## Решение

### 1. ✅ Автоматическая проверка через Ruff

Добавлены правила `ANN` для проверки type hints:

- `ANN001`: Missing type annotation for function argument
- `ANN201`: Missing return type annotation for public function
- `ANN202`: Missing return type annotation for private function
- `ANN204`: Missing return type annotation for special method
- `ANN205`: Missing type annotation for `*args`
- `ANN206`: Missing type annotation for `**kwargs`

**Настройки в `pyproject.toml`:**

```toml
[tool.ruff.lint]
select = ["E", "W", "F", "ANN"]  # Добавлен ANN
ignore = [
    "ANN101",  # self в методах
    "ANN102",  # cls в classmethod
]
```

### 2. ✅ Улучшенная проверка через Mypy

Добавлены более строгие проверки:

- `warn_no_return`: Предупреждает о функциях без return
- `check_untyped_defs`: Проверяет функции без type hints
- `warn_unreachable`: Предупреждает о недостижимом коде

### 3. ✅ Автоматическое исправление

Создан скрипт `scripts/add_type_hints.py` для автоматического добавления `-> None`:

```bash
# Показать что будет изменено
python scripts/add_type_hints.py app/ core/ --dry-run

# Применить изменения
python scripts/add_type_hints.py app/ core/
```

### 4. ✅ Pre-commit хуки

Добавлен ruff hook для проверки type hints на этапе pre-push:

- Проверяет все Python файлы
- Автоматически исправляет простые случаи и
- Блокирует push при наличии проблем

### 4. ✅ Pre-commit хуки

Добавлен ruff hook для проверки type hints на этапе pre-push:

- Проверяет все Python файлы
- Автоматически исправляет простые случаи и
- Блокирует push при наличии проблем

Добавлен ruff hook для проверки type hints на этапе pre-push:

- Проверяет все Python файлы
- Автоматически исправляет простые случаи и
- Блокирует push при наличии проблем

## Использование

### Проверка локально

```bash
# Проверка через ruff
ruff check . --select ANN

# Автоматическое исправление
ruff check . --select ANN --fix

# Использование скрипта
python scripts/add_type_hints.py app/ core/ --dry-run
```

### CI/CD

Type hints теперь проверяются автоматически:

- **Pre-commit**: Ruff проверяет и исправляет простые случаи
- **Pre-push**: Ruff строго проверяет type hints
- **CI**: Mypy проверяет типы в полном объеме

## Документация

Полная документация доступна в `docs/TYPE_HINTS_GUIDE.md`:

- Правила и рекомендации
- Примеры использования
- Частые проблемы и решения
- Миграция существующего кода

## Результат

Теперь проблемы с missing type hints будут:

1. ✅ Автоматически обнаруживаться через ruff
2. ✅ Автоматически исправляться где возможно
3. ✅ Блокировать push при наличии проблем
4. ✅ Проверяться в CI/CD

## Следующие шаги

1. Запустите проверку существующего кода:

   ```bash
   ruff check . --select ANN
   ```

2. Исправьте найденные проблемы автоматически:

   ```bash
   python scripts/add_type_hints.py app/ core/
   ```

3. Проверьте через mypy:

   ```bash
   mypy app/ core/
   ```
