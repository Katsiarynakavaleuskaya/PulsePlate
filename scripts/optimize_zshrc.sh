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

    # Создаем временный файл для безопасного редактирования
    TEMP_FILE=$(mktemp "${ZSHRC_FILE}.tmp.XXXXXX")
    trap "rm -f '$TEMP_FILE'" EXIT INT TERM

    # Обрабатываем файл построчно, исключая строки с setup_cli_aliases.sh
    # Паттерн допускает: пробелы, комментарии, различные формы кавычек и путей
    # Также отслеживаем, определены ли уже PROJECT_ROOT или ALIASES_SCRIPT
    has_project_root=false
    has_aliases_script=false

    while IFS= read -r line || [ -n "$line" ]; do
        # Проверяем, содержит ли строка setup_cli_aliases.sh (с учетом вариаций)
        # Удаляем комментарии и лишние пробелы для проверки
        cleaned_line=$(echo "$line" | sed 's/#.*$//' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')

        # Отслеживаем наличие определений переменных ПЕРЕД фильтрацией
        if echo "$cleaned_line" | grep -qiE "^[[:space:]]*PROJECT_ROOT[[:space:]]*="; then
            has_project_root=true
        fi
        if echo "$cleaned_line" | grep -qiE "^[[:space:]]*ALIASES_SCRIPT[[:space:]]*="; then
            has_aliases_script=true
        fi

        # Пропускаем строки, которые являются командами source/. для setup_cli_aliases.sh
        # Паттерн допускает: source/. перед именем, различные кавычки, пути, комментарии
        # НО сохраняем определения переменных (PROJECT_ROOT, ALIASES_SCRIPT)
        if echo "$cleaned_line" | grep -qiE "(source|\.)\s+.*setup_cli_aliases\.sh"; then
            continue
        fi

        # Сохраняем все остальные строки (включая определения переменных)
        echo "$line" >> "$TEMP_FILE"
    done < "$ZSHRC_FILE"

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
