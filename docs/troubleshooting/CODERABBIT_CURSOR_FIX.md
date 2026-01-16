# 🔧 Исправление проблемы CodeRabbit в Cursor: черное окно

**Проблема:** CodeRabbit ревью запускается, но файлы не загружаются - черное окно.

---

## 🔍 Диагностика

### Шаг 1: Проверьте расширение CodeRabbit

1. Откройте Cursor
2. Нажмите `Cmd+Shift+X` (или View → Extensions)
3. Найдите "CodeRabbit" или "CodeRabbit AI"
4. Проверьте:
   - ✅ Расширение установлено
   - ✅ Расширение включено (Enabled)
   - ✅ Нет ошибок в статусе

### Шаг 2: Проверьте аутентификацию

CodeRabbit требует аутентификацию через GitHub или API токен.

**Проверка через Command Palette:**

1. Нажмите `Cmd+Shift+P` (Command Palette)
2. Введите: `CodeRabbit: Sign In` или `CodeRabbit: Authenticate`
3. Следуйте инструкциям для входа

**Альтернатива - через настройки:**

1. `Cmd+,` (Settings)
2. Найдите `coderabbit` в поиске
3. Проверьте настройки:
   - `coderabbit.apiKey` - должен быть установлен
   - `coderabbit.enabled` - должен быть `true`

### Шаг 3: Проверьте логи расширения

1. `Cmd+Shift+P` → `Developer: Show Logs...`
2. Выберите `CodeRabbit` или `Extension Host`
3. Ищите ошибки:
   - `Authentication failed`
   - `API error`
   - `Failed to load`
   - `Network error`

### Шаг 4: Проверьте конфигурацию проекта

Убедитесь, что `.coderabbit.yaml` правильно настроен:

```yaml
# .coderabbit.yaml должен быть в корне проекта
language: en-US
reviews:
  profile: chill
```

---

## 🛠 Решения

### Решение 1: Переустановка расширения

1. `Cmd+Shift+X` → найдите CodeRabbit
2. Нажмите "Uninstall"
3. Перезапустите Cursor
4. Установите расширение заново
5. Аутентифицируйтесь снова

### Решение 2: Очистка кэша и storage

```bash
# Закройте Cursor полностью

# Очистите storage CodeRabbit
rm -rf ~/Library/Application\ Support/Cursor/User/globalStorage/*coderabbit*

# Очистите кэш
rm -rf ~/Library/Application\ Support/Cursor/Cache/*

# Перезапустите Cursor
```

### Решение 3: Проверка API токена

Если CodeRabbit использует API токен:

1. Откройте настройки: `Cmd+,`
2. Найдите `coderabbit.apiKey`
3. Если токен установлен, попробуйте:
   - Удалить токен
   - Сохранить настройки
   - Перезапустить Cursor
   - Установить токен заново

### Решение 4: Проверка сетевого подключения

CodeRabbit требует доступ к API:

1. Проверьте интернет-соединение
2. Проверьте, не блокирует ли firewall/прокси запросы
3. Попробуйте отключить VPN (если используется)

### Решение 5: Обновление расширения

1. `Cmd+Shift+X` → CodeRabbit
2. Проверьте, есть ли обновления
3. Обновите до последней версии
4. Перезапустите Cursor

### Решение 6: Проверка прав доступа

Убедитесь, что Cursor имеет доступ к:
- Файловой системе (для чтения файлов проекта)
- Сети (для API запросов)

**macOS:**
- System Settings → Privacy & Security → Files and Folders
- Убедитесь, что Cursor имеет доступ к нужным папкам

---

## 🔄 Альтернативные способы использования CodeRabbit

### Вариант 1: GitHub App (рекомендуется)

Если локальное расширение не работает, используйте GitHub App:

1. Установите CodeRabbit GitHub App: https://github.com/apps/coderabbitai
2. CodeRabbit будет работать автоматически на всех PR
3. Комментарии будут появляться в GitHub, а не в редакторе

**Преимущества:**
- ✅ Работает стабильно
- ✅ Не зависит от локального расширения
- ✅ Комментарии видны всем участникам PR

### Вариант 2: Веб-интерфейс

1. Откройте PR на GitHub
2. CodeRabbit автоматически проанализирует изменения
3. Комментарии появятся в PR

### Вариант 3: Команда в PR

Добавьте комментарий в PR:
```
@coderabbitai review
```

---

## 📋 Чек-лист диагностики

- [ ] Расширение CodeRabbit установлено и включено
- [ ] Аутентификация выполнена (`CodeRabbit: Sign In`)
- [ ] API токен установлен (если требуется)
- [ ] Интернет-соединение работает
- [ ] Cursor имеет права доступа к файлам
- [ ] Расширение обновлено до последней версии
- [ ] Логи не показывают критических ошибок
- [ ] `.coderabbit.yaml` существует в корне проекта

---

## 🆘 Если ничего не помогает

### 1. Полная переустановка

```bash
# Закройте Cursor

# Удалите все данные CodeRabbit
rm -rf ~/Library/Application\ Support/Cursor/User/globalStorage/*coderabbit*
rm -rf ~/Library/Application\ Support/Cursor/Cache/*

# Переустановите Cursor (опционально)
# Или просто переустановите расширение CodeRabbit
```

### 2. Используйте GitHub App

GitHub App работает стабильнее локального расширения:
- https://github.com/apps/coderabbitai
- Установите для репозитория
- CodeRabbit будет работать на всех PR автоматически

### 3. Обратитесь в поддержку

- CodeRabbit Support: support@coderabbit.ai
- GitHub Issues: https://github.com/coderabbitai/coderabbit/issues
- Discord: https://discord.gg/coderabbit

---

## 📝 Текущая конфигурация проекта

Ваш проект уже настроен:
- ✅ `.coderabbit.yaml` существует
- ✅ Конфигурация для Python и TypeScript
- ✅ Profile: `chill` (менее агрессивные комментарии)

**Проверьте:**
```bash
cat .coderabbit.yaml
```

---

## ✅ Быстрая проверка

Выполните в терминале:

```bash
# Проверьте конфигурацию
cat .coderabbit.yaml

# Проверьте, что файл существует
ls -la .coderabbit.yaml

# Проверьте логи Cursor (если доступны)
ls -la ~/Library/Application\ Support/Cursor/logs/
```

---

**Last updated:** 2026-01-16
**Status:** Troubleshooting Guide
