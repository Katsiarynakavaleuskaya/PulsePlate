# OTel and OpenInference Mapping

**Status:** Reference mapping for PulsePlate backend GenAI tracing
**Last updated:** 2026-03-11

## Span Types

| PulsePlate surface | Span name pattern | `openinference.span.kind` | Notes |
| --- | --- | --- | --- |
| Insight orchestration | `insight chain` | `CHAIN` | Main `/insight` and `/api/v1/insight` route-local span |
| CBT orchestration | `cbt insight agent` | `AGENT` | Route-local span for `/api/v1/pro/cbt/insight` |
| LLM inference | `inference {model}` | `LLM` | Wraps `provider.generate(...)` at call site |
| Retrieval | `retrieval query` | `RETRIEVER` | Wraps bounded RAG retrieval calls |
| Tool call | `tool {name}` | `TOOL` | Helper available for future surfaces |

## Exported Attributes

### Standard OTel GenAI attributes

- `gen_ai.provider.name`
- `gen_ai.request.model`
- `gen_ai.response.model`
- `gen_ai.request.temperature` when explicitly known
- `gen_ai.request.top_k` when explicitly known
- `gen_ai.usage.input_tokens`
- `gen_ai.usage.output_tokens`

### OpenInference classification

- `openinference.span.kind`

### PulsePlate-safe custom attributes

- `pulseplate.request.id`
- `pulseplate.user.tier`
- `http.route`
- `pulseplate.feature_flags.*`
- `pulseplate.prompt.fingerprint`
- `pulseplate.prompt.length`
- `pulseplate.completion.fingerprint`
- `pulseplate.completion.length`
- `pulseplate.retrieval.max_chunks`
- `pulseplate.rag.hops`
- `pulseplate.rag.agent_id`
- `pulseplate.route_type`

## Event Policy

Allowed event names:

- `pulseplate.gen_ai.prompt`
- `pulseplate.gen_ai.completion`

Allowed event payloads:

- HMAC fingerprint
- content length
- role where relevant

Raw prompt/completion bodies are not exported in v1.

## Explicit Non-Goals

- No orchestration telemetry mapping here
- No vendor-specific dashboard contract
- No frontend/mobile trace propagation in this phase
