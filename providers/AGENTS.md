# Agent instructions (scope: providers/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `providers/` and below.
- Key files: `perplexity.py`, `ollama.py`, `pico.py`, `stub.py`.

## Conventions
- Keep provider interfaces stable; avoid leaking network calls into core logic.
- Use `stub.py` or local mocks for tests; avoid real network calls in unit tests.
- Keep secrets out of code; read from env or config.

## Import & CI safety (hard rules)

- No dynamic imports (`spec_from_file_location`, `exec_module`) anywhere in `providers/`.
- No network calls at import time. Provider modules must be import-safe.
- Unit tests must use `providers/stub.py` or monkeypatched transports.
- Secrets must be read from env/config only; never hardcode tokens.

### FitChef Agent API experiment

- `perplexity_agent.py` is a default-off, development-only FitChef text adapter.
  Keep selection at the existing two FitChef runtime seams; it must not enter
  the global `llm.py` selector or change CBT insight selection.
- Preserve fixed Responses API transport, explicit reviewed model and effort,
  empty tools, `store=False`, bounded input/output/timeout, and zero SDK retries.
  Provider failure must not trigger a second paid call or automatic Sonar reroute.
- Validate configuration and prompt budget before quota consumption; allocate
  the client only for admitted generation. Accept only completed, error-free,
  exact-model final assistant text and keep SDK exception content out of logs.
- Production/staging and real-user activation remain blocked pending reviewed
  Agent privacy/consent and the separately owned high-distress prerequisite.
  `store=False` is not evidence of zero retention or release readiness.

### Pre-commit verification
```bash
# 1. No dynamic imports
git grep -nE "spec_from_file_location|exec_module\(" providers

# 2. No import-time network calls (review context if found)
git grep -nE "requests\.|httpx\.|aiohttp\." providers

# 3. No hardcoded secrets
git grep -nE "TOKEN|SECRET|BEARER|API[_-]?KEY" providers

# All should be empty or only env variable names
```
