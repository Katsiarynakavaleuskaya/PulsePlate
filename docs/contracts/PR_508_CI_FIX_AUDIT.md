# PR-508: CI Fix Audit

**Дата:** 2026-01-11
**Статус:** ✅ Все проверки пройдены

---

## 1) Проверка дублирования установки deps

### Python-setup action анализ

`.github/actions/python-setup/action.yml` устанавливает:
- **Base dependencies**: `requirements-dev.txt` или `requirements.txt` (БЕЗ `constraints.txt`)
- **Dev deps**: `pre-commit`, `bandit` (если `install-dev-deps: "true"`)
- **Test deps**: `pytest`, `pytest-cov` (если `install-test-deps: "true"`)

### Наш шаг в openapi-sync

```yaml
- name: Install backend dependencies
  run: |
    python -m pip install -r requirements.txt -c constraints.txt
```

### Вывод

✅ **Нет дублирования:**
- `python-setup` устанавливает `requirements.txt` БЕЗ `constraints.txt`
- Наш шаг устанавливает `requirements.txt` С `constraints.txt` (более строго)
- Это **уточнение**, а не дублирование
- `pip install` с `-c constraints.txt` переустановит пакеты с правильными версиями (idempотентно)

**Рекомендация:** Оставить как есть. Это гарантирует детерминизм установки зависимостей.

---

## 2) Проверка .secrets.baseline

### Diff анализ

```diff
- "line_number": 151
+ "line_number": 188
- "generated_at": "2026-01-10T00:02:24Z"
+ "generated_at": "2026-01-10T21:08:27Z"
```

### Вывод

✅ **Изменения минимальные и ожидаемые:**
- `line_number` изменился из-за добавления строк в `ci.yml` (добавлен `openapi-sync` job)
- `generated_at` обновился (нормально для detect-secrets)
- **Нет новых секретов** (только обновление метаданных)

✅ **Baseline используется:**
- `.pre-commit-config.yaml` содержит: `args: [--baseline, .secrets.baseline]`
- Pre-commit hook использует baseline корректно

**Рекомендация:** Оставить в PR-508. Это требование pre-commit hook.

---

## 3) Мини-чек перед merge

### ✅ 1) OpenAPI determinism тест

```bash
pytest -q tests/test_openapi_determinism.py
# Result: PASSED
```

### ✅ 2) OpenAPI artifacts синхронизированы

```bash
make openapi-check
# Result: PASSED (git diff --exit-code = 0)
```

### ✅ 3) CI-изменения только по делу

```diff
+  openapi-sync:
+    name: OpenAPI sync (backend -> frontend artifacts)
+    ...
+    - name: Install backend dependencies
+      run: |
+        python -m pip install -r requirements.txt -c constraints.txt
+    ...
+  test-pr:
-    needs: pr_scope_guard
+    needs: [pr_scope_guard, openapi-sync]
```

**Вывод:** Только необходимые изменения для OpenAPI determinism.

### ✅ 4) Проверка на случайный мусор

Файлы в PR:
- ✅ Core changes: `scripts/generate_openapi.py`, `legacy_app.py`, `Makefile`, `tests/test_openapi_determinism.py`
- ✅ Frontend: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/api/openapi.json`, `frontend/src/api/schema.ts`
- ✅ CI: `.github/workflows/ci.yml`, `.github/workflows/frontend-ci.yml`
- ✅ Docs: `AGENTS.md`, `frontend/AGENTS.md`, `docs/contracts/*`, `docs/audit/*`
- ✅ Baseline: `.secrets.baseline` (требование pre-commit)

**Вывод:** Все файлы относятся к PR-508 (OpenAPI determinism).

### ✅ 5) Baseline на шум

```diff
- "line_number": 151
+ "line_number": 188
- "generated_at": "2026-01-10T00:02:24Z"
+ "generated_at": "2026-01-10T21:08:27Z"
```

**Вывод:** Минимальные изменения (только метаданные).

---

## 4) Анализ openapi-sync job

### Полный diff job'а

```yaml
openapi-sync:
  name: OpenAPI sync (backend -> frontend artifacts)
  runs-on: ubuntu-latest
  timeout-minutes: 10
  env:
    APP_ENV: test
    ENVIRONMENT: test
  steps:
    - name: Checkout
      uses: actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955

    - name: Setup Python environment
      uses: ./.github/actions/python-setup
      with:
        python-version: "3.13.6"
        install-dev-deps: "true"

    - name: Install backend dependencies
      run: |
        python -m pip install -r requirements.txt -c constraints.txt

    - name: Setup Node.js
      uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020
      with:
        node-version: "20"
        cache: "npm"
        cache-dependency-path: frontend/package-lock.json

    - name: Install frontend dependencies
      working-directory: frontend
      run: npm ci

    - name: Generate OpenAPI + TS types
      run: make openapi

    - name: Fail if generated artifacts differ
      run: git diff --exit-code frontend/src/api/openapi.json frontend/src/api/schema.ts
```

### Проверка на мины

✅ **Python version**: `3.13.6` (консистентно с другими jobs)
✅ **Node version**: `20` (консистентно с frontend-ci)
✅ **Cache**: `npm` cache настроен правильно
✅ **Order**: Python setup → Backend deps → Node setup → Frontend deps → Generate
✅ **Constraints**: Используется `-c constraints.txt` для детерминизма
✅ **Env vars**: `APP_ENV=test`, `ENVIRONMENT=test` (как в `scripts/generate_openapi.py`)

**Вывод:** Нет проблем с порядком шагов, кешем или версиями.

---

## 5) Готовый PR-комментарий

```
**CI fix:** `openapi-sync` job failed because backend dependencies were not installed before running `make openapi`, causing `ModuleNotFoundError: fastapi` when importing `app.main`.

Added an explicit backend deps install step (`pip install -r requirements.txt -c constraints.txt`) before OpenAPI generation. No dependency changes required.

**Note:** The `python-setup` action installs `requirements.txt` without `constraints.txt`, so this step ensures deterministic dependency resolution (required for OpenAPI schema generation).
```

---

## ✅ Итог

**Все проверки пройдены:**
1. ✅ Нет дублирования установки deps (наш шаг уточняет с constraints.txt)
2. ✅ `.secrets.baseline` стабилен (минимальные изменения)
3. ✅ Все мини-чеки пройдены
4. ✅ CI-изменения только по делу
5. ✅ Нет проблем с порядком шагов/кешем/версиями

**Готово к merge!** 🚀
