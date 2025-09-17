#!/usr/bin/env bash
# Устанавливает post-commit hook, который напоминает про npm ci и package-lock.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_FILE="$ROOT_DIR/.git/hooks/post-commit"

cat <<'INFO'
🔧 Установка post-commit напоминания...
INFO

cat <<'HOOK' >"$HOOK_FILE"
#!/usr/bin/env bash
"$(dirname "$0")/../../scripts/post_commit_reminder.sh"
HOOK

chmod +x "$HOOK_FILE"

cat <<'DONE'
✅ post-commit hook установлен.
Он будет выводить напоминание после каждого коммита.
DONE
