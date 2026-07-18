### Вариант 1: Unified Hook (рекомендуется)

Для установки рекомендуемого unified hook, выполните следующие команды:

```bash
# Скопировать unified hook в место назначения
cp .githooks/pre-commit-unified .githooks/pre-commit

# Сделать его исполняемым
chmod +x .githooks/pre-commit

# Настроить git для использования директории с хуками
git config core.hooksPath .githooks

# Проверить, что хук работает правильно
# Запустить хук напрямую для проверки
.githooks/pre-commit
```

Хуки из репозитория выбирают Python через `scripts/hooks/repo_python.sh`.
Точный приоритет: корректный абсолютный исполняемый файл `VENV_PYTHON`
(иначе `DEV_PYTHON`), `.venv` текущего checkout, затем `.venv` основного
checkout. Некорректный явно заданный override — terminal error: resolver не
переходит к следующему кандидату. Основной checkout определяется не по имени
каталога: resolver канонизирует Git common dir, требует basename `.git` и
повторно проверяет в основном checkout те же canonical top-level и common dir.
Поэтому linked worktree может находиться в любой вложенной, соседней или
внешней директории, а bare/separate/подставная `.git` layout отклоняется.
Только CI может перейти к системному `python3`/`python`; локально отсутствие
доверенного Python завершает hook с ошибкой. Запускайте Python-инструменты
через выбранный interpreter (`python -m ...`), чтобы hook не использовал
ambient environment без locked dependencies, например FastAPI.

**Преимущества:**
- 🎯 Все проверки в одном месте
- 🚀 Работает автоматически
- 🔧 Легко настроить

---

### Option 1: Unified Hook (recommended)

To install the recommended unified hook, run the following commands:

```bash
# Copy the unified hook to the destination
cp .githooks/pre-commit-unified .githooks/pre-commit

# Make it executable
chmod +x .githooks/pre-commit

# Configure git to use the hooks directory
git config core.hooksPath .githooks

# Verify that the hook is working correctly
# Run the hook directly for a quick check
.githooks/pre-commit
```

Checked-in hooks resolve Python through `scripts/hooks/repo_python.sh`.
The exact precedence is a valid absolute regular executable `VENV_PYTHON`
(otherwise `DEV_PYTHON`), the current checkout `.venv`, then the primary
checkout `.venv`. An invalid explicitly configured override is terminal; the
resolver does not continue to another candidate. The primary checkout is not
inferred from a directory name: the resolver canonicalizes Git's common dir,
requires basename `.git`, and revalidates the same canonical top-level and
common dir from the primary checkout. Linked worktrees may therefore live in
nested, sibling, or arbitrary external directories, while bare, separate, and
decoy `.git` layouts are rejected. Only CI may fall back to system
`python3`/`python`; local execution fails closed without a trusted interpreter.
Keep Python tools behind the resolved interpreter (`python -m ...`) so hooks
cannot drift into an ambient environment missing locked dependencies such as
FastAPI.

**Advantages:**
- 🎯 All checks in a single place
- 🚀 Runs automatically
- 🔧 Easy to configure
