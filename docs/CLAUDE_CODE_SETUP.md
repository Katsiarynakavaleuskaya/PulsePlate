# 🤖 Claude Code CLI - Правильная Настройка

**Дата**: 2025-01-09
**Статус**: Готово к использованию

---

## ✅ Что было исправлено

### **Проблема #1: Cursor вылетал из-за невалидных AI моделей**

**Удалены проблемные файлы:**
- ❌ `.cursor-settings.json` → `.cursor-settings.json.backup`
  - Содержал несуществующие модели: `gpt-5`, `codex`, `grok-3`
  - Использовал placeholder API ключи
- ❌ `.cursor-priorities.md` → `.cursor-priorities.md.backup`

### **Проблема #2: Конфликты AI расширений**

**Удалены из `.vscode/settings.json`:**
- ❌ `coderabbit.agentType: "Native"`
- ❌ `coderabbit.autoReviewMode: "auto"`
- ❌ `claudeCodeChat.permissions.yoloMode: true`
- ❌ `github.copilot.nextEditSuggestions.enabled: true`
- ❌ `MutableAI.upsell: true`
- ❌ Избыточные `workbench.editor.*` настройки

**Причина**: Множественные AI расширения конфликтовали и ели память.

---

## 🚀 Как правильно подключить Claude Code к проекту

### **Вариант 1: Через Web интерфейс (РЕКОМЕНДУЮ)**

1. Открыть проект в браузере: https://claude.ai/code
2. Нажать **"Open Repository"**
3. Выбрать `PulsePlate` из списка GitHub репозиториев
4. Claude Code автоматически:
   - Индексирует весь проект
   - Понимает структуру кода
   - Готов к работе

**Преимущества**:
- ✅ Не использует локальную память
- ✅ Работает в облаке (быстро)
- ✅ Нет конфликтов с Cursor

---

### **Вариант 2: Через CLI (для продвинутых)**

```bash
# 1. Установить Claude Code CLI (если еще не установлен)
npm install -g @anthropic-ai/claude-code

# 2. Войти в аккаунт
claude login

# 3. Инициализировать в проекте
cd /path/to/PulsePlate
claude init

# 4. Настроить контекст (опционально)
claude settings

# 5. Запустить сессию
claude chat
```

**Важно**: CLI требует Node.js >= 18.x

---

### **Вариант 3: Через Cursor (ПОСЛЕ ИСПРАВЛЕНИЯ)**

1. **Закрыть Cursor полностью** (Quit, не просто закрыть окно)
2. **Очистить кэш Cursor**:
   ```bash
   # macOS/Linux
   rm -rf ~/.cursor/Cache
   rm -rf ~/.cursor/Code\ Cache

   # Windows
   rmdir /s %APPDATA%\Cursor\Cache
   rmdir /s %APPDATA%\Cursor\Code Cache
   ```
3. **Перезапустить Cursor**
4. **Проверить память**: `Activity Monitor` (macOS) / `Task Manager` (Windows)
   - Cursor должен использовать < 1GB RAM
   - Если > 2GB → перезапустить заново

5. **Настроить AI в Cursor** (Settings → Features):
   ```json
   {
     "cursor.ai.enabled": false,  // ОТКЛЮЧИТЬ встроенный AI!
     "cursor.ai.autoComplete": false
   }
   ```

6. **Использовать внешний Claude Code**:
   - Открыть терминал в Cursor
   - Запустить `claude chat`

---

## 🧹 Как освободить память в Cursor

### **Симптомы проблемы:**
- Cursor использует > 2GB RAM
- Компьютер использует swap память
- Cursor тормозит/вылетает
- Ошибки "Out of memory"

### **Решение:**

#### **1. Отключить встроенный AI Cursor**
Settings → Features → отключить:
- ❌ Cursor Tab (AI autocomplete)
- ❌ Cursor Chat
- ❌ Cursor Command K

#### **2. Отключить расширения**
Extensions → Отключить:
- ❌ GitHub Copilot
- ❌ CodeRabbit
- ❌ Tabnine
- ❌ Codeium
- ❌ Любые другие AI расширения

**Оставить только**:
- ✅ Python (Microsoft)
- ✅ Pylance
- ✅ Black Formatter
- ✅ Ruff

