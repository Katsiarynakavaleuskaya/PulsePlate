# Karpathy PR-B4 Bounded Reference-Corpus Policy Packet

**Branch:** `codex/advisory-wiki-reference-corpus-policy-b4`
**Title:** `docs(orchestration): define bounded reference-corpus policy for advisory wiki`
**Date:** 2026-04-30
**Scope:** Rail B1 advisory wiki reference-corpus policy

## Summary

PR-B4 is a docs/governance slice for the Rail B1 advisory wiki line. It
defines how DeepWiki or similar reference corpora may be used as bounded,
read-only secondary aids while preserving repo artifacts as the only source of
truth.

This PR does not implement ingestion, embeddings, vector search, product RAG,
runtime policy, API contracts, OpenAPI, DTOs, semantic cache, GraphRAG,
Redis/GPTCache, or ContextManifest behavior.

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
- `pulseplate-ledger`
- `pulseplate-pr-review`

Required tooling:

- GitHub for PR truth, current-head checks, review-thread audit, and
  merge-readiness evidence.

Conditionally active:

- CodeRabbit, Sourcery, and Cubic review governance only if those bots actually
  run or comment on the PR.

Explicitly not needed unless a concrete gate demands it:

- Browser Use, Computer Use, Linear, Canva, Figma, Hugging Face, Cloudflare,
  Life Science Research, LaTeX Tectonic, and Remotion.

## Policy Contract

- Reference corpora are read-only secondary understanding aids for operators and
  role agents.
- Repo-tracked artifacts remain the only canonical source of truth for product
  behavior, runtime contracts, orchestration policy, ledger state, and merge
  governance.
- Any conflict between a reference corpus and repo artifacts resolves to repo
  truth.
- Reference corpora cannot authorize product behavior, public response shape,
  DB/runtime truth, API/DTO/OpenAPI contracts, legal/compliance claims, medical
  or production marketing claims, or knowledge promotion.
- Reference-corpus notes must not be promoted into canonical docs, runtime
  code, or advisory wiki pages without a separate repo-reviewed PR.
- Advisory wiki artifacts remain local support-plane material, not product RAG
  memory and not persistent runtime truth.

## Boundaries

- Rail A product runtime remains separate from Rail B1 advisory wiki memory.
- Rail B2 plugin/control-plane work remains separate from Rail B1.
- External corpus import, sync, scraping, and background refresh are out of
  scope.
- Contradiction lint, ranking/index weighting, manifest/history, and reference
  corpus admission tooling remain follow-ons unless separately opened.
- This policy does not open semantic cache or GraphRAG gates.

## Validation

Required local gates:

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `python3 scripts/orchestration/task_bootstrap.py --goal "Define PR-B4 bounded reference-corpus policy for advisory wiki" --task-class "Orchestration" --pr-phase pre_open`
- `git diff --check`
- `python3 scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/KARPATHY_PR_B4_BOUNDED_REFERENCE_CORPUS_POLICY_PACKET_2026-04-30.md docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md docs/roadmap/BACKLOG_LEDGER.md docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md docs/review/PR_<new_number>_FIXED_MAPPING.md`
- `pytest -q tests/test_repo_policy_guards.py`
- `pre-commit run --all-files`

Full local `make verify` is intentionally not run under the operator-approved
CPU exception for this docs/governance lane. PR body and the fixed-mapping
artifact must document the deferral; current-head GitHub CI and strict
merge-readiness checks remain required before merge-ready claims.

Post-open review order:

1. `qa-engineer-agent`
2. `bug-hunter`

## Security Notes

This PR is docs/governance only. It introduces no new runtime entrypoint,
network retrieval path, persistence path, secret handling, authentication
surface, or user-facing AI behavior.

## Marketing & GTM

No marketing or GTM claim is changed. Reference corpora must not be used to
support public product, medical, wellness efficacy, or production-readiness
claims without a separate reviewed evidence packet.
