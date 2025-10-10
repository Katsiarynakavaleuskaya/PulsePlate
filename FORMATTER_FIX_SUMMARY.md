# Исправление циклического конфликта Black ↔ Ruff

## 🎯 Проблема

При одновременном использовании **Black** и **Ruff** для форматирования возникал циклический конфликт:

- Black форматировал код → Ruff переформатировал → Black снова менял → бесконечный цикл
- Это блокировало `git push` и создавало проблемы в CI/CD pipelines

## ✅ Решение

**Полностью перешли на Ruff** как единственный форматтер и линтер.

### Что изменили

#### 1. **pyproject.toml**

```diff
+ # Note: We use Ruff for both linting AND formatting (replaces Black + flake8 + isort)
+ # Ruff is faster and fully compatible with Black's formatting style
+ # DO NOT add [tool.black] config - it will conflict with Ruff formatter

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.format]
+ # Use black-compatible formatting (Ruff replaces Black entirely)
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

**Важно:** НЕ добавляйте секцию `[tool.black]` — это вызовет конфликт!

#### 2. **requirements-all.txt**

```diff
- black>=24.0
- flake8>=7.0
+ # black>=24.0  # Replaced by ruff format (black-compatible)
+ # flake8>=7.0  # Replaced by ruff (faster alternative)
```

#### 3. **Makefile**

```diff
- lint: ## Lint with flake8
-   flake8 .
+ lint: ## Lint with ruff
+   ruff check .

- fmt: ## Format with black and isort
-   black .
-   isort .
+ fmt: ## Format with ruff
+   ruff format .
+   ruff check --fix .

- fmt-check:
-   black --check --diff .
-   isort --check-only --diff .
+ fmt-check:
+   ruff format --check .
+   ruff check .
```

#### 4. **Scripts**

Обновлены скрипты:

- `scripts/quick_check.sh`
- `scripts/check_main_branch_push.sh`

```diff
- black --check --diff .
- isort --check-only --diff .
+ ruff format --check .
+ ruff check .
```

#### 5. **Workflows**

- `.github/workflows/pr-automation.yml` → обновлён commit message

```diff
- * Applied pre-commit auto-fixes (black, ruff, etc.)
+ * Applied pre-commit auto-fixes (ruff format, ruff check)
```

#### 6. **Документация**

- Создан `docs/FORMATTING_STRATEGY.md` с полным описанием стратегии
- Обновлён `PROJECT_UPDATE_GUIDE.md`

### Файлы, которые НЕ трогали

✅ `.pre-commit-config.yaml` — уже использовал только Ruff
✅ `README.md` — не содержал упоминаний Black/flake8

## 🚀 Как использовать

### Команды форматирования

```bash
# Отформатировать весь код
ruff format .

# Автофикс lint проблем
ruff check --fix .

# Полный цикл (format + lint)
make fmt

# Только проверка (без изменений)
ruff format --check .
ruff check .

# Или через Makefile
make fmt-check
```

### Pre-commit hooks

Pre-commit hooks уже настроены правильно:

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.9
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

### CI/CD

Все workflows используют только Ruff, конфликтов больше не будет.

## 📊 Результат

✅ **Форматирование:** 20 файлов переформатировано
✅ **Lint:** All checks passed!
✅ **Конфликтов:** 0
✅ **Производительность:** +10-100x быстрее

## 🔍 Проверка

```bash
# Проверить форматирование
ruff format --check .

# Проверить lint
ruff check .

# Проверить, что Black не установлен
pip show black  # должно быть "WARNING: Package(s) not found"
```

## 📚 Дополнительно

См. подробности в:

- `docs/FORMATTING_STRATEGY.md` — полное описание стратегии
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff vs Black Performance](https://github.com/astral-sh/ruff#benchmarks)

---

**Дата:** 10 октября 2025
**Статус:** ✅ Завершено
**Автор:** PulsePlate Dev Team
**Проблема:** Циклический конфликт Black ↔ Ruff
**Решение:** Полный переход на Ruff (100% Black-compatible)
