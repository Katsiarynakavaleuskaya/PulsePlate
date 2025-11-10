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
    echo "ℹ️  Повторное применение не требуется. Прерываю выполнение."
    exit 0
fi

# Ищем строку с загрузкой setup_cli_aliases.sh
if grep -q "setup_cli_aliases.sh" "$ZSHRC_FILE"; then
    echo "📝 Найдена загрузка setup_cli_aliases.sh"
    echo "   Обновляю для использования тихого режима..."
    echo ""

    # Создаем временный файл для безопасного редактирования
    TEMP_FILE=$(mktemp "${ZSHRC_FILE}.tmp.XXXXXX")
    trap 'rm -f "$TEMP_FILE"' EXIT INT TERM

    # Обрабатываем файл построчно, исключая строки с setup_cli_aliases.sh
    # SIMPLIFIED: Use basic heuristics instead of complex quote/escape parsing
    # We remove lines that look like source/. commands for setup_cli_aliases.sh
    # This is safe because:
    # 1. These lines are typically uncommented and at start of line
    # 2. False positives (commented lines) won't break functionality - they'll be preserved
    # 3. Edge cases with quotes/escapes in comments are rare and not critical for this use case
    has_project_root=false
    has_aliases_script=false

    while IFS= read -r line || [ -n "$line" ]; do
        # Simple approach: Remove shell comments (# to end of line)
        # NOTE: This may incorrectly strip # inside strings, but since we're only
        # checking for variable definitions and source commands (which shouldn't
        # appear in comments), this trade-off is acceptable for simplicity
        cleaned_line=$(echo "$line" | sed 's/#.*//')

        # Отслеживаем наличие определений переменных ПЕРЕД фильтрацией
        if echo "$cleaned_line" | grep -qiE "^[[:space:]]*PROJECT_ROOT[[:space:]]*="; then
            has_project_root=true
        fi
        if echo "$cleaned_line" | grep -qiE "^[[:space:]]*ALIASES_SCRIPT[[:space:]]*="; then
            has_aliases_script=true
        fi

        # Пропускаем строки, которые являются командами source/. для setup_cli_aliases.sh
        # After removing comments, check if line contains source/. command
        if echo "$cleaned_line" | grep -qiE "(source|\.)\s+.*setup_cli_aliases\.sh"; then
            continue
        fi

        # Сохраняем все остальные строки (включая оригинальные с комментариями)
        echo "$line" >> "$TEMP_FILE"
    done < "$ZSHRC_FILE"

    # Validation: warn if variables were set but script invocation was skipped
    if [ "$has_project_root" = true ] || [ "$has_aliases_script" = true ]; then
        if ! grep -q "setup_cli_aliases\.sh" "$TEMP_FILE"; then
            echo "⚠️  Warning: PROJECT_ROOT/ALIASES_SCRIPT found but setup_cli_aliases.sh invocation was removed" >&2
        fi
    fi

    # Добавляем определения переменных, если их нет
    if [ "$has_project_root" = false ]; then
        echo "PROJECT_ROOT=\"$PROJECT_ROOT\"" >> "$TEMP_FILE"
    fi
    if [ "$has_aliases_script" = false ]; then
        echo "ALIASES_SCRIPT=\"\$PROJECT_ROOT/setup_cli_aliases.sh\"" >> "$TEMP_FILE"
    fi

    # Добавляем канонический двухстрочный блок загрузки
    echo "SETUP_ALIASES_QUIET=true" >> "$TEMP_FILE"
    echo "source \"\$ALIASES_SCRIPT\"" >> "$TEMP_FILE"

    # Создаем резервную копию перед атомарной заменой
    cp "$ZSHRC_FILE" "${ZSHRC_FILE}.bak"

    # Атомарно заменяем оригинальный файл
    mv "$TEMP_FILE" "$ZSHRC_FILE"
    trap - EXIT INT TERM

    echo "✅ Обновлено для тихого режима загрузки"
else
    echo "ℹ️  Автоматическая загрузка setup_cli_aliases.sh не найдена"
    echo "   Добавьте вручную в $ZSHRC_FILE:"
    echo ""
    echo "   # PulsePlate aliases (тихая загрузка)"
    echo "   ALIASES_SCRIPT=\"$ALIASES_SCRIPT\""
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
