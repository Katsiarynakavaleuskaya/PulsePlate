#!/bin/bash

# Скрипт для установки иконок из ZIP файла
# Автоматически распаковывает и копирует иконки в проект

echo "📦 Устанавливаем иконки из ZIP файла..."

# Пути (относительно скрипта)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR="$PROJECT_DIR/temp_icons"
ICONS_DIR="$PROJECT_DIR/PulsePlate/Assets.xcassets/AppIcon.appiconset"

# Создаем временную папку
mkdir -p "$TEMP_DIR"

echo "📁 Временная папка: $TEMP_DIR"
echo ""
echo "📋 Инструкция:"
echo "1. Скопируйте ваш ZIP файл с иконками в папку:"
echo "   $TEMP_DIR"
echo ""
echo "2. После копирования запустите:"
echo "   ./install_icons_from_zip.sh extract"
echo ""

# Функция для поиска ZIP файла
find_zip_file() {
    local zip_file
    zip_file="$(find "$TEMP_DIR" -name "*.zip" -type f | head -1)"
    if [ -z "$zip_file" ]; then
        echo "❌ ZIP файл не найден в папке $TEMP_DIR"
        echo "📁 Содержимое папки:"
        ls -la "$TEMP_DIR"
        return 1
    fi
    echo "$zip_file"
}

# Функция для извлечения иконок
extract_icons() {
    local zip_file
    zip_file=$(find_zip_file)
    if [ $? -ne 0 ]; then
        return 1
    fi

    echo "📦 Найден ZIP файл: $(basename "$zip_file")"
    echo "🔄 Извлекаем иконки..."

# Извлекаем в подпапку
ORIGINAL_DIR="$PWD"
cd "$TEMP_DIR" || { echo "❌ Не удалось перейти в $TEMP_DIR"; return 1; }
unzip -q "$zip_file" -d "extracted"
cd "$ORIGINAL_DIR" || { echo "❌ Не удалось вернуться в $ORIGINAL_DIR"; return 1; }

    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при извлечении ZIP файла"
        return 1
    fi

    echo "✅ ZIP файл успешно извлечен"

    # Ищем PNG файлы
    echo "🔍 Ищем PNG файлы..."
    find "$TEMP_DIR/extracted" -name "*.png" -type f -print0 | while IFS= read -r -d '' file; do
        echo "   📄 $(basename "$file")"
    done

    return 0
}

# Функция для копирования иконок
copy_icons() {
    echo "📋 Копируем иконки в проект..."

    # Создаем резервную копию существующих иконок
    if [ -d "$ICONS_DIR" ]; then
        echo "💾 Создаем резервную копию существующих иконок..."
        cp -r "$ICONS_DIR" "$ICONS_DIR.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Копируем новые иконки
    echo "📁 Копируем PNG файлы..."
    find "$TEMP_DIR/extracted" -name "*.png" -type f -print0 | while IFS= read -r -d '' file; do
        filename="$(basename "$file")"
        echo "   📄 Копируем $filename"
        cp "$file" "$ICONS_DIR/" || echo "⚠️ Ошибка копирования $filename"
    done

    # Обновляем Contents.json, если он есть в архиве
    local appicon_src
    appicon_src="$(find "$TEMP_DIR/extracted" -type d -name "AppIcon.appiconset" | head -1)"
    if [ -n "$appicon_src" ] && [ -f "$appicon_src/Contents.json" ]; then
        echo "   📄 Обновляем Contents.json"
        cp "$appicon_src/Contents.json" "$ICONS_DIR/Contents.json"
    fi

    # Проверяем результат
    echo "✅ Проверяем установленные иконки..."
    png_count=$(find "$ICONS_DIR" -name "*.png" -type f | wc -l)
    echo "📊 Установлено $png_count PNG файлов"

    # Показываем список установленных иконок
    echo "📋 Установленные иконки:"
    find "$ICONS_DIR" -name "*.png" -type f -print0 | sort -z | while IFS= read -r -d '' file; do
        size=$(file "$file" | grep -o '[0-9]* x [0-9]*' | head -1)
        echo "   📄 $(basename "$file"): $size"
    done

    echo ""
    echo "🎯 Иконки успешно установлены!"
    echo "📱 Теперь откройте проект в Xcode:"
    echo "   open PulsePlate.xcodeproj"

    return 0
}
cleanup() {
    echo "🧹 Очищаем временные файлы..."
    rm -rf "$TEMP_DIR/extracted"
    echo "✅ Временные файлы удалены"
}

# Основная логика
case "${1:-help}" in
    "extract")
        if extract_icons; then
            copy_icons
            cleanup
        fi
        ;;
    "cleanup")
        cleanup
        ;;
    *)
        echo "📦 Установка иконок из ZIP файла"
        echo ""
        echo "Использование:"
        echo "  $0 extract    - Извлечь и установить иконки"
        echo "  $0 cleanup    - Очистить временные файлы"
        echo ""
        echo "Пошаговая инструкция:"
        echo "1. Скопируйте ZIP файл в: $TEMP_DIR"
        echo "2. Запустите: $0 extract"
        echo "3. Откройте проект в Xcode"
        ;;
esac
