#!/bin/bash

# Скрипт для перемещения маскота FitChef из AppIcon в правильное место

echo "🐱 Перемещаем маскота FitChef..."

# Пути
ICONS_DIR="/Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean/ios/PulsePlate/Assets.xcassets/AppIcon.appiconset"
MASCOT_DIR="/Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean/ios/PulsePlate/Assets.xcassets/FitChef.imageset"

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

# Копируем маскота в разные размеры
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/fitchef@1x.png"
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/fitchef@2x.png"
cp "$ICONS_DIR/$mascot_file" "$MASCOT_DIR/fitchef@3x.png"

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
