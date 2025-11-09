#!/bin/bash
# 🔧 Оптимизация .zshrc для быстрой загрузки
# Usage: ./scripts/optimize_zshrc.sh

set -euo pipefail

ZSHRC_FILE="$HOME/.zshrc"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALIASES_SCRIPT="$PROJECT_ROOT/setup_cli_aliases.sh"

echo "🔧 Оптимизация .zshrc для быстрой загрузки..."
echo ""

# Проверяем, существует ли файл
if [ ! -f "$ZSHRC_FILE" ]; then
    echo "❌ Файл $ZSHRC_FILE не найден"
    exit 1
fi

# Создаем резервную копию
BACKUP_FILE="${ZSHRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ZSHRC_FILE" "$BACKUP_FILE"
echo "✅ Создана резервная копия: $BACKUP_FILE"
echo ""

# Проверяем, есть ли уже оптимизированная загрузка
if grep -q "SETUP_ALIASES_QUIET" "$ZSHRC_FILE"; then
    echo "⚠️  Похоже, оптимизация уже применена"
    echo "   Проверьте строки с SETUP_ALIASES_QUIET в $ZSHRC_FILE"
    echo ""
fi

# Ищем строку с загрузкой setup_cli_aliases.sh
if grep -q "setup_cli_aliases.sh" "$ZSHRC_FILE"; then
    echo "📝 Найдена загрузка setup_cli_aliases.sh"
    echo "   Обновляю для использования тихого режима..."
    echo ""

    # Заменяем обычную загрузку на тихую
    sed -i.bak "s|source.*setup_cli_aliases.sh|SETUP_ALIASES_QUIET=true source \"\$ALIASES_SCRIPT\"|g" "$ZSHRC_FILE"
    rm -f "${ZSHRC_FILE}.bak"

    # Убеждаемся, что ALIASES_SCRIPT установлен перед использованием
    if ! grep -q "ALIASES_SCRIPT=" "$ZSHRC_FILE"; then
        # Добавляем определение ALIASES_SCRIPT перед загрузкой
        sed -i.bak "/setup_cli_aliases.sh/i\\
ALIASES_SCRIPT=\"\$HOME/Developer/BMI-App_2025_clean/setup_cli_aliases.sh\"\\
" "$ZSHRC_FILE"
        rm -f "${ZSHRC_FILE}.bak"
    fi

    echo "✅ Обновлено для тихого режима загрузки"
else
    echo "ℹ️  Автоматическая загрузка setup_cli_aliases.sh не найдена"
    echo "   Добавьте вручную в $ZSHRC_FILE:"
    echo ""
    echo "   # PulsePlate aliases (тихая загрузка)"
    echo "   ALIASES_SCRIPT=\"\$HOME/Developer/BMI-App_2025_clean/setup_cli_aliases.sh\""
    echo "   if [[ -f \"\$ALIASES_SCRIPT\" ]] && [[ \$- == *i* ]]; then"
    echo "       SETUP_ALIASES_QUIET=true source \"\$ALIASES_SCRIPT\""
    echo "   fi"
    echo ""
fi

echo ""
echo "✅ Оптимизация завершена"
echo ""
echo "💡 Для применения изменений выполните:"
echo "   source ~/.zshrc"
echo ""
echo "📊 Для диагностики проблем используйте:"
echo "   $PROJECT_ROOT/scripts/diagnose_cursor.sh"
