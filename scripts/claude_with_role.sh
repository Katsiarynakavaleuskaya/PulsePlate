#!/bin/bash
# 🎯 Claude Code с автоматической загрузкой роли PulsePlate
# Usage: ./scripts/claude_with_role.sh [дополнительные аргументы claude]
#
# Note: Claude Code автоматически читает файлы из .claude/ директории,
# поэтому не нужно использовать --append-system-prompt, что предотвращает
# segmentation fault в Bun при передаче больших промптов через аргументы.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ROLE_DIR="$PROJECT_ROOT/.claude"

# Проверяем наличие директории с ролями
if [ ! -d "$ROLE_DIR" ]; then
    echo "❌ Error: Role directory not found: $ROLE_DIR" >&2
    exit 1
fi

# Проверяем наличие команды claude
if ! command -v claude >/dev/null 2>&1; then
    echo "❌ Error: 'claude' command not found in PATH" >&2
    echo "" >&2
    echo "Please install the Claude/Cursor CLI:" >&2
    echo "  - Visit https://claude.ai/download or https://cursor.sh" >&2
    echo "  - Or install via your package manager" >&2
    exit 1
fi

# Запускаем Claude Code в директории проекта
# Claude Code автоматически загрузит роли из .claude/ директории
cd "$PROJECT_ROOT"
exec claude "$@"
