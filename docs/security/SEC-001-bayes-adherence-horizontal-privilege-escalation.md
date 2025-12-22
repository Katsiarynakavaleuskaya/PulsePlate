# SEC-001: Horizontal privilege escalation in Bayesian adherence endpoints

**Label**: security
**Priority**: critical
**Severity**: high
**Status**: in progress
**Owner**: Backend
**Reported**: 2025-09-18
**Target remediation**: 2025-10-15

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

## Required Work

- Replace `user_id` in payload/query with `Depends(get_current_user)` to derive identity from auth.
- Remove `user_id` from request schema and forbid extra fields.
- Add per-API-key rate limiting for adherence endpoints.
- Enforce stricter input validation/whitelisting on request payload and analyzer key.
- Add logging and alerting for suspicious cross-user attempts.
- Update tests, threat model, and security posture documentation.

## Acceptance Criteria

- Requests cannot supply `user_id` in adherence payload or query parameters.
- `get_current_user` supplies the effective `user_id` for reads/writes.
- Sending `user_id` in the payload returns HTTP 422.
- Different API keys yield isolated adherence state.
- Rate limiting, input whitelisting, and alerting controls are documented and implemented.
- Documentation records current posture and remediation timeline.

## Mitigation Plan (Interim)

- Enforce per-API-key rate limiting for adherence endpoints.
- Forbid extra request fields and whitelist allowed payload keys.
- Log and alert on suspicious cross-user attempts or unexpected identifiers.

## Remediation Timeline

- Identity derivation from auth context: next release (target 2025-09-20).
- Interim controls (rate limiting, logging/alerting): by 2025-10-15.
- Full user authentication mapping: planned follow-up after interim controls.
