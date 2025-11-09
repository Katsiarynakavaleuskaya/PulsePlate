# 🔧 Диагностика проблем с Claude Code CLI

## Быстрая проверка

### 1. Проверка установки Claude CLI
```bash
which claude
claude --version
```

**Ожидаемый результат:** Путь к команде и версия (например, `2.0.34`)

### 2. Проверка скрипта с ролью
```bash
./scripts/claude_with_role.sh --version
```

**Ожидаемый результат:** Версия Claude CLI

### 3. Проверка файла роли
```bash
test -f .claude/role.md && echo "✅ Файл найден" || echo "❌ Файл не найден"
wc -l .claude/role.md
```

## Частые проблемы и решения

### Проблема: "command not found: claude"

**Решение:**
1. Установите Claude Code CLI:
   - macOS: `brew install claude-code` или скачайте с https://claude.ai/download
   - Или через Cursor: CLI устанавливается автоматически с Cursor IDE

2. Проверьте PATH:
   ```bash
   echo $PATH | grep -q "/opt/homebrew/bin" && echo "✅ Homebrew в PATH" || echo "⚠️ Добавьте в PATH"
   ```

### Проблема: "Алиас ppclaude не работает"

**Решение:**
Алиасы нужно загрузить в текущей сессии:
```bash
source setup_cli_aliases.sh
ppclaude --version
```

Или используйте скрипт напрямую:
```bash
./scripts/claude_with_role.sh
```

### Проблема: "Role file not found"

**Решение:**
Проверьте, что вы находитесь в корне проекта:
```bash
pwd  # Должно быть: .../BMI-App_2025_clean
ls -la .claude/role.md
```

### Проблема: Интерактивная сессия не запускается

**Возможные причины:**
1. **Лимит сессий достигнут** - проверьте на https://claude.ai
2. **Требуется аутентификация** - выполните:
   ```bash
   claude
   /login
   ```
3. **Проблема с системным промптом** - попробуйте без роли:
   ```bash
   claude  # Без --append-system-prompt
   ```

### Проблема: "Session limit reached"

**Решение:**
1. Дождитесь сброса лимита (обычно каждые 24 часа)
2. Используйте GitHub Copilot CLI или другие инструменты
3. Проверьте баланс на https://claude.ai

## Правильный запуск

### Вариант 1: Через алиас (после загрузки)
```bash
source setup_cli_aliases.sh
ppclaude
```

### Вариант 2: Напрямую через скрипт
```bash
./scripts/claude_with_role.sh
```

### Вариант 3: Обычный Claude (без роли)
```bash
claude
```

### Вариант 4: С явным указанием роли
```bash
claude --append-system-prompt "$(cat .claude/role.md)"
```

## Для teleport-сессий

Если нужен `--teleport`, сначала войдите в аккаунт:
```bash
claude
/login
# Следуйте инструкциям
```

Затем используйте:
```bash
ppclaude --teleport session_XXXXX
```

## Диагностика проблем

Запустите полную диагностику:
```bash
./scripts/diagnose_claude_cli.sh
```

Или вручную проверьте:
```bash
echo "=== Claude CLI ===" && \
claude --version && \
echo "=== Скрипт ===" && \
./scripts/claude_with_role.sh --version && \
echo "=== Файл роли ===" && \
test -f .claude/role.md && echo "✅ Найден" || echo "❌ Не найден" && \
echo "=== Алиасы ===" && \
type ppclaude 2>/dev/null && echo "✅ Загружены" || echo "⚠️ Не загружены (запустите: source setup_cli_aliases.sh)"
```

## Получение помощи

Если проблема не решена:
1. Проверьте логи: `claude --debug`
2. Проверьте документацию: https://docs.anthropic.com/claude/docs/claude-code-cli
3. Проверьте статус: https://status.anthropic.com
