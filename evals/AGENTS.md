# Evals lane instructions

Scope: `evals/` and subdirectories

## Purpose
This directory is for offline evaluation only.
It must never become part of request-path runtime.

## Hard rules
- Do not import from `evals/` inside `app/`, `core/`, `frontend/`, or `ios/`
- Heavy eval dependencies (`ragas`, `datasets`, future judge libs) must be lazy-imported inside CLI entrypoints
- Do not add eval dependencies to `requirements.txt` or `requirements-dev.txt`; keep high-level declarations in `requirements-evals.in` and exact pins in compiled `requirements-evals.txt`
- Keep the `ragas<1.0` compatibility bound until the companion runner migrates from the current v0.4-compatible imports
- Generated reports are local artifacts and must not be committed
- Bootstrap eval PRs are report-only by default
- Semantic cache, graph retrieval, and provider behavior changes are out of scope for eval bootstrap PRs
- First evaluation surface is `/api/v1/pro/cbt/insight` unless a later packet explicitly expands scope
- Do not create a second canonical evaluation source of truth beside `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md`
- The "single canonical evaluation SoT" rule applies to release-gate evaluation lanes. Sibling measurement contracts (e.g., validity, psychometrics) for different measurement concerns may exist as separate docs under `docs/evals/` provided they explicitly defer to `PULSEPLATE_RAG_RELEASE_GATES.md` for PASS/NO-GO decisions. See `docs/evals/PULSEPLATE_EVAL_VALIDITY_CONTRACT.md`

## Companion test note
- Eval-lane test-specific rules live in `tests/evals/AGENTS.md`
