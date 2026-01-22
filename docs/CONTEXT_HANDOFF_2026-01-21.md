# 🧾 PulsePlate — CONTEXT HANDOFF (после merge PR-560 + PR-561)

**Дата фиксации:** 2026-01-21
**Ветка/статус:** `main` актуален, PR-560 и PR-561 **смерджены**
**Правило процесса:** всегда **Audit (Qoder) → Implementation (Cursor) → DoD/CI**

---

## 0) Канонические принципы (не обсуждаем, соблюдаем)

1. **Thin clients only** (iOS/Web): **0** BMI/нутри-логики на клиенте. Только контракт, UX, локализация, ретраи, ошибки.
2. **Backend first / determinism first**: downstream меняем только когда upstream стабилен.
3. **Документация как контракт**: изменения в процессах/политиках → обновлять **AGENTS.md** и при необходимости **RUNBOOK_AGENT.md**.
4. **Security suppressions**: отдельные PR, 1 CVE per PR, с `docs/security/CVE-*.md`, expiry + monitor.

---

## 1) Что закрыто и смёржено (факты)

### PR-560 — CI iOS stability (merged)

**Что вошло:**

* Исправления iOS CI стабилизации (bootstatus timeout **60s → 180s**, параметризовано env `SIM_BOOT_TIMEOUT_SECONDS`)
* `docs/roadmap/BACKLOG_LEDGER.md`: статус и DoD чекбоксы выровнены под "awaiting merge / in progress" до мержа
* `ios/AGENTS.md`: приведён к **split build/test flow** (`build-for-testing` → `test-without-building`), убрана/правится дублирующая секция (если осталась — чистить отдельным коммитом, но PR уже merged)
* Swift 6 actor isolation ошибки устранены (ошибки типа "Main actor-isolated…")

**Заметка:** часть "debug procedures" лучше держать в `RUNBOOK_AGENT.md`, а в `AGENTS.md` — только инварианты/правила.

### PR-561 — Trivy suppression (CVE-2025-15281 glibc) (merged)

**Что вошло:**

* `trivy/ignore-policy.rego`: исправлен Rego parse error (helper rules вместо inline `or`)
* Suppression с **узким allowlist**:
  * пакеты: `libc6`, `libc-bin`
  * версии: **deb12u10** и **deb12u13** (runner drift)
  * PkgID: все 4 комбинации (libc6/libc-bin × u10/u13)
* Expiry policy checker проходит: **ровно 1** строка `Suppression expires:` в файле, остальное через `Review-by:`
* `docs/security/CVE-2025-15281-glibc.md`: severity уточнена до **Minor (per Debian Security Tracker)** + monitor/expiry

---

## 2) Канонические документы/карта (куда смотреть)

**Обязательные "канон" доки проекта:**

* `docs/BMI_CANONICAL_HANDOFF.md` (One BMI Engine, anti-dup guards, child ≠ teen, downstream freeze правила)
* `docs/audit/ROOT_CAUSE_ANALYSIS_BMI_UNDEFINED.md`, `docs/audit/DECISION_LOG_BMI_UNDEFINED.md`
* `docs/audit/BACKEND_P0_REMEDIATION_PLAN.md`, `docs/audit/BACKEND_P0_GUARD_POLICY_PROPOSAL.md`
* `docs/roadmap/BACKLOG_LEDGER.md` (postponed items обязаны фиксироваться)
* `docs/security/*` (CVE suppressions с expiry/monitor)
* `AGENTS.md` + `ios/AGENTS.md` + `frontend/AGENTS.md` + `RUNBOOK_AGENT.md`

---

# Следующий PR (старт нового окна): Thin HTTP Adapter для iOS + Web

## Цель

Сделать **единую тонкую транспортную прослойку** (HTTP adapter) для клиентов:

