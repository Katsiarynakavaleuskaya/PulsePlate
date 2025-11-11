#!/bin/bash
# 🔧 Продвинутая оптимизация .zshrc для максимальной производительности
# Usage: ./scripts/optimize_zshrc_advanced.sh [--dry-run] [--force] [--help]
# RU: Скрипт всегда сохраняет резервную копию ~/.zshrc и записывает оптимизированный блок в ~/.zshrc.optimized перед изменениями.
# EN: The script always creates a timestamped backup of ~/.zshrc and writes the optimised block to ~/.zshrc.optimized before any mutation.

set -euo pipefail

ZSHRC_FILE="$HOME/.zshrc"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPTIMIZED_FILE="${ZSHRC_FILE}.optimized"

print_usage() {
    cat <<'USAGE'
Usage: ./scripts/optimize_zshrc_advanced.sh [--dry-run] [--force] [--help]

Options:
  --dry-run   Show analysis and diffs only; no files will be modified.
  --force     Replace the entire ~/.zshrc with the optimised block (requires explicit confirmation).
  --help      Display this help message.

By default the script performs a safe merge:
  • creates ~/.zshrc.backup.<timestamp>
  • writes the optimised block to ~/.zshrc.optimized
  • replaces the existing “BEGIN/END PULSEPLATE OPTIMIZED BLOCK” section or appends it if missing.
USAGE
}

# Parse flags
DRY_RUN=false
FORCE=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --force)
            FORCE=true
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            echo "❌ Unknown flag: $1"
            print_usage
            exit 1
            ;;
    esac
    shift
done

echo "🔧 Продвинутая оптимизация .zshrc..."
if [ "$DRY_RUN" = true ]; then
    echo "   [DRY-RUN MODE: No changes will be made]"
fi
echo ""

if [ ! -f "$ZSHRC_FILE" ]; then
    echo "❌ Error: $ZSHRC_FILE does not exist or is not a regular file"
    exit 1
fi

# Timestamped backup (non destructive path)
if [ "$DRY_RUN" = false ]; then
    BACKUP_FILE="${ZSHRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$ZSHRC_FILE" "$BACKUP_FILE"
    echo "✅ Создана резервная копия: $BACKUP_FILE"
    echo ""
else
    BACKUP_FILE="(dry-run: backup not created)"
fi

# Quick analysis of current setup (mirrors legacy behaviour)
echo "📊 Анализ текущей конфигурации:"
echo ""
if grep -q "compinit.*-C" "$ZSHRC_FILE"; then
    echo "✅ compinit уже оптимизирован (кеширование)"
else
    echo "⚠️  compinit не оптимизирован"
fi
if grep -q '\[[[:space:]]*\$-[[:space:]]*==[[:space:]]*\*i\*[[:space:]]*\]' "$ZSHRC_FILE"; then
    echo "✅ Проверка интерактивности присутствует"
else
    echo "⚠️  Проверка интерактивности отсутствует"
fi
if grep -q "SETUP_ALIASES_QUIET" "$ZSHRC_FILE"; then
    echo "✅ Тихая загрузка алиасов настроена"
else
    echo "⚠️  Тихая загрузка алиасов не настроена"
fi
echo ""

echo "💡 Рекомендации по оптимизации:"
echo "1. compinit должен использовать кеширование (compinit -C -i)"
echo "2. Тяжелые операции только в интерактивных сессиях (if [[ \$- == *i* ]])"
echo "3. Pyenv полная инициализация выполняется лениво"
echo "4. Docker completions подключаются только при необходимости"
echo ""

# Confirmation to proceed
if [ "$DRY_RUN" = false ]; then
    read -p "Применить оптимизации? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Оптимизации не применены"
        exit 0
    fi
fi

echo "📝 Генерирую оптимизированную версию..."

# Temporary artefacts
TEMP_NEW_CONFIG=$(mktemp)
TEMP_BLOCK=$(mktemp)
MERGED_PREVIEW=$(mktemp)
cleanup() {
    rm -f "$TEMP_NEW_CONFIG" "$TEMP_BLOCK" "$MERGED_PREVIEW"
}
trap cleanup EXIT

# Base optimised snippet
cat > "$TEMP_NEW_CONFIG" <<'EOF'
# Оптимизированная загрузка для быстрого старта терминала
# Тяжелые операции выполняются только в интерактивных сессиях

# Homebrew (быстро, можно выполнять всегда)
eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null

# Pyenv - только PATH в .zprofile, полная инициализация только в интерактивных сессиях
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"

