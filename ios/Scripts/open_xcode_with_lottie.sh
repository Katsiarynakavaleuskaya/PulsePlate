#!/bin/bash

# 🚀 Скрипт для открытия Xcode с инструкциями по установке Lottie

echo "🚀 Открываем Xcode с инструкциями по установке Lottie..."

# Переходим в директорию скрипта и открываем Xcode проект
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || { echo "❌ Не удалось перейти в директорию скрипта"; exit 1; }

echo "📱 Открываем PulsePlate.xcodeproj..."
cd "$SCRIPT_DIR/.." || { echo "❌ Не удалось перейти в директорию ios/"; exit 1; }
open PulsePlate.xcodeproj

# Ждем немного, чтобы Xcode загрузился
echo "⏳ Ждем загрузки Xcode..."
sleep 3

# Показываем инструкции
echo ""
echo "📋 ИНСТРУКЦИИ ПО УСТАНОВКЕ LOTTIE:"
echo "=================================="
echo ""
echo "1️⃣ В Xcode выберите:"
echo "   File → Add Package Dependencies..."
echo ""
echo "2️⃣ Введите URL:"
echo "   https://github.com/airbnb/lottie-ios.git"
echo ""
echo "3️⃣ Выберите версию:"
echo "   Version: Up to Next Major"
echo "   From: 4.4.0"
echo ""
echo "4️⃣ Добавьте в Target:"
echo "   Выберите Target 'PulsePlate'"
echo "   Нажмите 'Add Package'"
echo ""
echo "5️⃣ Проверьте установку:"
echo "   В Project Navigator должна появиться папка 'Package Dependencies'"
echo "   В ней должен быть 'lottie-ios'"
echo ""
echo "6️⃣ Добавьте Lottie файлы:"
echo "   Перетащите файлы из PulsePlate/Resources/Lottie/ в Xcode"
echo "   Убедитесь, что они добавлены в Bundle"
echo ""
echo "7️⃣ Протестируйте:"
echo "   Запустите приложение"
echo "   Перейдите на вкладку 'Profile'"
echo "   Нажмите 'Test Lottie Animation'"
echo ""
echo "✅ Готово! Lottie будет установлен в проект"
echo ""
echo "📁 Дополнительные файлы:"
echo "  - LOTTIE_INSTALL_STEPS.md (подробная инструкция)"
echo "  - PulsePlate/Resources/Lottie/fitchef_blink.json (тестовая анимация)"
echo ""
echo "🎬 После установки Lottie вы сможете:"
echo "  - Использовать Lottie анимации в приложении"
echo "  - Создавать сложные анимации FitChef"
echo "  - Интегрировать анимации в UI компоненты"