* **iOS (Swift)**: `APIClient`/`BMIService`/`HTTPClient` без бизнес-логики
* **Web (TS)**: такой же thin adapter (fetch/httpx-like wrapper), типы из OpenAPI
* Клиенты должны уметь: baseURL, headers, JSON encode/decode, error envelope, timeouts/retry (минимально), telemetry hooks (опционально), i18n ошибок.

## Принципиально: что НЕ делаем в этом PR

* Никаких формул BMI/waist/рисков на клиенте
* Никаких "интерпретаций"/категорий на клиенте
* Никаких "схем расчётов" в UI — только отображение ответа API

---

## План PR: Audit → Implementation

## A) AUDIT (в начале нового окна, до кода)

**Нужно собрать фактами:**

1. **Канонические endpoints** (что клиент зовёт реально):
   * Public BMI calculate (точный путь + request/response модель)
   * (если уже есть) soft paywall hook контракт и поля (но UI не делаем)

2. **Error envelope**: как backend отдаёт ошибки (422/400/5xx) и формат payload

3. **Auth**: публичные запросы без ключа vs Pro/VIP (какие headers)

4. **i18n**: какие ключи приходят с backend и что локализуем на клиенте

**Выход аудита:**

* `docs/audit/PR_XXX_THIN_CLIENT_HTTP_ADAPTER_AUDIT.md`:
  * endpoints table
  * request/response samples (curl + JSON)
  * error payload examples
  * contract invariants (no client logic)

## B) IMPLEMENTATION (Cursor)

### iOS

* `ios/PulsePlate/Networking/HTTPClient.swift` (URLSession wrapper)
* `ios/PulsePlate/Networking/APIClient.swift` (baseURL from Info.plist, headers, JSON)
* `ios/PulsePlate/Services/BMIService.swift` (only calls endpoint, returns DTO)
* `ios/PulsePlate/Models/*DTO.swift` (request/response DTOs strictly aligned)

**Тесты:**

* URLProtocol stub tests (у вас уже есть паттерн `FailingURLProtocol`)
* decode/encode snapshot-like tests (no UI)

### Web (Vite/TS)

* `frontend/src/api/http.ts` (thin fetch wrapper)
* `frontend/src/api/bmi.ts` (function `calculateBMI(req): Promise<BMIResponseDTO>`)
* типы: либо `openapi-typescript`, либо ручной DTO (лучше автоген)
* error mapping: 422 validation errors → UI-friendly message keys

---

## DoD для PR (жёстко)

* [ ] iOS: unit tests green (encoding/decoding + request building + error mapping)
* [ ] Web: unit tests/tsc build green (минимум)
* [ ] No business logic on client (grep policy / review checklist)
* [ ] Документация обновлена:
  * `ios/AGENTS.md`: правила для thin adapter (где нельзя логика)
  * `frontend/AGENTS.md`: правила для thin adapter (где нельзя логика)
  * `AGENTS.md`: общий принцип thin clients (если ещё не закреплён)
  * если добавим debug steps — в `RUNBOOK_AGENT.md`, не в AGENTS

---

## Что нужно обновить в AGENTS.md (обязательно)

Добавить/уточнить правила:

1. **Client logic ban:** никакой BMI/waist/рисковой логики в iOS/Web — только отображение данных API.
2. **Contract-first:** любые изменения DTO → сначала обновить OpenAPI/contract docs, потом код.
3. **Error envelope canonical mapping:** клиент не "угадывает", а следует контракту.

---

## Ссылки на связанные документы

* `docs/BMI_CANONICAL_HANDOFF.md` — One BMI Engine invariant
* `ios/AGENTS.md` — iOS Thin Client Policy (уже есть)
* `frontend/AGENTS.md` — Frontend conventions
* `docs/contracts/soft_paywall.md` — Soft paywall hook contract
* `docs/roadmap/BACKLOG_LEDGER.md` — Postponed items

---

**Last updated:** 2026-01-21
**Maintainer:** @katsiaryna_kavaleuskaya
