# PR-595 — iOS Thin HTTP Adapter Audit

**Date:** 2026-01-26
**Target branch:** `main`
**Source branch:** `docs/pr-595-ios-thin-http-adapter-audit`
**Author:** @katsiaryna_kavaleuskaya
**Status:** 🟡 **Audit draft** (evidence pending)

---

## A. Scope (факты)

### Q1. Какая цель аудита?

Зафиксировать **фактическое состояние iOS networking слоя**, выявить:
- **dual-path HTTP** (прямые вызовы vs `APIClient`)
- legacy сервисы / “локальные клиенты”
- DTO/contract drift (ручные модели, рассинхрон с backend schema)

и подготовить **детерминированный remediation план** для перехода на **one thin HTTP adapter (`APIClient`)**.

### Q2. Что в scope / out of scope?

**In-scope (только факты transport/contract/wiring):**
- Где выполняются HTTP запросы (entry points)
- Как формируются `URLRequest`, где лежит base URL, заголовки, креды
- Какие сервисы/клиенты владеют сетевыми вызовами
- Какие DTO используются на границе сети (request/response/error envelopes)
- Где и как тестируется networking слой (URLProtocol stubs и т.п.)

**Out-of-scope (жёстко):**
- Backend изменения
- UI/UX / ViewModel архитектура (кроме факта: “делает ли ViewModel HTTP напрямую”)
- Любые вычисления/интерпретации (BMI/категории/решения) — только фиксация нарушений thin-client policy

### Q3. Канонические инварианты (re-statement)

- **One HTTP Path (iOS):** один транспортный слой как SoT
- **Thin client:** iOS не интерпретирует данные и не делает бизнес-решений (не считает BMI/risks и т.п.)
- **`APIClient`:** единственная точка HTTP (никакого `URLSession` снаружи)

---

## B. Инвентаризация: текущие HTTP пути (AS-IS)

> Ниже — команды для сбора фактов. В этот PR **не добавляем решения** — только наблюдения.

### Q4. Где выполняются сетевые запросы?

```bash
# Все прямые URLSession / dataTask
rg "URLSession|dataTask|uploadTask|downloadTask" ios/

# Любые URLRequest / HTTPURLResponse
rg "URLRequest|HTTPURLResponse" ios/

# Alamofire / сторонние клиенты (если есть)
rg "Alamofire|AF\." ios/
```

### Q5. Где используется `APIClient`?

```bash
rg "APIClient" ios/
```

### Q6. Где потенциальные legacy сервисы / адаптеры?

```bash
# Типичные legacy паттерны
rg "Service$|Client$|Networking|NetworkService" ios/

# Известные legacy из backlog (если присутствуют)
rg "LegacyBMIServicing|DefaultBMIService|BMIServiceError" ios/
```

### Q7. Где возможный DTO/contract drift (ручные модели)?

```bash
# Старые BMI модели / naming drift
rg "BMIRequest|BMIResponse|BMICalculate" ios/

# Новые канонические DTO (если уже заведены)
rg "BMICalculateRequest|BMICalculateResult" ios/
```

---

## C. Факты (заполняется по результатам `rg`)

> ⚠️ В этом разделе — только наблюдения: `path + line + what`. **Без “как надо”**.

### Q8. Обнаруженные HTTP entry points (таблица)

| File | Line | Type | Evidence | Notes |
|------|------|------|----------|-------|
| … | … | `URLSession` | `URLSession.shared...` | direct HTTP call |
| … | … | `APIClient` | `apiClient.request(...)` | OK |

### Q9. Dual-path networking: какие нарушения “One HTTP Path”?

**Violations (examples; replace with facts):**
- `ViewModel → URLSession` ❌
- `Service → URLSession` ❌
- `Service → APIClient` ✅

### Q10. Third-party HTTP clients (если есть)

| Library | File(s) | Notes |
|---------|---------|------|
| … | … | … |

### Q11. DTO/contract drift (если есть)

| Area | AS-IS DTO | Canonical backend DTO | Impact |
|------|-----------|-----------------------|--------|
| BMI | `BMIResponse` | `BMICalculateResult` | drift / mapping risk |
| … | … | … | … |

### Q12. Error handling: какие error-типы и где живут?

| Error Type | File | Usage |
|------------|------|-------|
| `BMIServiceError` | … | mapping/network layer |
| … | … | … |

---

## D. Таблица миграции: AS-IS → TO-BE (контрактно)

> Здесь фиксируем “что есть” vs “что будет” на уровне **архитектуры**, без кода в этом PR.

| Area | AS-IS | TO-BE |
|------|------|-------|
| HTTP transport | `URLSession` + `APIClient` | **`APIClient` only** |
| Direct networking in VM | possible | **forbidden** |
| Legacy services | `*Service` with own HTTP | ❌ removed / migrated |
| DTO | `BMIRequest`/`BMIResponse` | **canonical DTO aligned with backend** |
| Error handling | scattered (`*ServiceError`) | **shared `APIError`/canonical error envelope** |
| Test doubles | ad-hoc mocks | **URLProtocol / APIClient stubs (single seam)** |
| Entry point | scattered | **single `APIClient`** |

---

## E. Remediation plan (следующий PR-596; НЕ в этом PR)

> ⚠️ Этот PR = audit-only. Remediation делаем отдельным PR.

1. Удалить / изолировать legacy HTTP сервисы и прямые `URLSession` entry points
2. Перевести все сетевые вызовы на `APIClient` (единственный транспорт)
3. Выровнять DTO на канонические backend контракты (без ручного drift)
4. Обновить тесты (единая стратегия: URLProtocol/stubs на уровне `APIClient`)
5. Закрыть долги через `docs/roadmap/BACKLOG_LEDGER.md` (если что-то откладываем)

---

## F. DoD / Merge gates

### PR-595 (Audit PR) — Definition of Done

- [ ] Все HTTP пути перечислены: `file:line:evidence`
- [ ] Dual-path задокументирован (список нарушений + таблица entry points)
- [ ] DTO/contract drift зафиксирован (если присутствует)
- [ ] AS-IS → TO-BE таблица заполнена фактами
- [ ] План remediation для PR-596 описан (high-level, без кода)
- [ ] PR остаётся **docs-only** (только `*.md`)

### PR-596 (Remediation PR) — Definition of Done (для следующего шага)

- [ ] **Один HTTP слой (`APIClient`)**
- [ ] Нет `URLSession` / прямых сетевых вызовов вне `APIClient`
- [ ] DTO на границе сети = backend canonical (или адаптация строго в transport layer)
- [ ] Тесты green (локально + CI)
- [ ] Новые timeless-правила — только при необходимости в `AGENTS.md`
- [ ] Любые deferred items записаны в `docs/roadmap/BACKLOG_LEDGER.md`

---

## G. Links (заполнить)

- **Policy anchor:** `ios/AGENTS.md` (Thin Client + One HTTP Path)
- **Backlog ledger:** `docs/roadmap/BACKLOG_LEDGER.md` (item TBD)
- **Related audits:** (если есть) `docs/audit/PR_559_IOS_*`, `docs/audit/PR_560_*`

---

**Last updated:** 2026-01-26
**Maintainer:** @katsiaryna_kavaleuskaya
