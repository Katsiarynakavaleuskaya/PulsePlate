#!/usr/bin/env bash
# Git post-commit hook helper: remind about npm tooling sync after commits.

set -euo pipefail

cat <<'MSG'
🔁  Не забудь после коммита:
    • проверить, что изменения в package-lock.json добавлены в индекс (`git add package-lock.json`)
    • при необходимости выполнить `npm ci`, чтобы локальные инструменты совпадали с CI
MSG
