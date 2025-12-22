# Security Posture Notes

## Bayesian Adherence Endpoints

- Current posture: user identity is derived from the authenticated API key via `get_current_user`,
  and request payloads forbid `user_id` to prevent horizontal privilege escalation.
- Planned remediation timeline (SEC-001): implement per-API-key rate limiting, logging/alerting,
  and full user authentication mapping by 2025-10-15.
