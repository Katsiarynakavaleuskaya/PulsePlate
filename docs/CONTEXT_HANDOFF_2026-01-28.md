# CONTEXT HANDOFF — PulsePlate

**Дата:** 2026-01-28
**Основание:** Merge PR-616
**Merge SHA:** `51376fe88dd816977580532085c42c238bd6aa9d`

---

## 0) Текущий статус проекта (зафиксировано)

* **PR-616 (TP1) — MERGED ✅**

  * Ветка `chore/p1-thin-proxy-cleanup-helpers-1` удалена
  * `main` в корректном состоянии
  * Guards / CI / diff-coverage — зелёные
  * Запрещённые паттерны устранены (`builtins.__import__`, прямые `sys.modules` мутации)
  * BACKLOG_LEDGER синхронизирован

* **Инварианты проекта восстановлены**

  * `legacy_app.py` → **thin proxy only**
  * Helpers вынесены в канонические модули
  * Resolver-логика защищена (`callable()` checks)
  * Тесты детерминированы и xdist-safe

---

## 1) Что именно закрыл PR-616 (TP1 scope)

### Архитектура

* Вынесены helpers из `legacy_app.py`:

  * feature flags
  * nutrition wrappers
  * scheduler helpers
  * fingerprint logic
* Восстановлен принцип **"thin proxy only"**

### Качество и тесты

* Закрыты все ветки резолвера (`_resolve_nutrition_callable`)
* Добавлены таргетные coverage-тесты
* Устранены:

  * direct `sys.modules[...] = / del`
  * patching `builtins.__import__`
  * env-leak (`FEATURE_PREMIUM_NUTRITION`)
* Coverage ≥ 97%, guards enforced

### Документация

* BACKLOG_LEDGER приведён к **однозначным статусам**
* TP1 → `Merged`
* TP2 → `Ready to start (TP1 merged)`

---

## 2) Что **НЕ** делали намеренно (важно)

❌ **НЕ входило в TP1** (и не должно смешиваться):

* DB fallback helpers
* Любые изменения поведения БД / соединений
* Новый runtime-код вне helpers
* Рефактор "ради красоты" (DRY seams — отложено)

Это **осознанно отложено** в TP2.

---

## 3) Канонический следующий шаг — PR-TP2

### PR-TP2: Thin-proxy cleanup (DB fallback)

**Статус:** 📋 Ready to start
**Приоритет:** P0
**Тип:** High-risk refactor (audit-first)

### Цель TP2

* Вынести DB fallback helpers из `legacy_app.py`
* Создать канонический модуль:

  * `core/db/fallback.py` **или**
  * `app/utils/db_fallback.py` (решается на аудите)
* Оставить `legacy_app.py` строго thin-proxy

### Обязательные ограничения TP2

* **Audit-first** (никакого кода до аудита)
* Поведение fallback **не меняем**
* OpenAPI **не меняем**
* Guards должны остаться зелёными
* Coverage ≥ текущего уровня

---

## 4) Как мы начинаем PR-TP2 (строгий процесс)

### Шаг 1 — Audit (docs only)

Создаём:

* `docs/audit/PR_TP2_DB_FALLBACK_AUDIT.md`

В аудите:

* Где сейчас DB fallback логика
* Какие функции/пути
* Какие риски (side-effects, import order, env-зависимости)
* Что **точно нельзя сломать**

### Шаг 2 — Plan

Создаём:

* `docs/pr/PR_TP2_DB_FALLBACK_PLAN.md`

В плане:

* Целевая структура
* Migration steps
* Test strategy
* Explicit out-of-scope

### Шаг 3 — Только потом код

---

## 5) Follow-ups (НЕ часть TP2, зафиксировано)

Записано как **отдельные возможные PR** (P1/P2):

* DRY-рефактор import seams в `nutrition_wrappers.py`
  *(опционально, если реально потребуется)*
* Ужесточение isolation теста `unknown-name` через `_get_candidate_modules` mock
  *(только если появятся флапы)*

**Важно:** эти пункты **не смешиваются** с TP2.

---

## 6) Правила (считаем каноном)

1. PR-616 закрыт и смержен
2. `legacy_app.py` — thin proxy only
3. Следующий трек — **PR-TP2 audit-first**
4. Любой код → только после аудита и плана
5. Любые новые задачи → фиксируются в BACKLOG_LEDGER

---

## 7) Ссылки на ключевые документы

* **BACKLOG_LEDGER:** `docs/roadmap/BACKLOG_LEDGER.md` (PR-TP2 entry)
* **TP1 Audit:** `docs/audit/PR_THIN_PROXY_CLEANUP_AUDIT.md`
* **TP1 Plan:** `docs/pr/PR_THIN_PROXY_CLEANUP_PLAN.md`
* **AGENTS.md:** Root-level rules and invariants
* **RUNBOOK_AGENT.md:** CI/debug procedures

---

**Готовность:** ✅ Контекст зафиксирован, готов к работе над PR-TP2
