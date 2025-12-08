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
git commit --dry-run
```

**Преимущества:**
- 🎯 Все проверки в одном месте
- 🚀 Работает автоматически
- 🔧 Легко настроить
