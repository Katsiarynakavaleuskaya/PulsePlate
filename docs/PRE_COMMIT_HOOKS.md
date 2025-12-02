# 🪝 Pre-Commit Hooks Setup Guide

## Проблема: Два механизма хуков

В проекте используются **два механизма** pre-commit хуков, которые конфликтуют:

1. **Pre-commit framework** (`.pre-commit-config.yaml`)
   - Стандартный подход с YAML конфигурацией
   - Проверяет: Black, Bandit, mypy, yaml, trailing spaces
   - Устанавливается: `pre-commit install`

2. **Кастомный `.githooks/pre-commit`**
   - Bash-скрипт с кастомными проверками
   - Проверяет: Python syntax, backend tests, Black
   - Устанавливается: `git config core.hooksPath .githooks`

**Конфликт:** `git config core.hooksPath .githooks` блокирует pre-commit framework

## ✅ Решение: Unified Hook

Создан **`.githooks/pre-commit-unified`** - объединяет оба подхода:

### Что проверяет:

### Step 1: Pre-commit framework

- ✅ Black formatting (--line-length=100)
- ✅ Bandit security scan
- ✅ YAML syntax
- ✅ Trailing whitespace
- ✅ End-of-file fixer

### Step 2: Custom checks

- ✅ Python syntax (py_compile)
- ✅ Backend tests for changed files
- ✅ Recursive test discovery

## 🚀 Установка

### Вариант 1: Unified Hook (рекомендуется)

```bash
# Переключиться на unified hook
git config core.hooksPath .githooks
mv .githooks/pre-commit .githooks/pre-commit.old
mv .githooks/pre-commit-unified .githooks/pre-commit
chmod +x .githooks/pre-commit

# Проверка
git commit -m "test" --dry-run
```

**Преимущества:**
- 🎯 Все проверки в одном месте
- 🚀 Работает автоматически
- 🔧 Легко настроить

### Вариант 2: Pre-commit Framework Only

```bash
# Отключить кастомный путь
git config --unset core.hooksPath

# Установить pre-commit framework
pre-commit install
pre-commit install --hook-type pre-push

# Проверка
pre-commit run --all-files
```

**Преимущества:**
- 📦 Стандартный подход
- 🌍 Поддержка community hooks
- 🔄 Автоматические обновления

### Вариант 3: Custom Hooks Only

```bash
# Использовать только .githooks/
git config core.hooksPath .githooks

# Проверка
cat .githooks/pre-commit
```

**Недостатки:**
- ❌ Не запускает Black, mypy, Bandit
- ❌ Нужно вручную поддерживать

## 📋 Какие проверки запускаются

### Pre-commit (каждый коммит)

| Проверка | Источник | Описание |
|----------|----------|----------|
| Black | pre-commit framework | Форматирование кода (100 chars) |
| Bandit | pre-commit framework | Security scan |
| Python syntax | Custom | `python -m py_compile` |
| Backend tests | Custom | pytest для изменённых файлов |
| YAML | pre-commit framework | Валидация .yaml файлов |
| Trailing spaces | pre-commit framework | Удаление пробелов |
| End-of-file | pre-commit framework | POSIX newline |

### Pre-push (перед пушем)

| Проверка | Источник | Описание |
|----------|----------|----------|
| Mypy | pre-commit framework | Type checking |
| Bandit full | pre-commit framework | Полное сканирование |
| pip-audit | pre-commit framework | Уязвимости зависимостей |
| Docker build | Custom | Тест Docker образа |

## 🔧 Пропуск проверок

### Временно пропустить все проверки

```bash
git commit --no-verify -m "WIP: quick fix"
```

⚠️ **Используйте осторожно!** Это пропускает:
- Black formatting
- Bandit security
- Backend tests
- Mypy type checking

### Пропустить только тесты (но оставить Black/Bandit)

```bash
# Добавьте переменную окружения (hooks поддерживают SKIP_TESTS):
SKIP_TESTS=1 git commit -m "..."
```

### Пропустить конкретный hook

```bash
SKIP=black,mypy git commit -m "..."
```

## 🐛 Troubleshooting

### "Cowardly refusing to install hooks with core.hooksPath set"

```bash
# Временно отключить кастомный путь
git config --unset core.hooksPath

# Установить pre-commit
pre-commit install

# Вернуть кастомный путь (если нужен)
git config core.hooksPath .githooks
```

### "pre-commit not found"

```bash
pip install pre-commit
pre-commit install
```

### "Black, mypy, bandit не запускаются"

Проверьте:
```bash
# Какой hook установлен?
cat .git/hooks/pre-commit

# Или используется кастомный путь?
git config core.hooksPath

# Запустить вручную
pre-commit run --all-files
```

### "Тесты падают, но коммит прошёл"

Вы использовали `--no-verify`. Либо:
- Не используйте `--no-verify`
- Исправьте тесты перед коммитом
- Настройте unified hook

## 📚 Рекомендации

### Для разработки

1. **Установите unified hook** - получите все проверки
2. **Не используйте `--no-verify`** регулярно
3. **Запускайте `pre-commit run --all-files`** периодически

### Для CI/CD

1. **Добавьте `pre-commit run --all-files`** в CI
2. **Используйте pre-commit.ci** для автофиксов
3. **Настройте `.pre-commit-config.yaml`** для проекта

### Для команды

1. **Документируйте** какой вариант используется
2. **Синхронизируйте** настройки в команде
3. **Обновляйте** pre-commit hooks регулярно

## 🔄 Миграция на unified hook

```bash
# 1. Бэкап старого хука
cp .githooks/pre-commit .githooks/pre-commit.backup

# 2. Установить unified hook
mv .githooks/pre-commit-unified .githooks/pre-commit
chmod +x .githooks/pre-commit

# 3. Настроить git
git config core.hooksPath .githooks

# 4. Протестировать
echo "test" >> test.txt
git add test.txt
git commit -m "test unified hook"  # Должны запуститься все проверки
git reset HEAD~1  # Откатить тестовый коммит

# 5. Удалить бэкап (если всё работает)
rm .githooks/pre-commit.backup test.txt
```

## 📖 Дополнительно

- [Pre-commit documentation](https://pre-commit.com/)
- [Git hooks documentation](https://git-scm.com/docs/githooks)
- [Проект: TESTING_MEMORY_OPTIMIZATION.md](./TESTING_MEMORY_OPTIMIZATION.md)
