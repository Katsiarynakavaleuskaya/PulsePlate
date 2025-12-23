# Agent instructions (scope: providers/ and subdirectories)

## Scope and layout
- This AGENTS.md applies to: `providers/` and below.
- Key files: `grok.py`, `ollama.py`, `pico.py`, `stub.py`.

## Conventions
- Keep provider interfaces stable; avoid leaking network calls into core logic.
- Use `stub.py` or local mocks for tests; avoid real network calls in unit tests.
- Keep secrets out of code; read from env or config.
