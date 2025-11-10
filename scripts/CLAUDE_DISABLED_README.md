# Claude CLI Disabled

## ⚠️ Status / Статус

**English:** Claude CLI has been temporarily disabled in this project to prevent GPU usage.

**Русский:** Claude CLI временно отключен в этом проекте для предотвращения использования GPU.

## What Was Done / Что было сделано

1. ✅ **EN:** Closed Claude.app (GUI application)
   **RU:** Закрыто приложение Claude.app (GUI)

2. ✅ **EN:** Deactivated script `scripts/claude_with_role.sh`
   **RU:** Деактивирован скрипт `scripts/claude_with_role.sh`

3. ✅ **EN:** Disabled alias `ppclaude` in `setup_cli_aliases.sh`
   **RU:** Отключен алиас `ppclaude` в `setup_cli_aliases.sh`

## Status Check / Проверка статуса

```bash
# EN: Check running Claude processes
# RU: Проверить запущенные процессы Claude
ps aux | grep -i claude | grep -v grep

# EN: Try running the script (should show a warning)
# RU: Попробовать запустить скрипт (должен показать предупреждение)
./scripts/claude_with_role.sh
```

## Restoration / Восстановление

### 1. Restore claude_with_role.sh script / Восстановить скрипт claude_with_role.sh

```bash
git checkout scripts/claude_with_role.sh
```

### 2. Restore alias in setup_cli_aliases.sh / Восстановить алиас в setup_cli_aliases.sh

```bash
# EN: Uncomment the line in setup_cli_aliases.sh:
# RU: Раскомментировать строку в setup_cli_aliases.sh:
# create_alias "ppclaude" "$PROJECT_ROOT/scripts/claude_with_role.sh" "$PROJECT_ROOT/scripts/claude_with_role.sh"
```

### 3. Reload aliases / Перезагрузить алиасы

```bash
source setup_cli_aliases.sh
```

## Alternative: Complete Claude CLI Removal / Альтернатива: Полное удаление Claude CLI

**EN:** If you want to completely remove Claude CLI:

**RU:** Если хотите полностью удалить Claude CLI:

```bash
# EN: Remove via Homebrew
# RU: Удалить через Homebrew
brew uninstall --cask claude-code

# EN: Or remove manually
# RU: Или удалить вручную
rm /opt/homebrew/bin/claude
```

## Notes / Примечания

- **EN:** Claude.app (GUI application) can be launched manually, but it will use GPU
  **RU:** Claude.app (GUI приложение) можно запускать вручную, но оно будет использовать GPU

- **EN:** The CLI command `claude` is still installed in the system, but project scripts don't use it
  **RU:** CLI команда `claude` всё ещё установлена в системе, но скрипты проекта её не используют

- **EN:** To completely disable GPU processes, close all Claude applications
  **RU:** Для полного отключения GPU процессов нужно закрыть все приложения Claude
