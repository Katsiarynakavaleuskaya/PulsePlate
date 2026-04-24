# Plugin-Control-Plane Families Umbrella S0 Packet

**Date:** 24 April 2026
**Scope:** governance lane for Rail B2 advisory/control-plane families, with a
minimal typecheck-restoration exception
**Mode:** pre-open governance packet

## Purpose

Freeze one narrow governance PR that makes the plugin/control-plane rail
decision-complete without widening into product runtime truth, semantic cache,
bounded-context ownership, or public response logic.

This packet exists to:

- lock Rail B2 as advisory/control-plane family mapping only;
- keep product AI runtime truth on Rail A;
- keep Karpathy advisory wiki/workforce memory on Rail B1;
- keep semantic cache as a deferred product-runtime gate only;
- preserve one-PR-at-a-time cadence and worktree isolation.

## Scope-extension exception

The original lane is docs/governance-only. During final merge preparation,
fresh `main` was confirmed to fail `make typecheck` on
`core/food_sources/source_preflight.py:129` with a redundant `cast(...)` error.
PR-S0-B2 may include the minimal source-level typecheck-restoration change for
that exact mainline blocker.

This exception does not authorize product-runtime behavior changes, API/schema
changes, semantic-cache work, plugin implementation, or any Rail B2 runtime
authority.

## Hard boundaries

- No runtime/product code changes except the explicit typecheck-restoration
  exception above
- No route, OpenAPI, schema, DTO, storage, DB, authz, billing, or public
  response-contract mutation
- No semantic cache implementation or gate opening
- No Redis, GPTCache, embeddings, vector DB, GraphRAG, or ContextManifest work
- No plugin implementation work for GitHub, Cloudflare, Figma, Hugging Face,
  or similar control-plane families
- No Cloudflare deployment, Access policy mutation, worker changes, or preview
  promotion
- No Figma asset promotion, design-to-code activation, Code Connect mutation, or
  runtime design authority
- No Hugging Face model job, model promotion, provider runtime, or research
  result treated as product truth
- No public/user-facing RAG replacement
- No side-effectful tool/action execution, provider calls, autonomous
  promotion, merge, release, or user-facing automation

## Canonical rail split

### Rail A — Product AI runtime

Rail A remains the canonical runtime rail. Repo artifacts, contracts, DB,
runtime behavior, backend schemas, OpenAPI, and tests remain the source of
truth for product AI behavior and public response contracts.

Rail B2 must not overtake or shortcut Rail A sequencing.

### Rail B1 — Karpathy advisory wiki

Rail B1 remains separate from this packet. Advisory wiki/support-plane outputs
are non-canonical workforce memory only and must not become plugin/control-plane
authority or product runtime truth.

### Rail B2 — Plugin/control-plane families

Rail B2 is advisory/control-plane only.

Family placement:

- GitHub -> governance / CI / review truth
- Cloudflare -> edge / preview / Access control-plane
- Figma -> design execution / review evidence
- Hugging Face -> research / model-eval / external model tooling

Truth model:

- plugin/control-plane artifacts are advisory or operational evidence only;
- plugin/control-plane artifacts never become product AI runtime truth
  implicitly;
- plugin/control-plane artifacts never authorize semantic-cache rollout,
  bounded-context ownership, public response-contract logic, or product RAG
  replacement.

If plugin/control-plane artifacts conflict with repo files, contracts, DB
state, OpenAPI, backend schemas, tests, legal/compliance truth, or canonical
governance artifacts, repo truth wins.

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

## Canonical files for PR-S0-B2

- `docs/orchestration/PLUGIN_CONTROL_PLANE_FAMILIES_UMBRELLA_S0_PACKET_2026-04-24.md`
- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/orchestration/WAVE6_AI_RUNTIME_AND_ADVISORY_SERIES_PACKET_2026-04-13.md`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` (cross-link only;
  no gate change)

## Deliverables

- one canonical S0-B2 packet for the plugin/control-plane families umbrella;
- backlog B2 umbrella updated to reference this packet and target `PR-S0-B2`;
- epic Rail B2 wording updated to point to this packet;
- semantic cache retained as deferred product-runtime-only scope;
- Rail B1 advisory wiki kept separate from plugin/control-plane families.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- grep verification for Rail B2 advisory/control-plane wording
- grep verification that GitHub, Cloudflare, Figma, and Hugging Face are mapped
  as advisory/control-plane families
- grep verification that product runtime truth and public response logic remain
  forbidden
- grep verification that semantic cache remains deferred and product-runtime only
- grep verification that Rail B1 advisory wiki remains separate
