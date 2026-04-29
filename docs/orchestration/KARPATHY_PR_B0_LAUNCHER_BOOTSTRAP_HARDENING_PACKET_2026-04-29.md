# Karpathy PR-B0 Launcher-Bootstrap Hardening Packet

**Date:** 2026-04-29
**Branch:** `codex/karpathy-launcher-bootstrap-hardening-b0`
**Title:** `fix(local-workforce): harden launcher/bootstrap seam before advisory wiki expansion`

## Summary

PR-B0 hardens the repo-side cold-start bridge before Rail B1 advisory wiki compiler work. The
lane keeps launcher/bootstrap truth bounded: repo scripts may run analyze preflight and print the
next `task_bootstrap.py` command, but they must not claim global host auto-start or replace manual
`agent-coordinator` when launcher/runtime auto-capture is unavailable.

## Role Order

`agent-coordinator -> cursor-specialist-agent -> architecture-specialist -> security-auditor -> qa-engineer-agent -> bug-hunter`

Active skills:

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-pr-review`

## Scope

In scope:

- `scripts/orchestration/local_session_bootstrap.sh` CLI hardening.
- Launcher/bootstrap docs alignment in the existing local workforce surfaces.
- Backlog/RAG-Karpathy ledger evidence for PR-B0.
- Focused tests for the bridge contract.

Out of scope:

- PR-B1 advisory wiki compiler implementation.
- Product RAG replacement or runtime truth changes.
- Semantic cache, embeddings, vector DB, Redis/GPTCache, GraphRAG, or ContextManifest.
- Public API, OpenAPI, frontend, iOS, DB, Cloudflare, Figma, Hugging Face, or host wrapper mutation.

## Implementation Contract

- The repo bridge remains opt-in and non-mutating (`scripts/orchestration/local_session_bootstrap.sh:1-4`, `scripts/orchestration/local_session_bootstrap.sh:146-166`).
- `--help` must not run preflight (`scripts/orchestration/local_session_bootstrap.sh:63-68`).
- No-argument mode preserves the legacy placeholder recipe (`scripts/orchestration/local_session_bootstrap.sh:167-176`).
- Supplying concrete bootstrap options requires both `--goal` and `--task-class` (`scripts/orchestration/local_session_bootstrap.sh:87-139`).
- `--path` is repeatable and passed to `check_preflight.py --mode analyze` so scoped `AGENTS.md`
  resolution matches the printed bootstrap command (`scripts/orchestration/local_session_bootstrap.sh:112-115`, `scripts/orchestration/local_session_bootstrap.sh:145-147`).
- `--pr-phase` accepts only `pre_open`, `post_open_review`, `merge_ready`, or `none` (`scripts/orchestration/local_session_bootstrap.sh:136-139`).
- The script prints the exact `task_bootstrap.py` command but does not execute it (`scripts/orchestration/local_session_bootstrap.sh:154-166`).

## Validation

Local gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Harden PR-B0 launcher/bootstrap seam before advisory wiki expansion" --task-class "Orchestration" --pr-phase pre_open`
- `pytest -q tests/test_local_session_bootstrap.py tests/test_task_bootstrap.py tests/test_bootstrap_sync_policy.py tests/test_repo_policy_guards.py`
- `git diff --check`
- `pre-commit run --all-files`
- `make validate-changed`
- `make verify` unless operator explicitly applies the machine-heavy exception.

PR readiness:

- Open as draft if current-head `main` is still pending under operator-approved override.
- Add `docs/review/PR_<N>_FIXED_MAPPING.md` after the PR number exists.
- Run post-open `qa-engineer-agent -> bug-hunter`.
- Do not mark ready or merge until current-head PR checks and merge-readiness governance pass.
