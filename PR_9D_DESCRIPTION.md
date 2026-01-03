# PR-9d: Engineering lessons (PR-8b) + repo policy guard (forbid sys.modules mutations in tests)

## Summary

Этот PR фиксирует инженерные уроки из **PR-8b** как проектную память и добавляет **repo-policy guard**, запрещающий мутации `sys.modules` в тестах — чтобы больше не ловить *dual-module state*, флейки и "patch не туда".

---

## Scope (what's included)

### ✅ Docs

* `docs/ENGINEERING_LESSONS.md` — консолидированные уроки PR-8b (test determinism, diff-coverage, portability, error contracts)
* `AGENTS.md` — ссылка на документ как canonical source

### ✅ Repo policy guard

* `tests/test_repo_policy_sys_modules.py` — падает, если в `tests/**` есть:

  * `del sys.modules[...]`
  * `sys.modules[...] = ...`
* Краткая памятка в `tests/AGENTS.md` о запрете и команде проверки

### ✅ Test helper for deterministic endpoint patching

* `tests/_route_patch.py` — helper для детерминированного патчинга FastAPI endpoints
* `tests/test_route_patch_helper.py` — тесты для helper
* Решает проблему, когда `patch("app.routers.vip.get_available_regions", None)` не попадал в реально зарегистрированный handler

---

## Non-goals (explicitly out of scope)

* Никаких изменений бизнес-логики (VIP/PDF/weekly plan)
* Никаких CI/infra правок
* Никаких изменений публичных API контрактов
* Никаких "исключений через allowlist" (на старте)

---

## Why this PR

### 1) `sys.modules` mutations — это не "спорно", а **критический источник nondeterminism**

* создаёт dual-module state
* ломает `patch()`/`monkeypatch`
* вызывает импорт-зависимые баги и флейки

### 2) Уроки из PR-8b — это знания, которые должны жить в репо

Не "в голове", не "в чате", а в виде документа и guards.

### 3) Motivation example (real CI flake)

`patch("app.routers.vip.get_available_regions", None)` sometimes didn't affect the actually registered `/api/v1/vip/regions` handler in large test runs, producing **success instead of error**.
We fixed it by patching the real endpoint from `app.routes` (path+method) and using `monkeypatch` on `endpoint.__globals__` — policy-compliant and deterministic.

---

## Review order (recommended)

1. `docs/ENGINEERING_LESSONS.md`
2. `AGENTS.md` (link)
3. `tests/test_repo_policy_sys_modules.py`
4. `tests/_route_patch.py` + `tests/test_route_patch_helper.py`

---

## How to test

```bash
pytest -q tests/test_repo_policy_sys_modules.py
pytest -q tests/test_route_patch_helper.py
pytest -q
```

---

## Expected failure example

Если в `tests/**` появится мутация `sys.modules`, тест упадёт с **чётким и локализованным сообщением**:

```text
AssertionError: Repo policy violation: sys.modules mutations detected in tests.

- tests/vip/test_regions_error_paths.py
  L42: Forbidden: `del sys.modules[...]` in tests.

Fix:
- Use `patch()` / `monkeypatch.setattr()` instead of sys.modules edits.
- If you need re-import behavior, refactor code to inject dependencies.
- For FastAPI endpoints, use `tests/_route_patch.patch_route_dependency()`.
```

### What this means

* Тест **не зависит от порядка импортов**
* Сообщение указывает **точный файл и строки**
* Подсказка сразу ведёт к корректному решению (patch / monkeypatch / route helper)

### Why this is intentional

This guard exists to prevent:

* dual-module state
* silent patch failures
* nondeterministic tests that "pass locally but fail in CI"

---

## Risks & mitigations

### Risk: ложноположительные срабатывания regex

* Mitigation: правила минимальные (2 конкретных паттерна), сообщение об ошибке указывает файл/строки.

### Risk: кому-то "нужно" удалять `sys.modules` для test isolation

* Mitigation: правильный путь — `patch()`/`monkeypatch` или refactor на dependency injection. Dual-module state не допускаем.

---

## Notes

* Документ "Engineering Lessons" — derived from PR-8b и считается проектным эталоном.
* Этот PR сознательно вынесен отдельно, чтобы **PR-10 Weekly Plan Hardening** остался чистым и узким по scope.

---

## Related

* PR-8b: VIP Shoplist PDF export (source of lessons)
* PR-10: Weekly Plan Hardening (will benefit from this policy guard)

