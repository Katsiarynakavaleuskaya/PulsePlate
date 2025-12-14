#!/bin/bash
# Скрипт для исправления зависаний Qoder при Reload Window

set -e

echo "🔧 Исправление зависаний Qoder..."

# 1. Остановить зависшие языковые серверы
echo "1️⃣ Останавливаем зависшие языковые серверы..."
pkill -9 -f "lsp_server.py" 2>/dev/null || true
pkill -9 -f "pylance" 2>/dev/null || true
pkill -9 -f "pyright" 2>/dev/null || true
sleep 2

# 2. Очистить кэш языковых серверов
echo "2️⃣ Очищаем кэш языковых серверов..."
rm -rf ~/.qoder/extensions/ms-python.*/bundled/tool/__pycache__ 2>/dev/null || true
rm -rf ~/.cursor/extensions/ms-python.*/bundled/tool/__pycache__ 2>/dev/null || true
echo "✅ Кэш очищен"

# 3. Очистить кэш проекта
echo "3️⃣ Очищаем кэш проекта..."
if [ -d ".venv" ]; then
    find .venv -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find .venv -name "*.pyc" -delete 2>/dev/null || true
fi
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ Кэш проекта очищен"

# 4. Проверить процессы
echo "4️⃣ Проверяем процессы..."
QODER_PROCS=$(pgrep -i qoder | wc -l)
LSP_PROCS=$(pgrep -E "lsp_server|pylance|pyright" | wc -l)

echo "   Процессов Qoder: $QODER_PROCS"
echo "   Языковых серверов: $LSP_PROCS"

if [ "$QODER_PROCS" -gt 25 ]; then
    echo "⚠️ Слишком много процессов Qoder ($QODER_PROCS)"
    echo "   Рекомендуется перезапустить Qoder"
fi

echo ""
echo "✅ Готово!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. Перезапустите Qoder (закройте и откройте заново)"
echo "   2. Откройте проект"
echo "   3. Если зависает - используйте 'Kill Window' вместо 'Reload Window'"
echo "   4. Настройки оптимизированы для работы только с открытыми файлами"
