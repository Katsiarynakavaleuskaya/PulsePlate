#!/bin/bash

# Скрипт для перемещения маскота FitChef из AppIcon в правильное место

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

# Копируем маскота в канонические default filenames
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/FitChefDefault@1x.png"
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/FitChefDefault@2x.png"
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/FitChefDefault@3x.png"

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
