# PR-508: Готовые команды для пуша

**Дата:** 2026-01-10
**Статус:** ✅ Все правки применены, детерминизм подтверждён

---

## ✅ Финальная проверка перед коммитом

```bash
# Run from repo root (avoid hardcoded local paths)
cd "$(git rev-parse --show-toplevel)"

# 0) Быстрый sanity: покажи, что изменилось
git status
git diff --stat

# 1) Генерация (канонично)
make openapi

# 2) Тест детерминизма
pytest -q tests/test_openapi_determinism.py

# 3) Проверить что в рабочем дереве нет "дрожи"
git status
git diff --name-only
```

---

## 📋 Минимальный набор файлов для коммита

### Обязательные (core changes)
```bash
git add scripts/generate_openapi.py
git add legacy_app.py
git add Makefile
git add tests/test_openapi_determinism.py
```

### Frontend (generated artifacts + config)
```bash
git add frontend/package.json
git add frontend/src/api/openapi.json
git add frontend/src/api/schema.ts
```

### Documentation (rules)
```bash
git add AGENTS.md
git add frontend/AGENTS.md
```

### Optional (только если реально изменился)
```bash
# Проверить, изменился ли package-lock.json
git diff frontend/package-lock.json | head -5
# Если есть изменения — добавить:
git add frontend/package-lock.json
```

### НЕ коммитим (если не меняли намеренно)
- `.github/workflows/*` — только если реально меняли для этого PR
- `scripts/normalize_schema_ts.py` — это временный файл, можно удалить или не коммитить

---

## 🚀 Команды для пуша (пошагово)

```bash
# Run from repo root (avoid hardcoded local paths)
cd "$(git rev-parse --show-toplevel)"

# 1) Новая ветка
git checkout -b fix/openapi-determinism

# 2) Генерация (канонично)
make openapi

# 3) Тест детерминизма
pytest -q tests/test_openapi_determinism.py

# 4) Проверить что изменилось
git status
git diff --stat

# 5) Добавить файлы (осознанно)
git add scripts/generate_openapi.py legacy_app.py Makefile tests/test_openapi_determinism.py
git add frontend/package.json frontend/src/api/openapi.json frontend/src/api/schema.ts
git add AGENTS.md frontend/AGENTS.md

# 6) Проверить package-lock.json (если изменился)
git diff frontend/package-lock.json | head -5
# Если есть изменения — добавить:
git add frontend/package-lock.json

# 7) Коммит
git commit -m "fix(openapi): deterministic schema generation (schema-only)

- Enable PULSEPLATE_OPENAPI=1 mode to avoid SQLAlchemy double-loading
- Skip routers that import ORM models at module level (premium_week, pro)
- Pin openapi-typescript version (7.9.1) and enable --alphabetize flag
- Make make openapi the single canonical generation path
- Add determinism test for openapi.json + schema.ts
- Hard pin env vars in OpenAPI mode (no setdefault)
- Separate frontend-install target from openapi target

Schema-only mode (temporary): Premium/pro routers disabled due to
import-time ORM dependencies. Follow-up PR-509 will eliminate these
dependencies to enable full schema generation."

# 8) Контрольные проверки перед push
git diff --name-only origin/main...HEAD
make openapi && git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts

# 9) Пуш
git push -u origin fix/openapi-determinism
```

---

## 📝 PR Description (готовый для GitHub)
