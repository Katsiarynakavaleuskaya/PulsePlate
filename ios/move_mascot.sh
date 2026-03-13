#!/bin/bash

# Скрипт для перемещения маскота FitChef из AppIcon в правильное место
# Script for moving the FitChef mascot from AppIcon into the runtime asset set

set -euo pipefail

trap 'echo "❌ Ошибка в строке $LINENO: $BASH_COMMAND" >&2; exit 1' ERR

echo "🐱 Перемещаем маскота FitChef..."

# Пути (относительно скрипта)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ICONS_DIR="$SCRIPT_DIR/PulsePlate/Assets.xcassets/AppIcon.appiconset"
MASCOT_DIR="$SCRIPT_DIR/PulsePlate/Assets.xcassets/FitChef.imageset"

# Проверяем, что папки существуют
if [ ! -d "$ICONS_DIR" ]; then
    echo "❌ Папка с иконками не найдена: $ICONS_DIR"
    exit 1
fi

if [ ! -d "$MASCOT_DIR" ]; then
    echo "❌ Папка для маскота не найдена: $MASCOT_DIR"
    exit 1
fi

echo "📋 Найденные файлы в AppIcon:"
ls -la "$ICONS_DIR"/*.png | head -5

echo ""
echo "🤔 Какой файл является маскотом FitChef?"
echo "Пожалуйста, укажите имя файла (например: AppIcon-1024.png):"
read -r mascot_file

if [ ! -f "$ICONS_DIR/$mascot_file" ]; then
    echo "❌ Файл $mascot_file не найден в $ICONS_DIR"
    exit 1
fi

echo "🐱 Копируем маскота в правильное место..."

# Канонический runtime mirror использует реальный 1x/2x/3x output.
# The canonical runtime mirror must use true 1x/2x/3x renditions.
sips -Z 720 "$ICONS_DIR/$mascot_file" --out "$MASCOT_DIR/fitchef-neutral@3x.png" >/dev/null
sips -Z 480 "$MASCOT_DIR/fitchef-neutral@3x.png" --out "$MASCOT_DIR/fitchef-neutral@2x.png" >/dev/null
sips -Z 240 "$MASCOT_DIR/fitchef-neutral@3x.png" --out "$MASCOT_DIR/fitchef-neutral@1x.png" >/dev/null

echo "✅ Маскот FitChef перемещен в правильное место!"
echo "📁 Расположение: $MASCOT_DIR"
echo ""
echo "🎯 Теперь маскот можно использовать в коде:"
echo "   Image(\"FitChef\")"
echo ""
echo "🧹 Хотите удалить маскота из AppIcon? (y/n)"
read -r delete_mascot

if [ "$delete_mascot" = "y" ] || [ "$delete_mascot" = "Y" ]; then
    rm "$ICONS_DIR/$mascot_file"
    echo "🗑️ Маскот удален из AppIcon"
else
    echo "📋 Маскот оставлен в AppIcon (дубликат)"
fi

echo ""
echo "🎉 Готово! Маскот FitChef теперь в правильном месте!"
