# Karpathy PR-B3 Advisory Wiki Query/Lint Enrichment Packet

**Branch:** `codex/advisory-wiki-query-lint-enrichment-b3`
**Title:** `feat(orchestration): enrich advisory wiki query and lint without changing SoT`
**Date:** 2026-04-30
**Scope:** Rail B1 advisory wiki query/lint enrichment

## Summary

PR-B3 is the next substantive Rail B1 implementation slice after the advisory
wiki compiler closeout. It enriches local operator query and lint behavior while
preserving the advisory wiki as non-canonical compiled memory.

## Coordinator Workflow

Role order:

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `backend-engineer`
5. `security-auditor`
6. `qa-engineer-agent`
7. `bug-hunter`

Active skills:

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-pr-review`
- `agents-md`
- `code-review-expert`

Conditionally active:

- `coderabbit:code-review` if review quota is available; otherwise run a
  manual CodeRabbit/Sourcery-style review and record dispositions.

## Implementation Contract

- `wiki_query.py` keeps existing `list`, `search`, and `detail` JSON output
  unchanged by default.
- `wiki_query.py --mode search --include-context` may add deterministic
  `heading`, `excerpt`, and `match_count` fields for each hit.
- `wiki_lint.py` remains read-only and local-only.
- `wiki_lint.py` may report deterministic index/page drift and stale local
  `pages/<slug>.md` links.
- External URLs, non-wiki relative links, embeddings, vector search, network
  retrieval, contradiction checks, and product-runtime semantics are out of
  scope.

## Boundaries

- Rail B1 remains advisory/operator memory only.
- Advisory wiki artifacts remain local and gitignored under
  `artifacts/orchestration/wiki/`.
- This PR does not authorize product RAG replacement, runtime truth, public
  response logic, semantic cache, embeddings, vector DB, Redis/GPTCache,
  GraphRAG, or ContextManifest work.
- Rail B2 plugin/control-plane work remains separate.
- PR-B4 bounded reference-corpus policy remains separate.

## Validation

Required local gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Enrich PR-B3 advisory wiki query and lint without changing SoT" --task-class "Orchestration" --pr-phase pre_open`
- `git diff --check`
- `pytest -q tests/test_wiki_query.py tests/test_wiki_lint.py tests/test_wiki_ingest.py tests/test_wiki_promote.py tests/test_wiki_compiler_keys.py tests/test_repo_policy_guards.py`
- `pre-commit run --all-files`
- Full local `make verify` is intentionally not run for this lane under the
  operator-approved CPU exception. Do not run `make` targets locally unless the
  operator explicitly re-enables them; document the deferral in the PR body and
  fixed-mapping artifact.

Post-open review order:

1. `qa-engineer-agent`
2. `bug-hunter`

Merge readiness still requires review-thread disposition, current-head checks,
the merge-readiness wrapper, and the final wait-window.