# Docker completions - только в интерактивных сессиях
if [[ $- == *i* ]]; then
    # Docker CLI completions (ленивая загрузка)
    if [ -d "$HOME/.docker/completions" ]; then
        fpath=("$HOME/.docker/completions" $fpath)
    fi

    # Оптимизированная инициализация системы автодополнения
    autoload -Uz compinit
    if [[ -n ${ZDOTDIR:-$HOME}/.zcompdump(#qN.mh+24) ]]; then
        compinit -i
    else
        compinit -C -i
    fi

    # Pyenv полная инициализация (только в интерактивных сессиях)
    if command -v pyenv >/dev/null; then
        eval "$(pyenv init -)"
    fi
fi

# PulsePlate aliases (тихая загрузка для быстрого старта терминала)
if [[ $- == *i* ]]; then
    ALIASES_SCRIPT="__PROJECT_ROOT__/setup_cli_aliases.sh"
    if [[ -f "$ALIASES_SCRIPT" ]]; then
        SETUP_ALIASES_QUIET=true source "$ALIASES_SCRIPT"
    fi
fi
EOF

# Replace placeholder with actual project root using sed
# More portable approach: use sed with output redirection
sed "s|__PROJECT_ROOT__|${PROJECT_ROOT}|g" "$TEMP_NEW_CONFIG" > "${TEMP_NEW_CONFIG}.tmp" || {
    rm -f "${TEMP_NEW_CONFIG}.tmp"
    echo "❌ Error: sed command failed" >&2
    exit 1
}
mv "${TEMP_NEW_CONFIG}.tmp" "$TEMP_NEW_CONFIG"

# Wrap snippet with markers
BLOCK_START="# BEGIN PULSEPLATE OPTIMIZED BLOCK"
BLOCK_END="# END PULSEPLATE OPTIMIZED BLOCK"
{
    printf "%s\n" "$BLOCK_START"
    cat "$TEMP_NEW_CONFIG"
    printf "%s\n" "$BLOCK_END"
} > "$TEMP_BLOCK"

# Pre-flight check: verify python3 exists
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Error: python3 is required for this script" >&2
    exit 1
fi

# Compute safe-merge preview
python3 - <<'PY' "$ZSHRC_FILE" "$TEMP_BLOCK" "$MERGED_PREVIEW" "$BLOCK_START" "$BLOCK_END"
import sys
from pathlib import Path

zshrc_path, block_path, merged_path, block_start, block_end = sys.argv[1:]
current = Path(zshrc_path).read_text(encoding="utf-8")
block = Path(block_path).read_text(encoding="utf-8").rstrip() + "\n"

if block_start in current and block_end in current:
    pre, _, trailing = current.partition(block_start)
    _, _, post = trailing.partition(block_end)
    new_text = pre.rstrip("\n") + "\n" + block + post.lstrip("\n")
else:
    suffix = "" if current.endswith("\n") or current == "" else "\n"
    new_text = current + suffix + "\n" + block

Path(merged_path).write_text(new_text, encoding="utf-8")
PY

echo ""
echo "📋 Diff безопасного мерджа (unified diff):"
diff -u "$ZSHRC_FILE" "$MERGED_PREVIEW" || true

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "✅ Dry-run завершен. Конфигурация не изменена."
    echo "   Просмотрите временный блок: $TEMP_BLOCK"
    exit 0
fi

# Persist optimised block for manual audit
cp "$TEMP_BLOCK" "$OPTIMIZED_FILE"
echo ""
echo "✅ Оптимизированный блок сохранён: $OPTIMIZED_FILE"

# Syntax validation
echo ""
echo "🔍 Проверяю синтаксис оптимизированного блока..."
if ! zsh -n "$TEMP_BLOCK" 2>&1; then
    echo "❌ Ошибка синтаксиса! Оригинальный файл не изменён."
    exit 1
fi
echo "✅ Синтаксис корректен"

if [ "$FORCE" = true ]; then
    echo ""
    echo "⚠️  FORCE MODE: полный перезапись $ZSHRC_FILE из $OPTIMIZED_FILE."
    read -p "Type 'OVERWRITE' to confirm full replacement: " -r
    REPLY_TRIMMED=$(echo "$REPLY" | xargs)
    echo ""
    if [[ "$REPLY_TRIMMED" != "OVERWRITE" ]]; then
        echo "❌ Полная замена отменена. Исходный файл не изменён."
        exit 0
    fi
    echo "📝 Выполняю полную замену..."
    cp "$OPTIMIZED_FILE" "$ZSHRC_FILE"
else
    echo ""
    read -p "Применить безопасный мердж (замена/добавление блока)? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📝 Применяю безопасный мердж..."
        cp "$MERGED_PREVIEW" "$ZSHRC_FILE"
    else
        echo "ℹ️  Оригинальный .zshrc оставлен без изменений. Используйте $OPTIMIZED_FILE для ручного аудита."
        exit 0
    fi
fi

echo ""
echo "✅ Оптимизации применены без удаления пользовательских настроек"
echo "💾 Резервная копия: $BACKUP_FILE"
echo "🧩 Оптимизированный блок: $OPTIMIZED_FILE"
echo ""
echo "💡 Для применения изменений выполните:"
echo "   source ~/.zshrc"
echo ""
echo "📊 Для проверки производительности:"
echo "   time zsh -c 'source ~/.zshrc && echo Loaded'"
echo ""
echo "📊 Для диагностики проблем используйте:"
echo "   $PROJECT_ROOT/scripts/diagnose_cursor.sh"
