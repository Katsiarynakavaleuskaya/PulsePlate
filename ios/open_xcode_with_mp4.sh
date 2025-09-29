#!/bin/bash

# 🎬 Скрипт для открытия Xcode с инструкциями по добавлению MP4

echo "🎬 Открываем Xcode с инструкциями по добавлению MP4..."

# Открываем Xcode проект
echo "📱 Открываем PulsePlate.xcodeproj..."
open PulsePlate.xcodeproj

# Ждем немного, чтобы Xcode загрузился
echo "⏳ Ждем загрузки Xcode..."
sleep 3

# Показываем инструкции
echo ""
echo "📋 ИНСТРУКЦИИ ПО ДОБАВЛЕНИЮ MP4 В XCODE:"
echo "======================================="
echo ""
echo "1️⃣ В Xcode Project Navigator:"
echo "   Найдите папку 'PulsePlate'"
echo "   Правой кнопкой → 'Add Files to PulsePlate'"
echo ""
echo "2️⃣ Выберите папку с MP4:"
echo "   Перейдите в PulsePlate/Resources/MP4/"
echo "   Выберите все .mp4 файлы"
echo "   Убедитесь, что 'Add to target: PulsePlate' отмечен"
echo "   Нажмите 'Add'"
echo ""
echo "3️⃣ Проверьте Bundle Resources:"
echo "   Выберите проект в Project Navigator"
echo "   Выберите Target 'PulsePlate'"
echo "   Перейдите на вкладку 'Build Phases'"
echo "   Разверните 'Copy Bundle Resources'"
echo "   Убедитесь, что MP4 файлы там есть"
echo ""
echo "4️⃣ Протестируйте:"
echo "   Запустите приложение"
echo "   Перейдите на вкладку 'Profile'"
echo "   Нажмите 'Test MP4 Animation'"
echo "   Проверьте воспроизведение видео"
echo ""
echo "5️⃣ Проверьте Bundle:"
echo "   Нажмите 'Test Bundle Files'"
echo "   Убедитесь, что файлы найдены в Bundle"
echo ""
echo "✅ Готово! MP4 файлы будут добавлены в Bundle"
echo ""
echo "📁 Файлы готовы:"
echo "  - PulsePlate/Resources/MP4/ (MP4 файлы)"
echo "  - ADD_MP4_TO_XCODE.md (подробная инструкция)"
echo "  - BundleTestView.swift (тест Bundle)"
echo ""
echo "🎬 После добавления MP4 вы сможете:"
echo "  - Воспроизводить видео анимации FitChef"
echo "  - Переключаться между анимациями"
echo "  - Интегрировать анимации в UI"
