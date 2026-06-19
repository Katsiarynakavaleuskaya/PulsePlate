# SEC-001: Horizontal privilege escalation in Bayesian adherence endpoints

**Label**: security
**Priority**: critical
**Severity**: high
**Status**: implemented for auth-derived identity; follow-ups tracked
**Owner**: Backend
**Reported**: 2025-09-18
**Last reviewed**: 2026-06-19

## Summary

The Bayesian adherence endpoints accepted `user_id` from the request payload or query, allowing a
client with a valid API key to read or mutate another user's adherence state. This is a horizontal
privilege escalation risk because the identifier was trusted from untrusted input instead of the
authenticated context.

## Affected Endpoints

- `POST /api/v1/bayes/adherence/event`
- `GET /api/v1/bayes/adherence/risk`

## Impact

- Cross-user modification of Bayesian adherence state.
- Unauthorized access to adherence risk metrics for other users.
- Potential data leakage in analytics and user-facing risk scores.

## Implemented Work

- Bayesian adherence routes derive the effective subject from
  `Depends(get_current_user)`.
- Requests cannot use payload/query `user_id` as the effective subject.
- API-key state isolation is covered by deterministic tests.
- The API auth/tier/BOLA contract pack registers adherence routes as PRO,
  auth-derived-subject routes.
- Security posture documentation records the current contract evidence.

## Current Acceptance Criteria

- Requests cannot use supplied `user_id` in adherence payload or query
  parameters as the effective subject.
- `get_current_user` supplies the effective `user_id` for reads/writes.
- Different API keys yield isolated adherence state.
- Documentation records current posture and remaining follow-ups.

## Evidence

- `tests/test_bayes_adherence_api.py`
- `tests/security/test_api_auth_tier_contract_pack.py`
- `docs/security/SECURITY_POSTURE.md`

## Deferred Follow-ups

- First-class user-authentication mapping remains tracked in
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-first-class-auth-principal-mapping`.
- Operational alerting for suspicious cross-subject attempts remains part of the
  same follow-up and must not be represented as implemented runtime behavior
  until a dedicated PR lands it.
