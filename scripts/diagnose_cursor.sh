#!/bin/bash
# 🔍 Диагностика проблем с Cursor и памятью
# Usage: ./scripts/diagnose_cursor.sh

set -euo pipefail

echo "🔍 Диагностика Cursor и системных ресурсов..."
echo ""

# Проверка процессов Cursor
echo "📊 Процессы Cursor:"
ps aux | grep -i "cursor\|claude" | grep -v grep | awk '{printf "  PID: %-6s CPU: %5s%% MEM: %6s%% %s\n", $2, $3, $4, $11}' | head -10
echo ""

# Топ процессов по памяти
echo "💾 Топ-10 процессов по использованию памяти:"
top -l 1 -n 10 -o mem | tail -n +8 | head -10 | awk '{printf "  %-6s %5s%% %8s %s\n", $1, $3, $7, $2}'
echo ""

# Использование памяти системы
echo "📈 Использование памяти системы:"
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("  %-16s %16.2f Mi\n", "$1:", $2 * $size / 1048576);'
echo ""

# Проверка zsh процессов
echo "🐚 Процессы zsh:"
ps aux | grep zsh | grep -v grep | head -5
echo ""

# Проверка времени загрузки shell
echo "⏱️  Тест времени загрузки shell:"
time zsh -c "echo 'Shell startup test'" 2>&1 | tail -1
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
        echo "  Размер проекта: $(du -sh "$PROJECT_ROOT" 2>/dev/null | cut -f1)"
    fi
fi

echo ""
echo "✅ Диагностика завершена"