#### **3. Ограничить индексацию**

Settings → Search → исключить:
```json
{
  "files.watcherExclude": {
    "**/.git/**": true,
    "**/.venv/**": true,
    "**/node_modules/**": true,
    "**/__pycache__/**": true,
    "**/.pytest_cache/**": true,
    "**/.ruff_cache/**": true,
    "**/.mypy_cache/**": true,
    "**/cache/**": true,
    "**/test_cache/**": true
  },
  "search.exclude": {
    "**/.venv/**": true,
    "**/node_modules/**": true,
    "**/__pycache__/**": true
  }
}
```

#### **4. Очистить кэш регулярно**

Добавить в `.gitignore`:
```
# Cursor/VSCode cache
.vscode/.ropeproject
.vscode-server
.cursor/
```

Скрипт для очистки (создать `scripts/clean_cursor_cache.sh`):
```bash
#!/bin/bash
echo "Cleaning Cursor cache..."
rm -rf ~/.cursor/Cache
rm -rf ~/.cursor/Code\ Cache
rm -rf ~/.cursor/CachedData
echo "✅ Cache cleared!"
```

---

## 📊 Проверка системы после исправления

### **Команды для проверки:**

```bash
# 1. Проверить использование памяти
free -h  # Linux
top      # macOS

# 2. Проверить процессы Cursor
ps aux | grep -i cursor

# 3. Проверить размер кэша
du -sh ~/.cursor/Cache

# 4. Проверить git статус
git status

# 5. Проверить конфигурацию
cat .vscode/settings.json
```

### **Нормальные значения:**
- Cursor RAM: 500MB - 1.5GB
- Cursor Cache: < 500MB
- Swap usage: 0% (не используется)

### **Проблемные значения:**
- ❌ Cursor RAM > 2GB → перезапустить
- ❌ Cursor Cache > 1GB → очистить
- ❌ Swap > 10% → закрыть другие приложения

---

## 🎯 Рекомендуемый workflow

### **Для ежедневной работы:**

1. **Cursor** - только для редактирования кода
   - AI функции ОТКЛЮЧЕНЫ
   - Используется как легкий редактор

2. **Claude Code Web** - для AI помощи
   - https://claude.ai/code
   - Открыть проект PulsePlate
   - Задавать вопросы, генерировать код
   - Копировать результаты в Cursor

3. **Claude Code CLI** - для автоматизации
   - Запускать в терминале
   - Использовать для batch операций
   - Интеграция с git workflow

### **Преимущества:**
- ✅ Cursor быстрый и легкий
- ✅ Claude Code не грузит локальную память
- ✅ Нет конфликтов между AI
- ✅ Лучшее качество AI (Claude Sonnet 4.5)

---

## ❓ FAQ

### **Q: Почему нельзя использовать AI в Cursor?**
A: Можно, но это ест много памяти. Встроенный AI Cursor использует ~2GB RAM постоянно. Claude Code Web работает в облаке - не грузит ваш компьютер.

### **Q: Как переключиться между Cursor и Claude Code?**
A: Редактируйте код в Cursor, когда нужна AI помощь - переключайтесь на Claude Code Web или CLI.

### **Q: Можно ли использовать Copilot вместе с Claude Code?**
A: Нет, они конфликтуют и удваивают использование памяти. Выберите один инструмент.

### **Q: Почему удалили `.cursor-settings.json`?**
A: Там были несуществующие AI модели (`gpt-5`, `codex`, `grok-3`), которые вызывали краш при инициализации.

### **Q: Как вернуть старые настройки?**
A: Бэкапы сохранены:
- `.cursor-settings.json.backup`
- `.cursor-priorities.md.backup`

Но **не рекомендую** - они вызывают проблемы.

---

## 🔗 Полезные ссылки

- [Claude Code Documentation](https://docs.claude.com/code)
- [Cursor Documentation](https://cursor.sh/docs)
- [PulsePlate README](../README.md)
- [Bayesian Expansion Strategy](./BAYESIAN_EXPANSION_STRATEGY.md)

---

**Статус**: ✅ Конфигурация исправлена
**Следующий шаг**: Перезапустить Cursor и проверить использование памяти
