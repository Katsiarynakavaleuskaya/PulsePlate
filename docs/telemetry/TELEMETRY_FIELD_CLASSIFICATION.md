# Telemetry Field Classification

| Field family | Persistence rule | Notes |
| --- | --- | --- |
| `pp.req.fingerprint` | store | Stable request hash |
| `http.route` / `http.status_code` / `duration.ms` | store | Low-cardinality span metadata |
| `query` / `request_body` | redact + truncate | Minimized before vault encryption |
| `llm_response` / `response_body` | redact + truncate | Minimized before vault encryption |
| `prompt` / `provider_trace` | hash only | Never stored in plaintext |
| `health_profile` / medical-like fields | hash only | Derived-sensitive by default |
| `pp.full_pointer_sha256` | store | Trace points to encrypted vault object only |

Canonical minimization base: `core/compliance/minimization.py`.
