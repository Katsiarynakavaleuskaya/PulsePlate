# PR4 Entitlement Routing Closeout Audit

**Date:** 2026-04-02
**Status:** post-open closeout evidence packet
**Scope:** backend authz truth only

## Summary

PR4 is the next real implementation PR in the monetization critical path.
It is a closeout lane for entitlement-backed routing after billing activation,
not a new billing/release/design wave.

Current sequencing baseline:
- PR1 Postgres foundation is already merged and stays out of PR4 scope.
- PR2 deploy shell lane materially landed via `#1293`; the CD env-token
  follow-up landed in `#1297`.
- PR3 activation + persistence truth merged as `#1296`; shadow runtime truth is
  no longer the active monetization narrative.
- After PR4, the sequence moves to web entitlement truth, legal/release shell,
  App Store/provider modernization, and only then the remaining AI waves.

## Scope In

- `app/middleware/api_tiers.py` as the single entitlement-truth seam for
  canonical `/api/v1/pro/*` and `/api/v1/vip/*`
- fail-closed routing semantics for `MISS`, `ERROR`, and `INVALID_TIER`
- production-like startup enforcement for DB-backed entitlement mode
- RU/BY manual billing carveout as transport-auth only
- canonical route-guard coverage and packet wording sync

## Scope Out

- web entitlement truth
- deploy shell work
- legal/release shell
- iOS / App Store / provider modernization
- broader auth-framework refactors
- WebSocket expansion beyond current secure foundation

## Evidence Snapshot

- DB-backed entitlement truth already fails closed in `app/middleware/api_tiers.py:249`,
  `app/middleware/api_tiers.py:257`, `app/middleware/api_tiers.py:296`, and
  `app/middleware/api_tiers.py:364`.
  Evidence:
  `app/middleware/api_tiers.py:249`,
  `app/middleware/api_tiers.py:257`,
  `app/middleware/api_tiers.py:296`,
  `app/middleware/api_tiers.py:364`.
  This means `ERROR` returns no env fallback, `MISS` stays denied,
  `INVALID_TIER` denies, and only `HIT` can unlock a protected paid route when
  `SUBSCRIPTION_DB_ENABLED=true`.
- Production-like startup already fails closed without DB-backed entitlement
  truth in `app/bootstrap/startup_guards.py:25`-`app/bootstrap/startup_guards.py:40`
  and is regression-covered in `tests/test_app_lifespan_additional.py:201`.
  Evidence:
  `app/bootstrap/startup_guards.py:25`,
  `tests/test_app_lifespan_additional.py:201`.
- RU/BY manual rails remain an explicit pre-entitlement transport-auth carveout,
  not an entitlement surface, in `app/routers/billing.py:128`,
  `app/routers/billing.py:197`, `app/routers/billing.py:242`, and
  `app/routers/billing.py:355`.
  Evidence:
  `app/routers/billing.py:128`,
  `app/routers/billing.py:197`,
  `app/routers/billing.py:242`,
  `app/routers/billing.py:355`.
- Canonical route-guard oracle remains
  `tests/test_pro_vip_route_dependency_guard.py:14` and
  `tests/test_pro_vip_route_dependency_guard.py:86`, including the
  pre-entitlement allowlist for manual-intent/reconcile routes.
  Evidence:
  `tests/test_pro_vip_route_dependency_guard.py:14`,
  `tests/test_pro_vip_route_dependency_guard.py:86`.
- Paid-route regression packet proves the carveout and entitlement transitions:
  pre-entitlement manual routes remain callable while canonical paid routes stay
  denied (`tests/test_paid_route_guards.py:316`), verified manual VIP unlocks
  PRO+VIP (`tests/test_paid_route_guards.py:347`), verified manual PRO unlocks
  only PRO (`tests/test_paid_route_guards.py:392`), and rejected manual
  reconcile stays denied (`tests/test_paid_route_guards.py:432`).
  Evidence:
  `tests/test_paid_route_guards.py:316`,
  `tests/test_paid_route_guards.py:347`,
  `tests/test_paid_route_guards.py:392`,
  `tests/test_paid_route_guards.py:432`.

## Narrative Rewrites for PR4 Packet

Do not use these stale phrasings in PR4 audit/review material:
- `PR3 pending`
- `deploy fix not applied`
- `websocket verifier not wired`

Use these instead:
- `PR3 merged as #1296 and shadow runtime truth removed`
- `deploy shell lane materially landed via #1293, with extra CD env-token follow-up in #1297`
- `websocket foundation is now wired enough to stop calling it stub-only, though it still is not the current release priority`

Narrative evidence:
- deploy shell lane materially landed:
  `docs/review/PR_1293_FIXED_MAPPING.md:49`
- CD env-token follow-up:
  `docs/review/PR_1297_FIXED_MAPPING.md:14`
- WebSocket foundation is a landed secure baseline rather than a stub-only
  placeholder: `docs/roadmap/BACKLOG_LEDGER.md:5488`

## Required PR4 Review Path

PR4 keeps the canonical post-open reviewer lane:
- open the PR first
- then run `qa-engineer-agent -> bug-hunter`
- only after that start the review/bot disposition loop

Evidence:
- `docs/runbooks/PR_CANONICAL_MATRIX_CHECKLIST.md:25`
- `docs/orchestration/workflow.md:134`

## Verification Baseline

The targeted closeout packet is green on the pre-open branch baseline:

```bash
pytest -q tests/test_paid_route_guards.py
pytest -q tests/test_pro_vip_route_dependency_guard.py
pytest -q tests/test_api_tiers.py
pytest -q tests/test_app_lifespan_additional.py
```

PR4 still requires the full pre-claim gates before any readiness statement:

```bash
pre-commit run --all-files
make verify
```

## Security Notes

- Persisted backend entitlement state remains the only authority for paid route
  unlock.
- `SUBSCRIPTION_DB_ENABLED=true` in production-like environments is a hard
  fail-closed contract, not an advisory posture.
- RU/BY manual rails remain explicit pre-entitlement transport surfaces and must
  not drift into authz bypass behavior.

## Decision

PR4 should proceed as a narrow authz closeout packet.
If a later PR needs web truth, release shell, or App Store/provider follow-through,
that work belongs to the next lanes after PR4 rather than being widened into this packet.
