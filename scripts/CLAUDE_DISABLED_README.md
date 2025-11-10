# Claude CLI Disabled - Account Banned

## ⚠️ Статус

Claude CLI временно отключен для предотвращения использования GPU пока аккаунт в бане.

## Что было сделано:

1. ✅ Закрыто приложение Claude.app (GUI)
2. ✅ Деактивирован скрипт `scripts/claude_with_role.sh`
3. ✅ Отключен алиас `ppclaude` в `setup_cli_aliases.sh`

## Проверка статуса:

```bash
# Проверить запущенные процессы Claude
ps aux | grep -i claude | grep -v grep

# Попробовать запустить скрипт (должен показать предупреждение)
./scripts/claude_with_role.sh
```

## Восстановление после восстановления аккаунта:

### 1. Восстановить скрипт claude_with_role.sh:
```bash
git checkout scripts/claude_with_role.sh
```

### 2. Восстановить алиас в setup_cli_aliases.sh:
```bash
# Раскомментировать строку в setup_cli_aliases.sh:
# create_alias "ppclaude" "$PROJECT_ROOT/scripts/claude_with_role.sh" "$PROJECT_ROOT/scripts/claude_with_role.sh"
```

### 3. Перезагрузить алиасы:
```bash
source setup_cli_aliases.sh
```

## Альтернатива: Полное удаление Claude CLI

Если хотите полностью удалить Claude CLI:

```bash
# Удалить через Homebrew
brew uninstall --cask claude-code

# Или удалить вручную
rm /opt/homebrew/bin/claude
```

## Примечания:

- Claude.app (GUI приложение) можно запускать вручную, но оно будет использовать GPU
- CLI команда `claude` всё ещё установлена в системе, но скрипты проекта её не используют
- Для полного отключения GPU процессов нужно закрыть все приложения Claude
