#!/bin/bash
# 🔍 Диагностика проблем с Cursor и памятью
# Usage: ./scripts/diagnose_cursor.sh

set -euo pipefail

echo "🔍 Диагностика Cursor и системных ресурсов..."
echo ""

# Проверка процессов Cursor
echo "📊 Процессы Cursor:"
if command -v ps >/dev/null 2>&1; then
    ps aux | grep -i "cursor\|claude" | grep -v grep | awk '{printf "  PID: %-6s CPU: %5s%% MEM: %6s%% %s\n", $2, $3, $4, $11}' | head -10 || echo "⚠️  ps command failed"
else
    echo "⚠️  ps command not available"
fi
echo ""

# Топ процессов по памяти
echo "💾 Топ-10 процессов по использованию памяти:"
if command -v top >/dev/null 2>&1; then
    top -l 1 -n 10 -o mem 2>/dev/null | tail -n +8 | head -10 | awk '{printf "  %-6s %5s%% %8s %s\n", $1, $3, $7, $2}' || echo "⚠️  top command failed"
else
    echo "⚠️  top command not available"
fi
echo ""

# Использование памяти системы
echo "📈 Использование памяти системы:"
if command -v vm_stat >/dev/null 2>&1 && command -v perl >/dev/null 2>&1; then
    vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("  %-16s %16.2f Mi\n", "$1:", $2 * $size / 1048576);' || echo "⚠️  vm_stat/perl pipeline failed"
else
    echo "⚠️  vm_stat or perl command not available"
fi
echo ""

# Проверка zsh процессов
echo "🐚 Процессы zsh:"
if command -v ps >/dev/null 2>&1; then
    ps aux | grep zsh | grep -v grep | head -5 || echo "⚠️  ps command failed"
else
    echo "⚠️  ps command not available"
fi
echo ""

# Проверка времени загрузки shell
echo "⏱️  Тест времени загрузки shell:"
if command -v time >/dev/null 2>&1 && command -v zsh >/dev/null 2>&1; then
    { time zsh -c "echo 'Shell startup test'"; } 2>&1 || echo "⚠️  time command failed"
else
    echo "⚠️  time or zsh command not available"
fi
echo ""

# Проверка размера .zshrc и .zprofile
echo "📄 Размер конфигурационных файлов:"
for file in ~/.zshrc ~/.zprofile ~/.zshenv; do
    if [ -f "$file" ]; then
        lines=$(wc -l < "$file" 2>/dev/null || echo "0")
        size=$(wc -c < "$file" 2>/dev/null || echo "0")
        echo "  $(basename $file): $lines строк, $size байт"
    fi
done
echo ""

# Проверка переменных окружения
echo "🌍 Количество переменных окружения:"
env | wc -l | awk '{print "  " $1 " переменных"}'
echo ""

# Проверка размера PROJECT_ROOT если установлен
if [ -n "${PROJECT_ROOT:-}" ]; then
    echo "📁 PROJECT_ROOT: $PROJECT_ROOT"
    if [ -d "$PROJECT_ROOT" ]; then
        if command -v du >/dev/null 2>&1; then
            du -sh "$PROJECT_ROOT" 2>/dev/null | cut -f1 | sed 's/^/  Размер проекта: /' || echo "⚠️  du command failed"
        else
            echo "⚠️  du command not available"
        fi
    fi
fi

echo ""
echo "✅ Диагностика завершена"
