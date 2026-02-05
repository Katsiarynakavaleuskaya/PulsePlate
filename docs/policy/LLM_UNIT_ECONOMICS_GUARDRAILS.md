## LLM Unit Economics Guardrails (Hard Policy)

**Last updated:** 5 February 2026
**Scope:** Backend only (LLM endpoints, e.g. `/api/v1/insight`).
**Goal:** Guarantee **positive unit economics under worst-case usage**.

---

## English (Canonical)

### 1) Invariant

LLM is a **metered resource**, not a feature. Any LLM endpoint is **economically unsafe** until it has a
**hard cost cap** (quota/budget) per user/key.

### 2) Why VIP-only + rate limiting is insufficient

Rate limiting bounds request velocity, not the time-integrated cost. A VIP user can sustain max usage every day.
Therefore, cost is bounded per minute but **unbounded per month** without a quota/budget layer.

### 3) Hard requirement: quota / budget layer (P0 security)

#### 3.1 Hard cap definition

At minimum, enforce one of:

- **Requests/month** (simplest, coarse)
- **Tokens/month** (better)
- **Estimated cost USD/month** (best; requires cost estimation inputs)

#### 3.2 Enforcement semantics

When quota is exceeded:

- The server must **hard-stop** the LLM call (no provider request).
- The API must return a deterministic, non-leaky error response (e.g. `429`).

**Note:** VIP-only + rate limiting are necessary but not sufficient. Until a monthly hard quota is enforced,
LLM endpoints remain **economically unsafe** by this policy and must be tracked as an open P0 security item in
`docs/roadmap/BACKLOG_LEDGER.md`.

### 4) Budget formula (upper bound)

Define per-paying-user monthly LLM budget as an **upper bound**, not an average:

\[
LLM\_budget_{user/month}
\le
Price
\times (1 - AppleFee)
\times (1 - Tax)
\times MarginTarget
\]

Where:

- **Price**: subscription price
- **AppleFee**: 0.15 or 0.30 depending on program/status
- **Tax**: effective tax rate (use pessimistic estimate)
- **MarginTarget**: desired retained margin (profit + reserves)

Request/token quotas must be derived from this budget.

---

### 5) Minimal safe baseline (recommended)

To guarantee a cost ceiling:

1. VIP-only access (tier guard)
2. Rate limiting (abuse burst protection)
3. **Monthly hard quota** (cost ceiling)
4. Cost shaping: input length cap, `max_tokens` cap, “cheap default model”
5. Observability + kill-switch (rapid shutdown on anomaly)

---

### 6) Security note

Quotas are security controls (economic DoS prevention), not “optimizations”.

---

## Русская версия (Reference)

### 1) Инвариант

LLM — это **ресурс с учётом потребления**, а не “фича”. Любой LLM endpoint считается **экономически небезопасным**
до тех пор, пока не введён **жёсткий верхний предел затрат** (quota/budget) на пользователя/ключ.

### 2) Почему VIP-only + rate limit недостаточно

Rate limit ограничивает скорость запросов, но не ограничивает **накопленную стоимость за месяц**.
VIP пользователь (или атакующий с VIP ключом) может стабильно “съедать” лимит каждый день.
Без quota/budget слой затрат остаётся **неограниченным во времени**.

### 3) Требование (P0 security): quota / budget слой

Минимально необходимо enforce один из вариантов:

- **Requests/month** (самое простое)
- **Tokens/month** (лучше)
- **Estimated cost USD/month** (лучшее, требует оценки стоимости)

При превышении квоты:

- сервер **не делает** вызов провайдера (hard-stop),
- API возвращает детерминированную ошибку без утечек (например `429`).

**Примечание:** VIP-only + rate limiting необходимы, но недостаточны. Пока не введена monthly hard quota,
LLM endpoints остаются **экономически небезопасными** по этой политике и должны быть отражены как открытый
P0 security item в `docs/roadmap/BACKLOG_LEDGER.md`.

### 4) Формула бюджета (upper bound)

Бюджет LLM на платящего пользователя в месяц задаётся как upper bound:

\[
LLM\_budget_{user/month}
\le
Price
\times (1 - AppleFee)
\times (1 - Tax)
\times MarginTarget
\]

Квоты в запросах/токенах должны быть производными от этого бюджета.

### 5) Минимальный безопасный контур

1. VIP-only (tier guard)
2. Rate limiting (burst protection)
3. **Monthly hard quota** (ceiling)
4. Cost shaping (input cap, max_tokens, cheap default model)
5. Observability + kill-switch

### 6) Security note

Квоты — это security control (защита от “денежного DoS”), а не “оптимизация”.
