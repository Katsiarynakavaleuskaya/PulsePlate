#!/bin/bash
# 🎯 Claude Code с автоматической загрузкой роли PulsePlate
# Usage: ./scripts/claude_with_role.sh [дополнительные аргументы claude]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROLE_FILE="$PROJECT_ROOT/.claude/role.md"

# Проверяем наличие файла роли
if [ ! -f "$ROLE_FILE" ]; then
    echo "❌ Error: Role file not found: $ROLE_FILE"
    exit 1
fi

# Загружаем роль
ROLE_CONTENT=$(cat "$ROLE_FILE")

# Запускаем Claude Code с ролью
cd "$PROJECT_ROOT"
exec claude --append-system-prompt "$ROLE_CONTENT" "$@"
