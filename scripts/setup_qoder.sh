#!/bin/bash
# Скрипт для правильной установки Qoder

set -e

echo "🔧 Настройка Qoder..."

# 1. Остановить все процессы
echo "1️⃣ Останавливаем процессы Qoder..."
pkill -9 -f Qoder 2>/dev/null || true
sleep 2

# 2. Удалить старое приложение (если нужно переустановить)
if [ "$1" == "--reinstall" ]; then
    echo "2️⃣ Удаляем старое приложение..."
    rm -rf /Applications/Qoder.app
    echo "✅ Старое приложение удалено"
fi

# 3. Проверить наличие приложения
if [ ! -d "/Applications/Qoder.app" ]; then
    echo "⚠️ Qoder.app не найден в /Applications/"
    echo "📥 Скачайте Qoder с официального сайта и установите вручную"
    echo "   После установки запустите этот скрипт снова"
    exit 1
fi

# 4. Удалить карантин (если есть)
echo "3️⃣ Удаляем карантин..."
xattr -cr /Applications/Qoder.app 2>/dev/null || true
echo "✅ Карантин удален"

# 5. Проверить подпись
echo "4️⃣ Проверяем подпись..."
if codesign --verify --verbose /Applications/Qoder.app 2>&1 | grep -q "valid on disk"; then
    echo "✅ Подпись валидна"
else
    echo "⚠️ Подпись нарушена - возможно нужна переустановка"
    echo "   Попробуем разрешить запуск через Gatekeeper..."
fi

# 6. Разрешить запуск через spctl (если нужно)
echo "5️⃣ Настраиваем Gatekeeper..."
spctl --add --label "Qoder" /Applications/Qoder.app 2>/dev/null || true

# 7. Очистить кэш AppTranslocation
echo "6️⃣ Очищаем кэш AppTranslocation..."
find /var/folders -name "AppTranslocation" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ Кэш очищен"

# 8. Запустить приложение
echo "7️⃣ Запускаем Qoder..."
open -a /Applications/Qoder.app

# 9. Проверить результат
sleep 5
if ps aux | grep -E "/Applications/Qoder.app" | grep -v grep | grep -v AppTranslocation > /dev/null; then
    echo ""
    echo "✅ УСПЕХ! Qoder запущен правильно из /Applications/"
    echo "   Без AppTranslocation"
else
    if ps aux | grep AppTranslocation | grep -i qoder > /dev/null; then
        echo ""
        echo "⚠️ Qoder все еще запускается через AppTranslocation"
        echo ""
        echo "💡 Решения:"
        echo "   1. Переустановите Qoder из официального источника"
        echo "   2. Или разрешите вручную:"
        echo "      System Settings → Privacy & Security → Allow Qoder"
        echo "   3. Или запустите: sudo spctl --master-disable"
    else
        echo "✅ Qoder запущен"
    fi
fi
