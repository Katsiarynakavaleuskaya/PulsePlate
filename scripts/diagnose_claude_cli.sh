#!/bin/bash
# 🔍 Диагностика Claude Code CLI

echo "🔍 Диагностика Claude Code CLI..."
echo ""

echo "=== 1. Проверка Claude CLI ==="
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude CLI найден: $(which claude)"
    claude --version 2>&1 | head -1
else
    echo "❌ Claude CLI не найден в PATH"
    echo "   Установите: brew install claude-code"
fi
echo ""

echo "=== 2. Проверка скрипта ==="
if [ -f "./scripts/claude_with_role.sh" ]; then
    echo "✅ Скрипт найден"
    bash -n ./scripts/claude_with_role.sh 2>&1 && echo "✅ Синтаксис корректен" || echo "❌ Ошибка синтаксиса"
else
    echo "❌ Скрипт не найден"
fi
echo ""

echo "=== 3. Проверка файла роли ==="
if [ -f ".claude/role.md" ]; then
    echo "✅ Файл роли найден"
    echo "   Размер: $(wc -c < .claude/role.md | awk '{print $1}') байт"
    echo "   Строк: $(wc -l < .claude/role.md | awk '{print $1}')"
else
    echo "❌ Файл роли не найден"
fi
echo ""

echo "=== 4. Проверка алиасов ==="
if type ppclaude >/dev/null 2>&1; then
    echo "✅ Алиас ppclaude загружен"
else
    echo "⚠️  Алиас ppclaude не загружен"
    echo "   Загрузите: source setup_cli_aliases.sh"
fi
echo ""

echo "=== 5. Тест запуска скрипта ==="
if ./scripts/claude_with_role.sh --version >/dev/null 2>&1; then
    echo "✅ Скрипт запускается успешно"
else
    echo "❌ Ошибка при запуске скрипта"
fi
echo ""

echo "✅ Диагностика завершена"
