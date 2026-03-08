# Data Classification and Processing Matrix

**Status:** Canonical
**Last updated:** 2026-03-08
**Policy version:** `2026-03-08.eu-first.v1`

This matrix is the canonical control-plane view for the current wellness runtime.

| Surface / artifact | Runtime / store | Purpose | Sensitivity | Retention | Deletion path | Third-party exposure |
| --- | --- | --- | --- | --- | --- | --- |
| `/bmi`, `/api/v1/bmi`, `/api/v1/pro/bmi/calculate` | Request scope | BMI wellness screening and explanation | Health-adjacent | Request-scoped unless copied into another feature path | Not directly applicable for request-only execution | No automatic third-party sharing |
| `/api/v1/bodyfat` | Request scope | Body-fat estimation | Health-adjacent | Request-scoped unless copied into another feature path | Not directly applicable for request-only execution | No automatic third-party sharing |
| `/api/v1/pro/nutrition/daily`, `/api/v1/pro/meal/weekly`, `/api/v1/premium/plate` | Request scope | Deterministic wellness targets and planning | Health-adjacent | Request-scoped unless persisted elsewhere | Not directly applicable for request-only execution | No automatic third-party sharing |
| `/insight`, `/api/v1/insight`, `/api/v1/pro/cbt/insight` | Runtime + minimized audit metadata | AI-generated wellness analysis | Derived sensitive | Provider/deployment specific; local audit metadata minimized | Local direct-user artifacts via DSAR map; provider-side artifacts follow provider terms | Yes, when a configured provider family is enabled |
| `/api/v1/feedback/rag` | SQL table `rag_feedback` | Quality improvement and retrieval/response feedback | Derived sensitive | Until deletion or retention review | Direct row deletion for user-bound artifacts | No automatic third-party sharing by default |
| `user_knowledge` artifacts | SQL table `user_knowledge` | Personalization and user-specific retrieval | Derived sensitive | Until deletion or retention review | Direct row deletion for user-bound artifacts | No automatic third-party sharing by default |
| Request fingerprints | Logs / rate-limit keying | Abuse prevention, rate limiting, operational security | Pseudonymous | `core/log_retention.py` policy | Retention-managed cleanup only | No automatic third-party sharing by default |
| Signed audit envelopes | `artifacts/orchestration/agent_control_audit.jsonl` | Tamper-evident record of privileged AI actions | Minimized security metadata | Security/audit policy | Retention-managed only | No automatic third-party sharing by default |
| LLM quota usage | SQL table `vip_llm_monthly_usage` | Economic abuse prevention | Pseudonymous / indirect | Billing/security policy | Support-led remediation or retention | No automatic third-party sharing by default |

## Notes

- “Health-adjacent” means wellness-profile inputs or formula-driven outputs that may reveal sensitive inferences depending on context.
- “Derived sensitive” means generated or inferred content that should be handled more carefully than generic telemetry.
- Current source of truth for `/privacy`: `core/compliance/privacy.py`, rendered by `legacy_app.py`.
- Canonical legal publication endpoints are `GET /privacy` and `GET /terms`.
