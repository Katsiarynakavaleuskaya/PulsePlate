# Evals lane instructions

Scope: `evals/` and subdirectories

## Purpose
This directory is for offline evaluation only.
It must never become part of request-path runtime.

## Hard rules
- Do not import from `evals/` inside `app/`, `core/`, `frontend/`, or `ios/`
- Heavy eval dependencies (`ragas`, `datasets`, future judge libs) must be lazy-imported inside CLI entrypoints
- Do not add eval dependencies to `requirements.txt` or `requirements-dev.txt`; keep them in `requirements-evals.txt`
- Generated reports are local artifacts and must not be committed
- Bootstrap eval PRs are report-only by default
- Semantic cache, graph retrieval, and provider behavior changes are out of scope for eval bootstrap PRs
- First evaluation surface is `/api/v1/pro/cbt/insight` unless a later packet explicitly expands scope
- Do not create a second canonical evaluation source of truth beside `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`

## Companion test note
- Eval-lane test-specific rules live in `tests/evals/AGENTS.md`
