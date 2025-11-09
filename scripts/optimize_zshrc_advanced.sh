#!/bin/bash
# 🔧 Продвинутая оптимизация .zshrc для максимальной производительности
# Usage: ./scripts/optimize_zshrc_advanced.sh

set -euo pipefail

ZSHRC_FILE="$HOME/.zshrc"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🔧 Продвинутая оптимизация .zshrc..."
echo ""

# Создаем резервную копию
BACKUP_FILE="${ZSHRC_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$ZSHRC_FILE" "$BACKUP_FILE"
echo "✅ Создана резервная копия: $BACKUP_FILE"
echo ""

# Проверяем текущую конфигурацию
echo "📊 Анализ текущей конфигурации:"
echo ""

# Проверяем наличие оптимизаций
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
echo ""
echo "1. compinit должен использовать кеширование:"
echo "   compinit -C -i  # вместо просто compinit"
echo ""
echo "2. Тяжелые операции должны выполняться только в интерактивных сессиях:"
echo "   if [[ \$- == *i* ]]; then ... fi"
echo ""
echo "3. Pyenv полная инициализация только в интерактивных сессиях"
echo ""
echo "4. Docker completions загружать лениво"
echo ""

# Предлагаем применить оптимизации
read -p "Применить оптимизации? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📝 Применяю оптимизации..."

    # Создаем оптимизированную версию
    cat > "$ZSHRC_FILE" << 'EOF'
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
    # Кеширование compinit для ускорения последующих запусков
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
    ALIASES_SCRIPT="$HOME/Developer/BMI-App_2025_clean/setup_cli_aliases.sh"
    if [[ -f "$ALIASES_SCRIPT" ]]; then
        # Тихая загрузка - без вывода сообщений при автоматическом запуске
        SETUP_ALIASES_QUIET=true source "$ALIASES_SCRIPT"
    fi
fi
EOF

    echo "✅ Оптимизации применены"
    echo ""
    echo "💡 Для применения изменений выполните:"
    echo "   source ~/.zshrc"
    echo ""
    echo "📊 Для проверки производительности:"
    echo "   time zsh -c 'source ~/.zshrc && echo Loaded'"
else
    echo "❌ Оптимизации не применены"
fi

echo ""
echo "📊 Для диагностики проблем используйте:"
echo "   $PROJECT_ROOT/scripts/diagnose_cursor.sh"
