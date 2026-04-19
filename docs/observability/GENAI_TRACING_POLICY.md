# GenAI Tracing Policy

**Status:** Canonical for backend GenAI tracing
**Last updated:** 2026-03-11

## Scope

This policy applies to backend GenAI tracing for:

- `/insight`
- `/api/v1/insight`
- `/api/v1/pro/cbt/insight`

It does **not** define frontend analytics, iOS analytics, or orchestration telemetry.

## Data-Minimization Contract

PulsePlate backend GenAI tracing exports only deterministic, low-risk metadata:

- request id
- route template
- tier (`FREE` / `PRO` / `VIP` when known)
- bounded feature-flag state
- provider/model identifiers
- prompt/completion HMAC fingerprints
- prompt/completion lengths
- bounded token-usage estimates
- bounded retrieval metadata such as hops and max chunks

PulsePlate backend GenAI tracing does **not** export in v1:

- raw prompts
- raw completions
- chunk contents
- chunk previews
- arbitrary free-text metadata
- raw paths with dynamic identifiers

## HMAC Fingerprinting

- Secret source: `PULSE_OBS_HMAC_KEY`
- Algorithm: `HMAC-SHA256`
- Purpose: deterministic correlation without storing raw prompt/completion payloads

If tracing is enabled but the HMAC key is missing, tracing must fail closed and fall back to no-op behavior rather than exporting unhashed payloads.

## Runtime Behavior

- Bootstrap lives in `app/main.py` via `app/bootstrap/tracing.py`
- `legacy_app.py` remains a thin compatibility layer and must not register tracing infrastructure
- Tracing is best-effort and must never break request handling
- Optional dependencies must be import-safe and patchable in tests

## Semantic Conventions

- OpenTelemetry GenAI attributes use the current `gen_ai.*` namespace
- OpenInference span classification uses `openinference.span.kind`
- Request/root spans are standard HTTP/backend spans and are kept separate from orchestration telemetry

## Related Documents

- `docs/observability/OTEL_OPENINFERENCE_MAPPING.md`
- `docs/analytics/README.md`
- `docs/compliance/DATA_CLASSIFICATION_AND_PROCESSING_MATRIX.md`
- `docs/compliance/PROVIDER_INVENTORY.md`
- `docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md`
