# PR-475 Review Response

## ✅ Addressed Review Comments

### 1) FastAPI / uvicorn minor bumps

- Confirmed the app uses an explicit FastAPI `lifespan` handler (`legacy_app.py`) rather than relying on deprecated `@app.on_event`.
- Runtime entrypoint remains canonical: `app.main:app` (Dockerfile + Makefile).
- Fixed `docker-compose.yaml` healthcheck to avoid relying on `curl` (the image healthcheck already uses Python).

### 2) OpenAI SDK 2.12–2.14 behavior changes

- Current usage is via the supported 2.x client surface:
  - `openai.OpenAI(...).models.list()`
  - `AsyncOpenAI(...).chat.completions.create(...)`
- No legacy `openai.ChatCompletion.create(...)` usage detected in the codebase.

### 3) Python version / lockfile regeneration drift

- Aligned local toolchain pinning by making `.python-version` match `.tool-versions` and CI/Docker (`3.13.6`).
- Updated setup docs (`README.md`, `AGENTS.md`) and added explicit `pip-compile` regeneration commands (`REQUIREMENTS.md`).
