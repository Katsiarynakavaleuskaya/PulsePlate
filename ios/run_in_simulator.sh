#!/bin/bash
# 🚀 Скрипт для запуска PulsePlate в iOS симуляторе из командной строки

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PATH="$SCRIPT_DIR/PulsePlate.xcodeproj"
SCHEME="PulsePlate"

# Выбираем симулятор (можно изменить)
SIMULATOR="iPhone 17 Pro"

echo "📱 Запускаем PulsePlate в симуляторе..."
echo "🎯 Симулятор: $SIMULATOR"
echo ""

# Проверяем наличие проекта
if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ Проект не найден: $PROJECT_PATH" >&2
    exit 1
fi

# Запускаем симулятор и приложение
echo "🔨 Собираем проект..."
xcodebuild \
    -project "$PROJECT_PATH" \
    -scheme "$SCHEME" \
    -destination "platform=iOS Simulator,name=$SIMULATOR" \
    build

echo ""
echo "🚀 Запускаем приложение в симуляторе..."
xcodebuild \
    -project "$PROJECT_PATH" \
    -scheme "$SCHEME" \
    -destination "platform=iOS Simulator,name=$SIMULATOR" \
    test-without-building

echo ""
echo "✅ Приложение запущено в симуляторе!"
echo "💡 Для остановки: закройте симулятор или нажмите Ctrl+C"
