# Karpathy Advisory Wiki Umbrella S0 Packet

**Date:** 24 April 2026
**Scope:** docs-only governance lane for Rail B1 advisory workforce memory
**Mode:** pre-open governance packet

## Purpose

Freeze one narrow docs-only PR that makes the Karpathy-style advisory wiki rail
decision-complete without widening into product RAG, runtime truth, semantic
cache, or plugin/control-plane ownership.

This packet exists to:

- lock Rail B1 as advisory workforce compiled memory only;
- keep product AI runtime truth on Rail A;
- keep plugin/control-plane families on Rail B2;
- keep semantic cache as a deferred product-runtime gate only;
- preserve one-PR-at-a-time cadence and worktree isolation.

## Hard boundaries

- No runtime/product code changes
- No route, OpenAPI, schema, DTO, storage, DB, authz, billing, or public
  response-contract mutation
- No semantic cache implementation or gate opening
- No Redis, GPTCache, embeddings, vector DB, GraphRAG, or ContextManifest work
- No plugin implementation work for GitHub, Cloudflare, Figma, Hugging Face,
  or similar control-plane families
- No public/user-facing RAG replacement
- No writes to canonical knowledge, runtime DB, or product source-of-truth
  stores
- No side-effectful tool/action execution, provider calls, autonomous
  promotion, merge, release, or user-facing automation

## Canonical rail split

### Rail A — Product AI runtime

Rail A remains the canonical runtime rail. Repo artifacts, contracts, DB,
runtime behavior, backend schemas, OpenAPI, and tests remain the source of
truth for product AI behavior and public response contracts.

### Rail B1 — Karpathy advisory wiki

Rail B1 is non-canonical advisory workforce memory only.

In scope:

- local operator memory;
- advisory wiki pages;
- advisory compiler/query/lint/promote governance;
- read-only reference-corpus policy;
- repository navigation and accumulated decision memory.

Out of scope:

- product RAG replacement;
- public/user-facing retrieval source;
- DB/runtime/API/legal/compliance truth;
- OpenAPI, backend schemas, or public response-contract truth;
- semantic cache, embeddings, vector DB, Redis/GPTCache, GraphRAG, or
  ContextManifest work.

If advisory wiki/support-plane output conflicts with repo files, contracts, DB
state, OpenAPI, backend schemas, tests, legal/compliance truth, or canonical
governance artifacts, repo truth wins.

### Rail B2 — Plugin/control-plane families

Rail B2 remains separate from this packet. GitHub, Cloudflare, Figma, Hugging
Face, and similar plugin/control-plane artifacts are advisory or operational
only and must not become product runtime truth implicitly.

Rail B2 must not be used as a shortcut for:

- semantic-cache rollout;
- bounded-context ownership;
- product RAG/runtime features;
- public response-contract logic.

## Required role-agent order

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains
  mandatory.

## Canonical files for PR-S0-B1

- `docs/orchestration/KARPATHY_ADVISORY_WIKI_UMBRELLA_S0_PACKET_2026-04-24.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` (cross-link only;
  no gate change)

## Deliverables

- one canonical S0-B1 packet for the Karpathy advisory wiki umbrella;
- backlog B1 umbrella updated to reference this packet and downstream
  advisory wiki children;
- epic Rail B1 wording updated to point to this packet;
- semantic cache retained as deferred product-runtime-only scope;
- Rail B2/plugin-control-plane families kept separate.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- grep verification for Rail B1 advisory/non-canonical/non-product-facing
  wording
- grep verification that product RAG replacement remains forbidden
- grep verification that semantic cache remains deferred and product-runtime
  only
- grep verification that Rail B2/plugin-control-plane remains separate
