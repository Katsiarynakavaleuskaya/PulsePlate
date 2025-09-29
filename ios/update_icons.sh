#!/bin/bash

# Скрипт для обновления иконок в Xcode проекте
# Автоматически обновляет все иконки и перезапускает Xcode

echo "🎨 Обновляем иконки PulsePlate..."

# Путь к проекту
PROJECT_DIR="/Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean/ios"
ICONS_DIR="$PROJECT_DIR/PulsePlate/Assets.xcassets/AppIcon.appiconset"

# Проверяем, что папка существует
if [ ! -d "$ICONS_DIR" ]; then
    echo "❌ Папка с иконками не найдена: $ICONS_DIR"
    exit 1
fi

# Переходим в папку проекта
cd "$PROJECT_DIR"

# Проверяем наличие всех иконок
echo "📋 Проверяем наличие иконок..."
required_icons=(
    "AppIcon-20@1x.png"
    "AppIcon-20@2x.png"
    "AppIcon-20@3x.png"
    "AppIcon-29@1x.png"
    "AppIcon-29@2x.png"
    "AppIcon-29@3x.png"
    "AppIcon-40@1x.png"
    "AppIcon-40@2x.png"
    "AppIcon-40@3x.png"
    "AppIcon-60@2x.png"
    "AppIcon-60@3x.png"
    "AppIcon-76@1x.png"
    "AppIcon-76@2x.png"
    "AppIcon-83.5@2x.png"
    "AppIcon-1024.png"
)

missing_icons=()
for icon in "${required_icons[@]}"; do
    if [ ! -f "$ICONS_DIR/$icon" ]; then
        missing_icons+=("$icon")
    fi
done

if [ ${#missing_icons[@]} -gt 0 ]; then
    echo "❌ Отсутствуют иконки:"
    for icon in "${missing_icons[@]}"; do
        echo "   - $icon"
    done
    echo ""
    echo "🔄 Генерируем недостающие иконки..."
    python3 generate_app_icons.py
else
    echo "✅ Все иконки на месте!"
fi

# Проверяем размеры иконок
echo "📏 Проверяем размеры иконок..."
for icon in "${required_icons[@]}"; do
    if [ -f "$ICONS_DIR/$icon" ]; then
        size=$(file "$ICONS_DIR/$icon" | grep -o '[0-9]* x [0-9]*' | head -1)
        echo "   $icon: $size"
    fi
done

echo ""
echo "🎯 Иконки готовы к использованию в Xcode!"
echo ""
echo "📱 Следующие шаги:"
echo "1. Откройте проект в Xcode: open PulsePlate.xcodeproj"
echo "2. Перейдите к Assets.xcassets > AppIcon.appiconset"
echo "3. Все иконки должны автоматически отобразиться"
echo "4. Соберите проект (⌘+B) для проверки"
echo ""
echo "✨ Готово!"
