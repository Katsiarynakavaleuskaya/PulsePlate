# PR-A: docs(contracts) — Define OpenAPI Visibility Rules and Audit Current Paths

**Type:** Docs-only (governance)
**Risk:** None (no runtime changes)
**Priority:** High (foundation for PR-B/PR-C)

---

## Purpose

Зафиксировать **канонические правила**, *что имеет право быть в OpenAPI*, а что нет, **до любых runtime-изменений**.

PR **не меняет поведение приложения**, не трогает код и не влияет на клиентов.

Это governance-PR: он снимает двусмысленность и служит базой для PR-B / PR-C.

---

## Scope

**Только документация:**

* `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md` — правила видимости эндпоинтов в OpenAPI
* `docs/contracts/OPENAPI_PATHS_AUDIT.md` — фактический инвентарь путей из текущего OpenAPI
* `docs/contracts/PRODUCT_TIER_MAP.md` — canonical tier mapping (FREE/PRO/VIP)
* `AGENTS.md` — добавлена секция "Product tiers and API namespaces"
* `docs/audit/API_ALIGNMENT_CHECKLIST.md` — обновлён под FREE/PRO/VIP модель

❌ **НЕТ:**
* runtime кода
* правок роутеров
* feature flags
* CI / infra

---

## Key Decisions (зафиксировано)

1. **Product tiers:** FREE / PRO / VIP — единственные уровни продукта
2. **`/premium/*` — deprecated namespace**, не tier
3. **OpenAPI = публичная витрина**, не отражение legacy/alias слоёв
4. Deprecated aliases, admin/debug/test/export **не должны быть видны в OpenAPI по умолчанию**
5. Canonical namespaces:
   * FREE → `/api/v1/bmi/*`
   * PRO → `/api/v1/pro/*`
   * VIP → `/api/v1/vip/*`

---

## Non-goals

* ❌ не скрывает `/premium/*` из OpenAPI (это PR-B)
* ❌ не исправляет `/premium/plan/week` (это PR-C)
* ❌ не переименовывает роуты
* ❌ не трогает frontend/iOS

---

## Verification (docs-only check)

```bash
git diff --name-only origin/main...HEAD \
  | rg -v "\.md$|README\.md$|AGENTS\.md$|RUNBOOK_AGENT\.md$|DEPLOYMENT\.md$"
```

**Ожидание:** пустой вывод → подтверждение, что PR строго docs-only.

---

## Why Now

Без этого PR:
* невозможно объективно сказать, **что считается регрессией**
* PR-B и PR-C будут спорить "по ощущениям", а не по правилам
* frontend/iOS продолжат генерить типы из мусорной схемы

---

## Follow-ups

* **PR-B:** schema hygiene — скрыть `/premium/*` из OpenAPI
* **PR-C:** VIP alignment — `/premium/plan/week` = alias → `/vip/menu/weekly/plan`
