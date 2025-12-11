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

**Advantages:**
- 🎯 All checks in a single place
- 🚀 Runs automatically
- 🔧 Easy to configure
