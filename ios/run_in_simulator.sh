#!/bin/bash
# 🚀 Скрипт для запуска PulsePlate в iOS симуляторе из командной строки

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PATH="$SCRIPT_DIR/PulsePlate.xcodeproj"
SCHEME="PulsePlate"

# Выбираем симулятор (можно изменить)
PREFERRED_SIMULATOR="iPhone 14"

# Fallback: автоматически находим доступный iPhone симулятор
echo "🔍 Ищем доступные симуляторы..."
AVAILABLE_SIMULATOR=$(xcrun simctl list devices available | grep -m 1 "iPhone" | sed -E 's/.*iPhone ([0-9]+[^)]*).*/iPhone \1/' | xargs)

if [ -z "$AVAILABLE_SIMULATOR" ]; then
    echo "❌ Не найден доступный iPhone симулятор" >&2
    exit 1
fi

# Проверяем предпочитаемый симулятор, используем fallback если недоступен
if xcrun simctl list devices available | grep -q "$PREFERRED_SIMULATOR"; then
    SIMULATOR="$PREFERRED_SIMULATOR"
    echo "✅ Используем предпочитаемый симулятор: $SIMULATOR"
else
    SIMULATOR="$AVAILABLE_SIMULATOR"
    echo "⚠️  Предпочитаемый симулятор '$PREFERRED_SIMULATOR' недоступен"
    echo "✅ Используем найденный симулятор: $SIMULATOR"
fi

echo ""
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
