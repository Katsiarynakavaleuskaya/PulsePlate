## LLM Unit Economics Guardrails (Hard Policy)

**Last updated:** 5 February 2026  
**Scope:** Backend only (LLM endpoints, e.g. `/api/v1/insight`).  
**Goal:** Guarantee **positive unit economics under worst-case usage**.

---

## 1) Core statement (invariant)

**RU:** LLM — это не “фича”, а **metered resource**. Любой LLM endpoint считается **небезопасным**
до тех пор, пока не введён **жёсткий верхний предел затрат** (quota/budget) на пользователя/ключ.

**EN:** LLM is a **metered resource**, not a feature. Any LLM endpoint is **economically unsafe**
until it has a **hard cost cap** (quota/budget) per user/key.

---

## 2) Why VIP-only + rate-limit is insufficient

**RU:** Rate limit ограничивает **скорость**, но не ограничивает **интеграл затрат по времени**.
VIP пользователь (или атакующий с VIP ключом) может стабильно “съедать” лимит каждый день.
Следовательно, cost bounded per minute, но **unbounded per month**.

**EN:** Rate limiting bounds request velocity, not the time-integrated cost. A VIP user can sustain max usage
every day. Therefore, cost is bounded per minute but **unbounded per month**.

---

## 3) Hard requirement: quota / budget layer (P0 security)

### 3.1 Hard cap definition

At minimum, enforce one of:

- **Requests/month** (simplest, coarse)
- **Tokens/month** (better)
- **Estimated cost USD/month** (best; requires cost estimation inputs)

### 3.2 Enforcement semantics

When quota is exceeded:

- The server must **hard-stop** the LLM call (no provider request).
- The API must return a deterministic, non-leaky error response (e.g. `429`).

---

## 4) Budget formula (upper bound)

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

**RU:** Квота в запросах/токенах должна быть производной от этого бюджета.  
**EN:** Request/token quotas must be derived from this budget.

---

## 5) Minimal safe baseline (recommended)

To guarantee a cost ceiling:

1. VIP-only access (tier guard)
2. Rate limiting (abuse burst protection)
3. **Monthly hard quota** (cost ceiling)
4. Cost shaping: input length cap, `max_tokens` cap, “cheap default model”
5. Observability + kill-switch (rapid shutdown on anomaly)

---

## 6) Security notes

**RU:** Quotas are security controls (economic DoS prevention), not “optimizations”.  
**EN:** Quotas are security controls (economic DoS prevention), not “optimizations”.

