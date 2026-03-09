# ADR: AI Runtime Bounded-Context Extraction Seam (2026-03-09)

- Status: Accepted (temporary seam)
- Owner: @katsiaryna_kavaleuskaya
- Related ledger item: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ai-bounded-context-extraction`

## Context

AI provider integration, safety controls, and insight/runtime behavior are
documented across several runtime areas. The target architecture is a clearer
bounded context, but the canonical package boundary is not implemented yet.

## Evidence

- Canonical API entrypoint remains split between bootstrap wiring in
  `app/main.py:11`-`app/main.py:26` and additive AI route registration in
  `app/main.py:83`-`app/main.py:87`.
- Import-safe compat and router-registration seams still live in
  `legacy_app.py:170`-`legacy_app.py:175` and
  `app/routers/pro_registration.py:26`-`app/routers/pro_registration.py:45`.
- Provider loading, transparency gating, and runtime orchestration for insights
  still flow through the legacy compatibility layer in
  `legacy_app.py:2225`-`legacy_app.py:2344`.
- Hard quota enforcement remains in `app/security/llm_monthly_quota.py:52`-`app/security/llm_monthly_quota.py:77`
  and `app/security/llm_monthly_quota.py:117`-`app/security/llm_monthly_quota.py:152`.
- Rate-limit guardrails remain in `app/security/rate_limit.py:48`-`app/security/rate_limit.py:76`
  and `app/security/rate_limit.py:173`-`app/security/rate_limit.py:205`.
- Public insight endpoints still enforce input guard + quota + rate limit in
  `legacy_app.py:2393`-`legacy_app.py:2441`.

## Decision

Keep the current runtime structure, but document AI bounded-context extraction
as an explicit temporary seam with a linked ledger item and removal criteria.

## Exit criteria

Retire this seam only when all are true:

1. A canonical AI runtime package structure exists and is documented.
2. Routers and client layers remain thin adapters around AI behavior.
3. Safety, evaluation, and provider ownership are mapped to that bounded
   context.
4. `AGENTS.md`, architecture docs, and quick-path docs no longer need
   transitional wording about future extraction.

## Consequences

- Positive: contributors get an auditable explanation for the current wording.
- Positive: the architecture target is explicit without pretending it already
  exists.
- Negative: AI runtime ownership remains distributed until the follow-up PR.
