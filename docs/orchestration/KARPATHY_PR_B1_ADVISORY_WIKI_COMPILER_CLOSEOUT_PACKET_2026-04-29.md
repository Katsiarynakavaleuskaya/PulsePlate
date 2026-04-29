# Karpathy PR-B1 Advisory Wiki Compiler Closeout Packet

**Branch:** `codex/karpathy-advisory-wiki-compiler-b1-closeout`
**Title:** `docs(roadmap): close advisory wiki compiler ledger`
**Date:** 2026-04-29
**Scope:** docs/governance closeout for Rail B1 advisory wiki compiler

## Summary

PR-B1 is a closeout reconciliation lane, not a compiler implementation lane.
Live repository truth shows the advisory wiki compiler v1 already landed in
PR #1371, with semantics hardening landed in PR #1372. This PR updates the
roadmap/ledger spine so the stale B1 item no longer appears open.

## Coordinator Workflow

Role order:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Active skills:

- `pulseplate-workflow`
- `pulseplate-gates`
- `pulseplate-guards`
- `pulseplate-pr-review`

## Evidence

- PR #1371 merged on 2026-04-07:
  `72b665763db36291b132ee148d347d7d6d8d273e`
- PR #1372 merged on 2026-04-08:
  `0c997be2352603c1bd5820d6d98f1c6b25793204`
- Canonical review artifacts:
  `docs/review/PR_1371_FIXED_MAPPING.md`,
  `docs/review/PR_1372_FIXED_MAPPING.md`
- Implementation evidence:
  `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`,
  `scripts/orchestration/wiki_ingest.py`,
  `scripts/orchestration/wiki_query.py`,
  `scripts/orchestration/wiki_lint.py`,
  `scripts/orchestration/wiki_promote.py`

## Boundaries

- Rail B1 remains advisory/operator memory only.
- Advisory wiki artifacts remain local and gitignored under
  `artifacts/orchestration/wiki/`.
- The compiler does not authorize product RAG replacement, runtime truth,
  public response logic, semantic cache, embeddings, vector DB, Redis/GPTCache,
  GraphRAG, or ContextManifest work.
- PR-B3 query/lint enrichment remains the next substantive workforce-memory
  implementation slice and is not bundled into this closeout.

## Validation

Required local gates for this docs-only closeout:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `git diff --check`
- `pytest -q tests/test_repo_policy_guards.py`
- Focused grep checks for PR #1371 / PR #1372 evidence, Rail B1 advisory-only
  wording, semantic-cache deferral, Rail B2 separation, and PR-B3 separation.
- `pre-commit run --all-files`
- `make validate-changed`

Full local `make verify` may be treated as machine-heavy if explicitly
operator-exempted; if so, the PR body and `docs/review/PR_<N>_FIXED_MAPPING.md`
must document the deferral and rely on current-head GitHub CI as the heavy
signal.
