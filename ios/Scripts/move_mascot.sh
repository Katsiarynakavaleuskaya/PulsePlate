#!/bin/bash

# Скрипт для перемещения маскота FitChef из AppIcon в правильное место
# Script for moving the FitChef mascot from AppIcon into the runtime asset set

# Включаем строгий режим для обработки ошибок
set -euo pipefail

# Функция для обработки ошибок
trap 'echo "❌ Ошибка в строке $LINENO: $BASH_COMMAND" >&2; exit 1' ERR

echo "🐱 Перемещаем маскота FitChef..."

# Пути (относительно скрипта)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ICONS_DIR="$SCRIPT_DIR/../PulsePlate/Assets.xcassets/AppIcon.appiconset"
MASCOT_DIR="$SCRIPT_DIR/../PulsePlate/Assets.xcassets/FitChef.imageset"

# Проверяем, что папки существуют
if [ ! -d "$ICONS_DIR" ]; then
    echo "❌ Папка с иконками не найдена: $ICONS_DIR"
    exit 1
fi

# Создаем папку для маскота если её нет
mkdir -p "$MASCOT_DIR"

if [ ! -d "$MASCOT_DIR" ]; then
    echo "❌ Папка для маскота не найдена: $MASCOT_DIR"
    exit 1
fi

echo "📋 Найденные файлы в AppIcon:"
shopt -s nullglob
pngs=("$ICONS_DIR"/*.png)
if (( ${#pngs[@]} == 0 )); then
    echo "❌ PNG-файлы не найдены в $ICONS_DIR"
    exit 1
fi

# Show first 5 PNG files
count=0
for png in "${pngs[@]}"; do
    echo "  - $(basename "$png")"
    ((count++))
    if (( count >= 5 )); then
        if (( ${#pngs[@]} > 5 )); then
            echo "  ... и ещё $((${#pngs[@]} - 5)) файлов"
        fi
        break
    fi
done
shopt -u nullglob

echo ""
echo "🤔 Какой файл является маскотом FitChef?"
echo "Пожалуйста, укажите имя файла (например: AppIcon-1024.png):"
read -r mascot_file

# Validate that filename doesn't contain path separators
if [[ "$mascot_file" == *"/"* ]] || [[ "$mascot_file" == *".."* ]]; then
    echo "❌ Недопустимое имя файла. Используйте только имя файла без пути."
    exit 1
fi

if [ ! -f "$ICONS_DIR/$mascot_file" ]; then
    echo "❌ Файл $mascot_file не найден в $ICONS_DIR"
    exit 1
fi

echo "🐱 Копируем маскота в правильное место..."

# Канонический runtime mirror использует реальный 1x/2x/3x output.
# The canonical runtime mirror must use true 1x/2x/3x renditions.
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/fitchef-neutral@3x.png"
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
