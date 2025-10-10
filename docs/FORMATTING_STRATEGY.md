# Formatting Strategy: Ruff Only

## Проблема

При одновременном использовании **Black** и **Ruff** для форматирования возникал циклический конфликт:

- Black форматировал код → Ruff переформатировал → Black снова менял → бесконечный цикл
- Это блокировало push в Git и вызывало проблемы в CI/CD

## Решение: Используем только Ruff

**Ruff** полностью заменяет три инструмента:

- ✅ **Black** → `ruff format` (100% совместим с Black)
- ✅ **flake8** → `ruff check` (быстрее и мощнее)
- ✅ **isort** → `ruff check --fix` (с автофиксом импортов)

### Преимущества Ruff

1. **В 10-100x быстрее** чем Black + flake8 + isort вместе взятые
2. **Одна конфигурация** в `pyproject.toml` для всего
3. **Нет конфликтов** - один инструмент = одна логика
4. **Полная совместимость** с Black-стилем
5. **Активная разработка** и поддержка (Astral)

## Конфигурация

### pyproject.toml

```toml
# Note: We use Ruff for both linting AND formatting (replaces Black + flake8 + isort)
# DO NOT add [tool.black] config - it will conflict with Ruff formatter

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.format]
# Use black-compatible formatting
quote-style = "double"
indent-style = "space"
line-ending = "auto"

[tool.isort]
profile = "black"  # Keep for compatibility, but Ruff handles imports
line_length = 100
```

### Команды

```bash
# Форматирование
ruff format .

# Lint + автофикс
ruff check --fix .

# Только проверка (CI/CD)
ruff format --check .
ruff check .

# Полный цикл (format + lint)
make fmt
```

### Pre-commit hooks

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.9
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

## Удалённые зависимости

Следующие пакеты **удалены** из `requirements-all.txt`:

- ❌ `black>=24.0` → заменён на `ruff format`
- ❌ `flake8>=7.0` → заменён на `ruff check`

**isort** оставлен закомментированным для обратной совместимости, но Ruff полностью покрывает его функциональность.

## Миграция

### Makefile команды

```makefile
# Старое (удалено)
fmt:
 black .
 isort .

lint:
 flake8 .

# Новое (текущее)
fmt:
 ruff format .
 ruff check --fix .

lint:
 ruff check .
```

### Scripts

Все скрипты обновлены:

- `scripts/quick_check.sh`
- `scripts/check_main_branch_push.sh`
- `scripts/auto_push.sh`

### CI/CD Workflows

Обновлены:

- `.github/workflows/pr-automation.yml`
- Pre-commit hooks в `.pre-commit-config.yaml`

## Проверка конфликтов

Если у вас возникают проблемы с форматированием:

```bash
# 1. Убедитесь, что Black НЕ установлен
pip uninstall black -y

# 2. Переустановите зависимости
pip install -r requirements-all.txt

# 3. Отформатируйте всё заново
ruff format .
ruff check --fix .

# 4. Проверьте
ruff format --check .
ruff check .
```

## Почему НЕ использовать Black + Ruff вместе?

❌ **Не делайте так:**

```toml
[tool.black]
line-length = 100
target-version = ["py313"]

[tool.ruff.format]
# ...
```

**Проблемы:**

1. Black и Ruff могут по-разному форматировать edge cases
2. Возникают циклические изменения: Black → Ruff → Black...
3. Pre-commit hooks зацикливаются
4. CI/CD падает с ошибками форматирования
5. Push блокируется

✅ **Правильно:**

```toml
# Note: DO NOT add [tool.black] config
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.format]
# Black-compatible formatting
```

## Дополнительная информация

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff vs Black Performance](https://github.com/astral-sh/ruff#benchmarks)
- [Migration Guide](https://docs.astral.sh/ruff/formatter/#black-compatibility)

---

**Дата:** 10 октября 2025
**Статус:** ✅ Активно (production-ready)
**Ответственный:** PulsePlate Dev Team
