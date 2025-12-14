#!/bin/bash
# Скрипт для полного удаления Qoder с MacBook

set -e

echo "🗑️  Полное удаление Qoder с MacBook..."
echo ""

# 1. Остановить все процессы Qoder
echo "1️⃣ Останавливаем все процессы Qoder..."
pkill -f "[Q]oder" 2>/dev/null || true
sleep 2
pkill -9 -f "[Q]oder" 2>/dev/null || true
sleep 1
echo "✅ Процессы остановлены"
echo ""

# 2. Удалить приложение из /Applications
echo "2️⃣ Удаляем приложение из /Applications..."
if [ -d "/Applications/Qoder.app" ]; then
    rm -rf "/Applications/Qoder.app"
    echo "✅ Qoder.app удален из /Applications"
else
    echo "ℹ️  Qoder.app не найден в /Applications"
fi
echo ""

# 3. Удалить кэши приложения
echo "3️⃣ Удаляем кэши приложения..."
# User caches
rm -rf ~/Library/Caches/com.qoder.* 2>/dev/null || true
rm -rf ~/Library/Caches/Qoder* 2>/dev/null || true
# System caches
sudo rm -rf /Library/Caches/com.qoder.* 2>/dev/null || true
sudo rm -rf /Library/Caches/Qoder* 2>/dev/null || true
echo "✅ Кэши удалены"
echo ""

# 4. Удалить настройки и конфигурационные файлы
echo "4️⃣ Удаляем настройки и конфигурацию..."
# Preferences
rm -rf ~/Library/Preferences/com.qoder.* 2>/dev/null || true
rm -rf ~/Library/Preferences/Qoder* 2>/dev/null || true
# Application Support
rm -rf ~/Library/Application\ Support/Qoder* 2>/dev/null || true
rm -rf ~/Library/Application\ Support/com.qoder.* 2>/dev/null || true
# Saved Application State
rm -rf ~/Library/Saved\ Application\ State/com.qoder.* 2>/dev/null || true
echo "✅ Настройки удалены"
echo ""

# 5. Удалить логи
echo "5️⃣ Удаляем логи..."
rm -rf ~/Library/Logs/Qoder* 2>/dev/null || true
rm -rf ~/Library/Logs/com.qoder.* 2>/dev/null || true
sudo rm -rf /var/log/Qoder* 2>/dev/null || true
echo "✅ Логи удалены"
echo ""

# 6. Удалить контейнеры (если есть)
echo "6️⃣ Удаляем контейнеры приложения..."
rm -rf ~/Library/Containers/com.qoder.* 2>/dev/null || true
rm -rf ~/Library/Group\ Containers/com.qoder.* 2>/dev/null || true
echo "✅ Контейнеры удалены"
echo ""

# 7. Очистить кэш AppTranslocation
echo "7️⃣ Очищаем кэш AppTranslocation..."
find /var/folders -name "AppTranslocation" -type d -exec rm -rf {} + 2>/dev/null || true
echo "✅ Кэш AppTranslocation очищен"
echo ""

# 8. Удалить настройки из Keychain (опционально)
echo "8️⃣ Проверяем Keychain..."
# Список всех записей, связанных с Qoder
if security find-generic-password -a "Qoder" 2>/dev/null | grep -q "keychain"; then
    echo "⚠️  Найдены записи в Keychain, связанные с Qoder"
    echo "   Для удаления выполните вручную:"
    echo "   open /Applications/Utilities/Keychain\ Access.app"
    echo "   Найдите и удалите записи, содержащие 'Qoder'"
else
    echo "ℹ️  Записи в Keychain не найдены"
fi
echo ""

# 9. Удалить настройки из Gatekeeper
echo "9️⃣ Удаляем настройки Gatekeeper..."
spctl --remove --label "Qoder" 2>/dev/null || true
echo "✅ Настройки Gatekeeper удалены"
echo ""

# 10. Проверка завершения
echo "🔍 Проверяем, что Qoder полностью удален..."
if [ -d "/Applications/Qoder.app" ]; then
    echo "❌ ОШИБКА: Qoder.app все еще существует!"
    exit 1
fi

if ps aux | grep -i qoder | grep -v grep > /dev/null; then
    echo "⚠️  ВНИМАНИЕ: Обнаружены процессы Qoder"
    ps aux | grep -i qoder | grep -v grep
else
    echo "✅ Процессы Qoder не найдены"
fi

echo ""
echo "✅ УДАЛЕНИЕ ЗАВЕРШЕНО!"
echo ""
echo "📥 Теперь вы можете:"
echo "   1. Скачать Qoder с официального сайта"
echo "   2. Установить его в /Applications/"
echo "   3. Запустить scripts/setup_qoder.sh для правильной настройки"
echo ""
