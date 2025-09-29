#!/bin/bash

# Скрипт для установки анимации FitChef (4 кадра)

echo "🎬 Устанавливаем анимацию FitChef..."

# Пути
ANIMATION_DIR="/Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean/ios/PulsePlate/Assets.xcassets/FitChefAnimation.imageset"
TEMP_DIR="/Users/katsiaryna_kavaleuskaya/Documents/BMI-App_2025_clean/ios/temp_animation"

# Создаем временную папку
mkdir -p "$TEMP_DIR"

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

    # Копируем файлы
    echo "📁 Копируем файлы анимации..."
    for file in "${frame_files[@]}"; do
        echo "   📄 Копируем $file"
        cp "$TEMP_DIR/$file" "$ANIMATION_DIR/"
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
