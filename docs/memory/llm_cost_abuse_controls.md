# Memory Capsule: LLM cost‑abuse controls (rate limit + quota + budgets)

**Topic:** Protecting expensive AI endpoints from abuse
**Type:** Hard rules + enforcement pointers
**Last updated:** 8 February 2026

---

## What

PulsePlate treats LLM endpoints as **abuse-prone** and enforces:

- **rate limiting** (deterministic 429 tests)
- **monthly hard quota** (enforced before provider calls)
- **feature-flag gating before charging/quota consumption**

Recursive/multi-agent pipelines amplify calls, so **budgets/stop conditions** are required in future runtime work.

---

## Why

Without hard controls, a single endpoint can become a predictable cost sink / DoS vector.

---

## Invariants (SoT)

- Rate limiting hard rule + enforcement list: `AGENTS.md:65`–`AGENTS.md:79`
- Monthly quota hard rule + gating order: `AGENTS.md:81`–`AGENTS.md:87`
- Feature flags checked before quota consumption: `AGENTS.md:86`

---

## Commands (verification)

- Verify repo policy guards (fast signal):

```bash
pytest -q tests/test_repo_policy_guards.py
```

- Rate limiting tests (deterministic 200 → 429 transitions):

```bash
pytest -q tests/test_rate_limit_llm_and_exports_api.py
pytest -q tests/test_rate_limit_client_key_api.py
```

- Full local gate (when preparing merge):

```bash
make verify
```

---

## Links (canonical)

- Policy + references: `AGENTS.md` → “Rate Limiting Policy” and “LLM Monthly Quota Policy”
- Related audit: `docs/audit/PR_628_RATE_LIMIT_LLM_EXPORTS_AUDIT.md`
