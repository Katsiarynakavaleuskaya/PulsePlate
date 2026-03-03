# ADR: Restaurant Partner Contract Temporary Seam (W3-R1)

**Status:** Accepted
**Date:** 2026-03-03
**Owner:** @katsiaryna_kavaleuskaya

## Context

Wave `W3-R1` introduces a contract-first `menu -> partner` API surface under `/api/v1/pro/restaurants/partner/*`.
To avoid DB migrations in this first contract wave, runtime storage is intentionally implemented with an
in-memory seam in `app/services/restaurant_partner_orders.py`.

This seam is temporary and must not become implicit long-term architecture.

## Decision

Use the in-memory seam only for `W3-R1` while locking:

1. Public API shape and status transitions.
2. Idempotency semantics (`client_event_id`) for create/confirm.
3. Fail-closed behavior for consent and invalid transitions.

## Exit Criteria (Mandatory)

1. Persistent storage replaces the in-memory seam with explicit audit/provenance model.
2. Contract tests cover all declared success/error paths and run deterministically in CI.
3. OpenAPI and generated frontend types stay synchronized with runtime behavior.
4. Backlog wave chain `W3-R2`/`W3-R3`/`W3-R4` is merged or explicitly re-planned with new DoD and blockers.

## Backlog Link (SoT)

- `docs/roadmap/BACKLOG_LEDGER.md`:
  - `P2: Execution Wave 3-R1 — Partner API contract freeze`
  - `P2: Execution Wave 3-R2 — Consent + signed handoff contract`
  - `P2: Execution Wave 3-R3 — Partner retrieval + confirmation hardening`
  - `P2: Execution Wave 3-R4 — Export adapter + deterministic contract tests`

## Consequences

- Positive: contract can be reviewed and integrated early without waiting on schema migrations.
- Negative: in-memory seam is not production-grade durability and must not be treated as final architecture.
