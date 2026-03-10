# Provider Inventory

**Status:** Canonical
**Last updated:** 2026-03-08

This inventory documents current processor families that may participate in AI
or privacy-relevant flows.

| Provider family | Category | Role | Data scope | Activation |
| --- | --- | --- | --- | --- |
| PulsePlate local/runtime processing | First-party | Deterministic formulas, routing, local app logic | Wellness profile inputs and runtime processing | Always active |
| xAI / Grok family | External processor | Configured AI generation for selected insight surfaces | User-submitted text and derived prompts; PulsePlate tracing stores HMAC fingerprints and lengths only | Conditional |
| OpenAI-compatible family | External processor | Configured AI generation for selected insight surfaces | User-submitted text and derived prompts; PulsePlate tracing stores HMAC fingerprints and lengths only | Conditional |
| Anthropic-compatible family | External processor | Configured AI generation for selected insight surfaces | User-submitted text and derived prompts; PulsePlate tracing stores HMAC fingerprints and lengths only | Conditional |
| Ollama-compatible self-hosted family | Self-hosted processor | Local/self-hosted AI generation | User-submitted text and derived prompts; PulsePlate tracing stores HMAC fingerprints and lengths only | Conditional |
| Pico family | External processor | Configured AI generation for selected insight surfaces | User-submitted text and derived prompts; PulsePlate tracing stores HMAC fingerprints and lengths only | Conditional |

## Rules

- Conditional families are not all active at the same time; actual activation depends on deployment configuration.
- Provider-side retention and downstream processing follow the selected provider or self-hosted deployment policy.
- Enabling an external provider does not move the product into a clinical lane by itself.
