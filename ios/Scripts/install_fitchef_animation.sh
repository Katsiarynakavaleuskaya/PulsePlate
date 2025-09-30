#!/bin/bash
set -euo pipefail

# Скрипт для установки анимации FitChef (4 кадра)

# Обработка аргументов командной строки
FORCE_MODE="false"
NON_INTERACTIVE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_MODE="true"
            shift
            ;;
        --non-interactive)
            NON_INTERACTIVE="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--force] [--non-interactive]"
            echo "  --force           Overwrite existing files without prompting"
            echo "  --non-interactive Skip all interactive prompts (fails on conflicts)"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            echo "Use --help for usage information" >&2
            exit 1
            ;;
    esac
done

echo "🎬 Устанавливаем анимацию FitChef..."

# Пути (относительно скрипта)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ANIMATION_DIR="$SCRIPT_DIR/../PulsePlate/Assets.xcassets/FitChefAnimation.imageset"
TEMP_DIR="$SCRIPT_DIR/temp_animation"

# Создаем временную папку
if ! mkdir -p "$TEMP_DIR"; then
    echo "❌ Ошибка: Не удалось создать временную папку $TEMP_DIR" >&2
    echo "   Проверьте права доступа к родительской директории" >&2
    exit 1
fi

# Проверяем, что папка создана и доступна для записи
if [ ! -d "$TEMP_DIR" ] || [ ! -w "$TEMP_DIR" ]; then
    echo "❌ Ошибка: Временная папка $TEMP_DIR недоступна для записи" >&2
    exit 1
fi

echo "📁 Временная папка для анимации: $TEMP_DIR"
echo ""
echo "📋 Инструкция:"
echo "1. Скопируйте 4 файла анимации FitChef в папку:"
echo "   $TEMP_DIR"
echo ""
echo "2. Файлы должны называться:"
echo "   - fitchef_frame1.png"
echo "   - fitchef_frame2.png"
echo "   - fitchef_frame3.png"
echo "   - fitchef_frame4.png"
echo ""
echo "3. После копирования запустите:"
echo "   ./install_fitchef_animation.sh install"
echo ""

# Функция для установки анимации
install_animation() {
    echo "🎬 Устанавливаем анимацию FitChef..."

    # Создаем директорию анимации и проверяем её создание
    if ! mkdir -p "$ANIMATION_DIR"; then
        echo "❌ Ошибка: Не удалось создать директорию $ANIMATION_DIR" >&2
        echo "   Проверьте права доступа к родительской директории" >&2
        ls -la "$(dirname "$ANIMATION_DIR")" >&2
        return 1
    fi

    # Проверяем наличие файлов
    local frame_files=(
        "fitchef_frame1.png"
        "fitchef_frame2.png"
        "fitchef_frame3.png"
        "fitchef_frame4.png"
    )

    local missing_files=()
    for file in "${frame_files[@]}"; do
        if [ ! -f "$TEMP_DIR/$file" ]; then
            missing_files+=("$file")
        fi
    done

    if [ ${#missing_files[@]} -gt 0 ]; then
        echo "❌ Отсутствуют файлы:"
        for file in "${missing_files[@]}"; do
            echo "   - $file"
        done
        echo ""
        echo "📁 Содержимое папки:"
        ls -la "$TEMP_DIR"
        return 1
    fi

    echo "✅ Все файлы анимации найдены!"

    # Копируем файлы с защитой от перезаписи
    echo "📁 Копируем файлы анимации..."
    for file in "${frame_files[@]}"; do
        dest_file="$ANIMATION_DIR/$file"
        src_file="$TEMP_DIR/$file"
        if [ -f "$dest_file" ]; then
            echo "⚠️  Файл $file уже существует в папке назначения."
            read -p "Хотите создать резервную копию и перезаписать файл? [y/N]: " overwrite_choice
            if [[ "$overwrite_choice" =~ ^[Yy]$ ]]; then
                backup_file="${dest_file}.bak_$(date +%s)"
                echo "   🗄️  Создаю резервную копию: $(basename "$backup_file")"
                mv "$dest_file" "$backup_file"
                echo "   📄 Копирую $file"
                if ! cp "$src_file" "$dest_file"; then
                    echo "❌ Failed to copy $src_file to $dest_file" >&2
                    return 1
                fi
            else
                echo "   ⏭️  Пропускаю копирование $file"
            fi
        else
            echo "   📄 Копирую $file"
            if ! cp "$src_file" "$dest_file"; then
                echo "❌ Failed to copy $src_file to $dest_file" >&2
                return 1
            fi
        fi
    done

    echo "✅ Анимация FitChef установлена!"
    echo "🎯 Теперь можно использовать AnimatedFitChef в коде"
    echo ""
    echo "📱 Пример использования:"
    echo "   AnimatedFitChef()"
    echo "   AnimatedMascotBubble(textKey: \"Привет!\")"

    return 0
}

# Основная логика
case "${1:-help}" in
    "install")
        install_animation
        exit $?
        ;;
    "cleanup")
        echo "🧹 Очищаем временные файлы..."
        rm -rf "$TEMP_DIR"
        echo "✅ Временные файлы удалены"
        ;;
    *)
        echo "🎬 Установка анимации FitChef"
        echo ""
        echo "Использование:"
        echo "  $0 install    - Установить анимацию"
        echo "  $0 cleanup    - Очистить временные файлы"
        echo ""
        echo "Пошаговая инструкция:"
        echo "1. Скопируйте 4 файла анимации в: $TEMP_DIR"
        echo "2. Запустите: $0 install"
        echo "3. Используйте AnimatedFitChef в коде"
        ;;
esac
