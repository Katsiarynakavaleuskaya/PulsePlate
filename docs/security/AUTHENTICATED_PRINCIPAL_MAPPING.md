# Authenticated Principal Mapping Contract

## Purpose

This document records the current PulsePlate authenticated-principal mapping
contract. It does not add a new auth model, does not complete full BOLA, does
not implement runtime alerting, and does not promote API-key-derived subjects
into first-class user authentication.

The current runtime contract is:

```text
credential or transport auth -> principal source -> ownership policy -> route/object expectation
```

## Current Mapping

| Surface | Current code source | Principal source | Ownership policy |
| --- | --- | --- | --- |
| PRO/VIP header or cookie tier context | `app/middleware/api_tiers.py:95` (`TierAuthContext`), `app/middleware/api_tiers.py:471` (`resolve_pro_auth_context`) | `CREDENTIAL_DERIVED_SUBJECT` | `AUTHENTICATED_SUBJECT` |
| API-key-derived subject | `app/middleware/api_tiers.py:735` (`derive_subject_id_from_api_key`), `app/middleware/api_tiers.py:766` (`CurrentUser`), `app/middleware/api_tiers.py:779` (`get_current_user`) | `CREDENTIAL_DERIVED_SUBJECT` | `AUTHENTICATED_SUBJECT` |
| Manual RU/BY billing transport | `app/routers/billing.py:165` (`_validate_billing_transport_key`), `app/routers/billing.py:280` (`_get_effective_manual_billing_key_validator`), `app/services/payments_activation.py:1238` (`issuer_from_api_key`) | `BILLING_ISSUER` | `ISSUER_SCOPED` |
| Feedback credential | `app/routers/feedback.py:83` (`get_feedback_user`) | `CREDENTIAL_DERIVED_SUBJECT` | `AUTHENTICATED_SUBJECT` |
| Bayesian adherence | `app/routers/bayes_adherence.py:52` and `app/routers/bayes_adherence.py:97` (`Depends(get_current_user)`) | `CREDENTIAL_DERIVED_SUBJECT` | `AUTHENTICATED_SUBJECT` |
| Legacy paid aliases | `tests/security/_api_authz_contracts.py:236` and `tests/security/_api_authz_contracts.py:297` | `CREDENTIAL_DERIVED_SUBJECT` | Must not be weaker than canonical paid routes |

The security classification source of truth remains
`tests/security/_api_authz_contracts.py:60` (`PrincipalSource`) and
`tests/security/_api_authz_contracts.py:71` (`OwnershipPolicy`). The PRO/VIP
subject tuple is defined at `tests/security/_api_authz_contracts.py:130`, and
the billing route contract starts at `tests/security/_api_authz_contracts.py:153`.

## Boundaries

The API-key-derived subject is a deterministic, positive, bigint-compatible
runtime identifier used for isolation. It is not a database `users.id`, not a
human-authenticated account, and not a replacement for the deferred first-class
user-authentication mapping.

Manual RU/BY billing routes are pre-entitlement transport-auth surfaces. A valid
transport key can create or reconcile a billing intent, but it does not unlock
PRO/VIP paid routes unless the backend later persists a valid active
entitlement. Manual billing access remains issuer-scoped through the resolved
issuer marker and payment activation audit owner.

Payload fields such as `user_id`, `subject_id`, issuer hints, or object IDs are
never principal truth by themselves. Object-level authorization must compare the
requested object against the authenticated principal source and ownership
policy for that route.

## Existing Evidence

- The auth/tier/BOLA contract pack registers sensitive routes with auth class,
  principal source, ownership policy, exposure, and foreign-object status:
  `docs/security/API_AUTH_TIER_BOLA_CONTRACT_PACK.md:11`.
- SEC-001 for Bayesian adherence is implemented for auth-derived identity:
  `docs/security/SEC-001-bayes-adherence-horizontal-privilege-escalation.md:31`.
- The remaining first-class user-authentication mapping and operational
  alerting follow-up is still open:
  `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-first-class-auth-principal-mapping`.

## Future Alert Labels

The labels below are a future observability contract only. This PR does not emit
production telemetry, runtime alerts, metrics, or logs for these labels.

```text
auth_principal_mismatch
tier_transport_confusion
legacy_alias_auth_mismatch
object_owner_mismatch
dependency_override_auth_attempt
```

Runtime alerting for suspicious cross-subject attempts remains deferred under
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-first-class-auth-principal-mapping`.
