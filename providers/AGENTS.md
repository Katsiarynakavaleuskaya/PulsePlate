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
