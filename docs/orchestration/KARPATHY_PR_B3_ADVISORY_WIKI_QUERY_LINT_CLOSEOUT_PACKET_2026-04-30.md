# Karpathy PR-B3 Advisory Wiki Query/Lint Closeout Packet

**Branch:** `codex/advisory-wiki-query-lint-enrichment-b3-closeout`
**Title:** `docs(roadmap): close advisory wiki query-lint ledger`
**Date:** 2026-04-30
**Scope:** docs/governance closeout for Rail B1 advisory wiki query/lint enrichment

## Summary

PR-B3 is already merged as PR #1596. This closeout lane reconciles the
roadmap/ledger spine so the advisory wiki query/lint enrichment item no longer
appears in progress.

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
- `pulseplate-ledger`
- `pulseplate-pr-review`
- `agents-md`
- `code-review-expert`

Conditionally active:

- GitHub CLI/plugin for PR and current-head check truth.
- `coderabbit:code-review` if review quota is available; otherwise run a
  manual CodeRabbit/Sourcery-style review and record dispositions.

Non-active unless a concrete blocker appears:

- Browser Use, Computer Use, LaTeX Tectonic, Google Drive, Cloudflare,
  Hugging Face, Life Science Research, and Expo.

## Evidence

- PR #1596 merged on 2026-04-30:
  `438d135f7ae0a07cb28549488284a40e08183c92`
- Implementation packet:
  `docs/orchestration/KARPATHY_PR_B3_ADVISORY_WIKI_QUERY_LINT_ENRICHMENT_PACKET_2026-04-30.md`
- Canonical review artifact:
  `docs/review/PR_1596_FIXED_MAPPING.md`
- Implementation surfaces:
  `scripts/orchestration/wiki_query.py`,
  `scripts/orchestration/wiki_lint.py`,
  `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`

## Boundaries

- Rail B1 remains advisory/operator memory only.
- This closeout does not reopen PR-B3 implementation scope.
- This lane does not authorize product RAG replacement, runtime truth, public
  response logic, semantic cache, embeddings, vector DB, Redis/GPTCache,
  GraphRAG, ContextManifest, OpenAPI, frontend, iOS, DB, Cloudflare, Expo,
  Hugging Face, or Life Science implementation work.
- PR-B4 bounded reference-corpus policy remains the next substantive Rail B1
  slice and is not bundled into this closeout.

## Validation

Required local gates for this docs-only closeout:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Close PR-B3 advisory wiki query-lint ledger after merged PR #1596" --task-class "Orchestration" --pr-phase pre_open`
- `git diff --check`
- `pytest -q tests/test_repo_policy_guards.py`
- Focused grep checks for PR #1596 evidence, Rail B1 advisory-only wording,
  semantic-cache deferral, and PR-B4 separation.
- `pre-commit run --all-files`
- `make validate-changed`

Full local `make verify` may be treated as machine-heavy if explicitly
operator-exempted; if so, the PR body and `docs/review/PR_<N>_FIXED_MAPPING.md`
must document the deferral and rely on current-head GitHub CI as the heavy
signal.
