# 🔧 Диагностика проблем с Claude Code CLI
# 🔧 Claude Code CLI Troubleshooting

**Language / Язык:** This document is available in Russian (primary) and English (section headers).
Документ доступен на русском (основной) и английском (заголовки разделов).

## Quick Fix Summary / Краткая справка по исправлению

| Symptom / Симптом | Quick Fix / Быстрое решение |
|-------------------|----------------------------|
| `command not found: claude` | **EN:** Install via `brew install claude-code` or download from https://claude.ai/download / ensure PATH contains Homebrew bin (`/opt/homebrew/bin`)<br/>**RU:** Установите через `brew install claude-code` или скачайте с https://claude.ai/download / убедитесь, что PATH содержит Homebrew bin (`/opt/homebrew/bin`) |
| Alias `ppclaude` not working<br/>Алиас `ppclaude` не работает | **EN:** Run `source setup_cli_aliases.sh` or use script directly: `./scripts/claude_with_role.sh`<br/>**RU:** Выполните `source setup_cli_aliases.sh` или используйте скрипт напрямую: `./scripts/claude_with_role.sh` |
| Role file not found<br/>Файл роли не найден | **EN:** Navigate to project root (`cd` to BMI-App_2025_clean) and ensure `.claude/role.md` exists<br/>**RU:** Перейдите в корень проекта (`cd` в BMI-App_2025_clean) и убедитесь, что `.claude/role.md` существует |
| Session limit reached<br/>Достигнут лимит сессий | **EN:** Wait 24 hours for reset or check status at https://claude.ai<br/>**RU:** Подождите 24 часа до сброса или проверьте статус на https://claude.ai |
| Interactive session won't start<br/>Интерактивная сессия не запускается | **EN:** Run `claude` then `/login` in the session, or check session limit / credit balance<br/>**RU:** Запустите `claude`, затем `/login` в сессии, или проверьте лимит сессий / баланс кредитов |

## Быстрая проверка / Quick Check

### 1. Проверка установки Claude CLI / Check Claude CLI Installation
```bash
which claude
claude --version
```

**Ожидаемый результат:** Путь к команде и версия (например, `2.0.34`)

### 2. Проверка скрипта с ролью / Check Role Script
```bash
./scripts/claude_with_role.sh --version
```

**Ожидаемый результат:** Версия Claude CLI

### 3. Проверка файла роли / Check Role File
```bash
test -f .claude/role.md && echo "✅ Файл найден" || echo "❌ Файл не найден"
wc -l .claude/role.md
```

## Частые проблемы и решения / Common Issues and Solutions

### Проблема: "command not found: claude" / Issue: "command not found: claude"

**Решение:**
1. Установите Claude Code CLI:
   - macOS: `brew install claude-code` или скачайте с https://claude.ai/download
   - Или через Cursor: CLI устанавливается автоматически с Cursor IDE

2. Проверьте PATH:
   ```bash
   echo $PATH | grep -q "/opt/homebrew/bin" && echo "✅ Homebrew в PATH" || echo "⚠️ Добавьте в PATH"
   ```

### Проблема: "Алиас ppclaude не работает" / Issue: "Alias ppclaude not working"

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

### Проблема: "Role file not found" / Issue: "Role file not found"

**Решение:**
Проверьте, что вы находитесь в корне проекта:
```bash
pwd  # Должно быть: .../BMI-App_2025_clean
ls -la .claude/role.md
```

### Проблема: Интерактивная сессия не запускается / Issue: Interactive session won't start

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

### Проблема: "Session limit reached" / Issue: "Session limit reached"

**Решение:**
1. Дождитесь сброса лимита (обычно каждые 24 часа)
2. Используйте GitHub Copilot CLI или другие инструменты
3. Проверьте баланс на https://claude.ai

## Правильный запуск / Proper Launch

### Вариант 1: Через алиас (после загрузки) / Option 1: Via alias (after loading)
```bash
source setup_cli_aliases.sh
ppclaude
```

### Вариант 2: Напрямую через скрипт / Option 2: Directly via script
```bash
./scripts/claude_with_role.sh
```

### Вариант 3: Обычный Claude (без роли) / Option 3: Regular Claude (without role)
```bash
claude
```

### Вариант 4: С явным указанием роли / Option 4: With explicit role specification
```bash
claude --append-system-prompt "$(cat .claude/role.md)"
```

## Для teleport-сессий / For teleport sessions

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

## Диагностика проблем / Problem Diagnostics

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

## Получение помощи / Getting Help

Если проблема не решена:
1. Проверьте логи: `claude --debug`
2. Проверьте документацию: https://docs.anthropic.com/claude/docs/claude-code-cli
3. Проверьте статус: https://status.anthropic.com
