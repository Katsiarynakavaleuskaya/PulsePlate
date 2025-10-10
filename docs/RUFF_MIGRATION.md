# 🔄 Миграция на новый Ruff Server

**Дата:** 10 октября 2025
**Причина:** Устаревание ruff-lsp, переход на встроенный Ruff server

---

## ⚠️ Что изменилось

### Старый способ (ruff-lsp) — УСТАРЕЛ

```json
{
  "ruff.lint.run": "onType",  // ❌ Больше не поддерживается
  "ruff.lint.args": [...],    // ❌ Больше не поддерживается
  "ruff.lint.enable": true,   // ❌ Больше не нужно
  "ruff.format.enable": true  // ❌ Больше не нужно
}
```

### Новый способ (встроенный Ruff server) — ✅ АКТУАЛЬНО

```json
{
  "ruff.enable": true,
  "ruff.organizeImports": true,
  "ruff.fixAll": true,

  // Все настройки берутся из pyproject.toml
  // Не нужно дублировать конфигурацию!
}
```

---

## 🚀 Миграция

### Шаг 1: Обновите Ruff расширение

В VS Code/Cursor:

1. Откройте Extensions (⌘+Shift+X)
2. Найдите "Ruff"
3. Обновите до последней версии (v2024.x или новее)

### Шаг 2: Удалите старые настройки

Удалите из `.vscode/settings.json`:

- ❌ `ruff.lint.run`
- ❌ `ruff.lint.args`
- ❌ `ruff.lint.enable`
- ❌ `ruff.format.enable`

### Шаг 3: Добавьте минимальные настройки

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.organizeImports": true,
  "ruff.fixAll": true
}
```

### Шаг 4: Вся конфигурация в pyproject.toml

**Всё остальное настраивается в `pyproject.toml`!**

```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4"]
fixable = ["I", "F401", "UP", "C4"]

[tool.ruff.lint.isort]
known-first-party = ["core", "app", "providers"]
```

---

## 📚 Преимущества нового сервера

### 1. Единая конфигурация

**Было (дублирование):**

```json
// .vscode/settings.json
"ruff.lint.args": ["--select=E,W,F,I"]

// pyproject.toml
select = ["E", "W", "F", "I"]
```

**Стало (один источник истины):**

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["E", "W", "F", "I"]
```

### 2. Автоматическое обнаружение

Ruff автоматически находит и читает `pyproject.toml`:

- ✅ Нет дублирования настроек
- ✅ Одинаковое поведение в IDE и CI
- ✅ Легче поддерживать

### 3. Быстрее работает

Новый встроенный сервер:

- ⚡ Быстрее запускается
- ⚡ Меньше потребляет памяти
- ⚡ Лучше интеграция с IDE

---

## 🔍 Проверка миграции

### Проверьте что всё работает

1. **Откройте Python файл**
2. **Внесите ошибку:**

   ```python
   import unused_module  # должна подсветиться
   ```

3. **Сохраните файл** (⌘+S)
4. **Проверьте:**
   - ✅ Импорт должен исчезнуть
   - ✅ Код отформатирован
   - ✅ Нет ошибок в Output → Ruff

### Если что-то не работает

```bash
# 1. Перезагрузите VS Code/Cursor
# 2. Проверьте что Ruff установлен
ruff --version

# 3. Проверьте pyproject.toml
ruff check --config pyproject.toml .

# 4. Откройте Output → Ruff в IDE
# Там будут логи работы сервера
```

---

## 📖 Дополнительная информация

- [Официальная миграция Ruff](https://docs.astral.sh/ruff/editors/migration/)
- [GitHub Discussion](https://github.com/astral-sh/ruff/discussions/15991)
- [Ruff Editor Integration](https://docs.astral.sh/ruff/editors/)

---

## ✅ Checklist миграции

- [x] Обновлён Ruff до последней версии
- [x] Удалены устаревшие настройки из `.vscode/settings.json`
- [x] Добавлены новые минимальные настройки
- [x] Вся конфигурация в `pyproject.toml`
- [x] Проверено форматирование при сохранении
- [x] Проверена организация импортов
- [x] Проверен авто-фикс ошибок

**Статус:** ✅ Миграция завершена!
