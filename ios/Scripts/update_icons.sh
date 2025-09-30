#!/bin/bash

# Скрипт для обновления иконок в Xcode проекте
# Автоматически обновляет все иконки и перезапускает Xcode

echo "🎨 Обновляем иконки PulsePlate..."

# Путь к проекту (относительно скрипта)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"  # Переходим на уровень выше из Scripts/
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

# Читаем имена файлов из Contents.json
CONTENTS_JSON="$ICONS_DIR/Contents.json"
if [ ! -f "$CONTENTS_JSON" ]; then
    echo "❌ Файл Contents.json не найден: $CONTENTS_JSON"
    exit 1
fi

# Извлекаем имена файлов из Contents.json
required_icons=($(python3 -c "
import json
import sys

try:
    with open('$CONTENTS_JSON', 'r') as f:
        data = json.load(f)

    filenames = []
    for image in data.get('images', []):
        filename = image.get('filename')
        if filename:
            filenames.append(filename)

    print(' '.join(filenames))
except Exception as e:
    print(f'Error reading Contents.json: {e}', file=sys.stderr)
    sys.exit(1)
"))

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
    python3 "$SCRIPT_DIR"/generate_app_icons.py || { echo "❌ Ошибка при генерации иконок"; exit 1; }
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
