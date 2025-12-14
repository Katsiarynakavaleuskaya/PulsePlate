#!/bin/bash
# Скрипт для правильной установки Qoder

set -e

echo "🔧 Настройка Qoder..."

# 1. Остановить все процессы
echo "1️⃣ Останавливаем процессы Qoder..."
# Сначала пытаемся корректно завершить процессы Qoder (SIGTERM)
# Используем шаблон [Q]oder, чтобы не зацепить саму команду pkill
pkill -f "[Q]oder" 2>/dev/null || true
sleep 2

# Затем принудительно завершаем оставшиеся процессы (SIGKILL), если они всё ещё живы
pkill -9 -f "[Q]oder" 2>/dev/null || true
sleep 1

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
# Note: May require sudo for full cleanup
if ! find /var/folders -name "AppTranslocation" -type d -exec rm -rf {} + 2>/dev/null; then
    echo "⚠️ Не удалось очистить AppTranslocation кэш (может требоваться sudo)"
else
    echo "✅ Кэш очищен"
fi

# 8. Запустить приложение
echo "7️⃣ Запускаем Qoder..."
open -a /Applications/Qoder.app

# 9. Проверить результат
sleep 5

# Найти запущенный процесс Qoder по имени бинарника внутри .app
qoder_pids="$(pgrep -f "Qoder.app/Contents/MacOS/Qoder" 2>/dev/null || true)"
if [ -z "${qoder_pids}" ]; then
    # Запасной вариант: искать по имени .app, если более точный шаблон не сработал
    qoder_pids="$(pgrep -f "Qoder.app" 2>/dev/null || true)"
fi

if [ -z "${qoder_pids}" ]; then
    echo ""
    echo "⚠️ Не удалось обнаружить запущенный процесс Qoder"
    echo "   Проверьте, запустилось ли приложение корректно"
    exit 1
fi

is_applications=false
is_apptranslocation=false

for pid in ${qoder_pids}; do
    exe_path=""

    # Linux-путь к бинарнику процесса, если доступен
    if [ -r "/proc/${pid}/exe" ]; then
        exe_path="$(readlink "/proc/${pid}/exe" 2>/dev/null || true)"
    fi

    # На macOS используем lsof, чтобы найти путь к Qoder.app
    if [ -z "${exe_path}" ] && command -v lsof >/dev/null 2>&1; then
        exe_path="$(lsof -p "${pid}" 2>/dev/null | awk '/Qoder\.app/ {print $9; exit}')"
    fi

    # Если путь не удалось определить, пропускаем этот PID
    if [ -z "${exe_path}" ]; then
        continue
    fi

    if echo "${exe_path}" | grep -q "AppTranslocation"; then
        is_apptranslocation=true
    fi

    if echo "${exe_path}" | grep -q "/Applications/Qoder.app"; then
        is_applications=true
    fi
done

echo ""

if [ "${is_applications}" = true ] && [ "${is_apptranslocation}" != true ]; then
    echo "✅ УСПЕХ! Qoder запущен правильно из /Applications/"
    echo "   Без AppTranslocation"
elif [ "${is_apptranslocation}" = true ]; then
    echo "⚠️ Qoder все еще запускается через AppTranslocation"
    echo ""
    echo "💡 Решения:"
    echo "   1. Переустановите Qoder из официального источника"
    echo "   2. Или разрешите вручную:"
    echo "      System Settings → Privacy & Security → Allow Qoder"
    echo "   3. Или в System Settings → Privacy & Security → Security → Allow apps from: App Store and identified developers"
else
    echo "✅ Qoder запущен"
fi
