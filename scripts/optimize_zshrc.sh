#!/bin/bash
# 🔧 Оптимизация .zshrc для быстрой загрузки
# Usage: ./scripts/optimize_zshrc.sh

set -euo pipefail

ZSHRC_FILE="$HOME/.zshrc"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALIASES_SCRIPT="$PROJECT_ROOT/setup_cli_aliases.sh"

# Validate PROJECT_ROOT points to a valid project
if [ ! -f "$PROJECT_ROOT/setup_cli_aliases.sh" ]; then
    echo "❌ Error: PROJECT_ROOT ($PROJECT_ROOT) does not point to a valid project"
    echo "   Expected file not found: $PROJECT_ROOT/setup_cli_aliases.sh"
    exit 1
fi

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

    # KNOWN LIMITATION: Comment-stripping approach
    # ==============================================
    # The sed 's/#.*//' command removes everything from # to end of line, which can
    # incorrectly strip # characters inside quoted strings (e.g., URLs with #fragment,
    # hashtag values, or other uses of # within quotes).
    #
    # Problematic examples:
    #   - URL="https://example.com/page#section"  → becomes URL="https://example.com/page"
    #   - TAG="#hashtag"  → becomes TAG=""
    #   - COMMENT='Line with # symbol'  → becomes COMMENT='Line with '
    #
    # This limitation is acceptable for this script because:
    # 1. We only check for variable definitions and source commands (which typically
    #    don't contain # in their values)
    # 2. False positives in comments won't break functionality - they'll be preserved
    # 3. Edge cases with quotes/escapes are rare and not critical for this use case
    #
    # For production use, consider using a proper shell parser or more sophisticated
    # quote-aware comment removal.

    # Pre-check: Scan for # characters inside quoted strings or URLs
    echo "🔍 Pre-checking for # characters inside quoted strings or URLs..."
    if grep -E '(https?://[^[:space:]]*#|["'"'"'].*#.*["'"'"'])' "$ZSHRC_FILE" >/dev/null 2>&1; then
        echo ""
        echo "⚠️  ⚠️  ⚠️  WARNING: POTENTIAL RISK DETECTED ⚠️  ⚠️  ⚠️" >&2
        echo "" >&2
        echo "The target file contains # characters inside quoted strings or URLs." >&2
        echo "The sed-based comment stripping may incorrectly remove these # characters," >&2
        echo "potentially corrupting URLs, hashtags, or other quoted content." >&2
        echo "" >&2
        echo "Examples found:" >&2
        grep -E '(https?://[^[:space:]]*#|["'"'"'].*#.*["'"'"'])' "$ZSHRC_FILE" | head -5 | sed 's/^/  /' >&2
        echo "" >&2
        echo "Do you want to continue? (yes/no)" >&2
        read -r user_response
        if [ "$user_response" != "yes" ]; then
            echo "Aborted by user." >&2
            exit 1
        fi
        echo ""
    fi

    # Prominent warning block
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "⚠️  CRITICAL WARNING: COMMENT STRIPPING RISK" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo "" >&2
    echo "This script uses sed-based comment stripping which may incorrectly" >&2
    echo "remove # characters inside quoted strings (URLs, hashtags, etc.)." >&2
    echo "" >&2
    echo "A backup will be created at: $BACKUP_FILE" >&2
    echo "Please review the diff preview before confirming changes." >&2
    echo "" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo ""

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
        # Check if the original line is a comment BEFORE any processing
        # This prevents commented-out source lines from being removed
        if echo "$line" | grep -qE '^[[:space:]]*#'; then
            # Preserve commented lines as-is
            echo "$line" >> "$TEMP_FILE"
            continue
        fi

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

    # Show unified diff preview before applying changes
    echo ""
    echo "📋 Preview of changes (unified diff):"
    echo "═══════════════════════════════════════════════════════════════"
    if diff -u "$ZSHRC_FILE" "$TEMP_FILE" || true; then
        echo "(No differences found)"
    fi
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "Do you want to apply these changes? (yes/no)"
    read -r apply_response
    if [ "$apply_response" != "yes" ]; then
        echo "Changes not applied. Original file preserved."
        rm -f "$TEMP_FILE"
        trap - EXIT INT TERM
        exit 0
    fi
    echo ""

    # Validation: Check syntax before replacing original file
    if ! zsh -n "$TEMP_FILE" 2>/dev/null; then
        echo "❌ ERROR: Syntax validation failed for modified file"
        echo "   The modified file has syntax errors. Restoring from backup."
        echo "   Backup location: $BACKUP_FILE"
        cp "$BACKUP_FILE" "$ZSHRC_FILE"
        rm -f "$TEMP_FILE"
        trap - EXIT INT TERM
        exit 1
    fi

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
