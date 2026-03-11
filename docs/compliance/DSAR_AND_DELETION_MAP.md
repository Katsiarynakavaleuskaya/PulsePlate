# DSAR and Deletion Map

**Status:** Canonical internal map
**Last updated:** 2026-03-08

This document describes what PulsePlate can currently export or delete for
direct-user artifacts without promising a public self-service endpoint.

| Artifact | Storage | Subject binding | Export | Delete | Notes |
| --- | --- | --- | --- | --- | --- |
| Account and user row | SQL `users` | Direct `user_id` | Yes | Yes | Public DSAR API still deferred until auth/ownership contract is explicit |
| RAG feedback | SQL `rag_feedback` | Direct `user_id` | Yes | Yes | Query/preview/response fields are minimized before persistence |
| User knowledge corpus | SQL `user_knowledge` | Direct `user_id` | Yes | Yes | Personalization artifacts remain internal-only |
| Request fingerprints | Logs / rate-limit keying | Indirect network identifier | No | No | Retention-managed only |
| LLM quota usage | SQL `vip_llm_monthly_usage` | Key fingerprint | No | No | Support-led remediation only |
| Signed audit envelopes | JSONL audit trail | Event metadata | No | No | Retention-managed only |

## Current DSAR Posture

- Support can service access/export/delete requests for direct-user SQL artifacts.
- Internal runtime helpers now provide deterministic export coverage for `users`, plus bounded delete execution for `rag_feedback` and `user_knowledge` with an explicit account-delete plan.
- Pseudonymous security artifacts and minimized audit artifacts are not exposed as public self-service assets.
- Deletion is implemented as row removal or retention-driven cleanup, not arbitrary in-place editing.
