# Wave 6 AI Runtime and Advisory Series Packet

**Date:** 13 April 2026
**Scope:** docs-only series bootstrap lane for the next AI/runtime train
**Mode:** pre-open governance packet

## Purpose

Freeze one narrow docs-only starting PR that makes the next series
decision-complete without widening into runtime implementation.

This packet exists to:

- lock the product AI runtime train to `A1b -> A5`;
- keep semantic cache as a deferred optimization gate only;
- split advisory/workforce memory from plugin/control-plane families;
- preserve one-PR-at-a-time cadence and worktree isolation.

## Hard boundaries

- No runtime/product code changes
- No OpenAPI or public contract mutation
- No semantic cache implementation
- No Redis / GPTCache rollout
- No plugin implementation work for GitHub / Cloudflare / Figma / Hugging Face
- No widening into `A6-A9`

## Canonical rail split

### Rail A — Product AI runtime

Canonical runtime rail only.

In scope for this series:

- `A1b` PRO quota reconciliation
- `A2` RAG hardening follow-through
- `A3` AI bounded-context packet
- `A4` bounded-context extraction
- `A5` LLM reliability/security gates

Out of scope for this series:

- semantic cache implementation
- philosophy rollout
- recursive rollout
- speed optimization
- scientific reliability publication

### Rail B1 — Workforce/wiki compiled memory

Advisory-only compiled memory rail.

Examples:

- local support plane
- advisory wiki/compiler/query/lint/promote flows
- operator-facing accumulated memory

### Rail B2 — Plugin/control-plane families

Advisory/control-plane rail only.

Family placement:

- GitHub -> governance / CI / review truth
- Cloudflare -> edge / preview / Access control-plane
- Figma -> design execution / review evidence
- Hugging Face -> research / model-eval / external model tooling

## Mandatory sequencing

1. `PR-S0` docs-only rail normalization
2. `PR-A1b`
3. `PR-A2`
4. `PR-A3`
5. `PR-A4`
6. `PR-A5`

Rules:

- do not open the next PR until the previous PR is merged, local `main` is synced,
  and current-head `main` is green/stable;
- do not use Rail B1 or Rail B2 as a shortcut for product runtime features;
- no plugin family may become runtime truth implicitly.

## Semantic cache gate

Semantic cache remains governed by:

- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`

Hard rule:

- no semantic cache work before `A1b`, `A2`, `A3`, `A4`, and at least `A5` are closed.

Later rollout order stays fixed:

1. docs contract
2. exact/fuzzy cache
3. bounded semantic cache for `/insight`
4. observability / false-hit guardrails
5. only then Redis / GPTCache backend

## Required role-agent order for this docs bootstrap lane

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `security-auditor`
5. `qa-engineer-agent`
6. `bug-hunter`

Rules:

- every assigned role agent must be used in this order;
- no assigned role agent may be skipped without an explicit packet update;
- the canonical post-open `qa-engineer-agent -> bug-hunter` pass remains mandatory.

## Canonical files for PR-S0

- `docs/roadmap/PulsePlate_RAG_LLM_Karpathy_Epic_Pipeline.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-wave6-ai-runtime-umbrella`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-karpathy-style-advisory-wiki-umbrella`
- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-plugin-control-plane-families-umbrella`
- `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md` (cross-link only if needed)
- this packet

## Deliverables for PR-S0

- explicit `Rail A / Rail B1 / Rail B2` structure in roadmap docs;
- one backlog umbrella for plugin/control-plane families;
- Wave 6 umbrella links normalized to the active `A1b -> A5` spine;
- semantic cache retained as deferred gate and not widened into implementation scope.

## Validation

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- grep verification for `Rail A`, `Rail B1`, `Rail B2`
- grep verification that semantic cache remains deferred-only
