<!-- markdownlint-disable MD013 -->
# PulsePlate Evidence Graph Runtime Epic

**Status:** PR-E0 governance umbrella
**Date:** 2026-04-28 (`America/New_York`)
**Canonical backlog anchor:** [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime)

## Decision

PulsePlate should not add "another RAG" or "another orchestrator" as the next
AI runtime step. The next governed layer is **Evidence Graph Runtime**: a
contract that makes evidence-bearing artifacts first-class assets with lineage,
idempotency, replay, policy versions, fingerprints, and admission behavior.

This epic strengthens the existing RAG, verification, knowledge-promotion, eval,
and advisory-wiki work without changing public product behavior in PR-E0.

## Rail Boundaries

| Rail | Name | Canonical role | Non-goals |
| --- | --- | --- | --- |
| Rail A | Product AI runtime | Runtime behavior backed by repo contracts, DB truth, verification bundles, tests, and merge gates | Advisory wiki truth, plugin/control-plane truth, premature semantic cache |
| Rail B1 | Advisory wiki / compiled memory | Non-canonical workforce planning memory and operator navigation | Product RAG replacement, public response logic, DB/API/legal truth |
| Rail B2 | Plugin/control-plane | Operational or advisory evidence from GitHub, Cloudflare, Figma, Hugging Face, Sentry, Jam, and similar systems | Product runtime truth, semantic-cache shortcuts, bounded-context ownership |

If Rail B1 or Rail B2 output conflicts with repo contracts, runtime behavior,
DB truth, OpenAPI, tests, legal/compliance truth, or canonical review artifacts,
the repo/runtime source of truth wins.

## Asset Contract Baseline

Every new evidence-bearing artifact introduced by this epic must define:

- `asset_type`
- `asset_id`
- `version`
- `rail`
- `upstream_assets`
- `fingerprint`
- `policy_version`
- `idempotency_key`
- replay behavior
- admission behavior

PR-E0 does not implement the contract in code. It freezes the governance shape
for later slices.

## PR Train

1. **PR-E1: Asset registry contracts**
   - Add minimal internal evidence asset references and fingerprint policy.
   - No DB migration, public API, or runtime behavior change.

2. **PR-E2: Unified eval event schema**
   - Normalize RAG gate artifacts such as `traces.jsonl`,
     `metrics_summary.json`, and `gate_report.md` into an append-only event
     contract.
   - No Iceberg, Parquet-first requirement, dashboard, or second eval source of
     truth.

3. **PR-E3: Knowledge promotion ledger and replay**
   - Add append-only promotion events, idempotency keys, deterministic
     supersession, dry-run replay, and promotion diff reporting.
   - Depends on PR-E1 and PR-E2.
   - No user-facing runtime changes.

4. **PR-E4: Active metadata admission**
   - Add deterministic decisions for `allow_execute`, `allow_promote`, and
     `allow_serve` using stale-upstream, policy, degraded-reason, fallback-rate,
     coverage, verification, and fingerprint checks.
   - Depends on PR-E1, PR-E2, and PR-E3.
   - No LLM call or hidden bypass flag.

5. **PR-E5: Advisory wiki evidence bridge**
   - Link advisory wiki artifacts to evidence assets while preserving the rule
     that wiki pages are planning memory, not runtime truth.
   - May proceed after PR-E1/PR-E2 scope is stable.

## Sequencing

```text
PR-E0 first:
  docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md
  docs/roadmap/BACKLOG_LEDGER.md
  AGENTS.md invariant

Then parallel-capable:
  PR-E1 asset registry contracts
  PR-E2 eval event schema
  PR-E5 advisory wiki evidence bridge

After PR-E1 + PR-E2:
  PR-E3 promotion ledger and replay

After PR-E1 + PR-E2 + PR-E3:
  PR-E4 active metadata admission
```

## Hard Boundaries

PR-E0 and the downstream train must not imply or implement:

- public API, DTO, OpenAPI, route, billing, entitlement, or user-facing behavior
  changes;
- DB migrations or persistent storage rollout before contracts stabilize;
- semantic cache, Redis, GPTCache, cache-hit logic, or semantic-cache metrics;
- GraphRAG runtime rollout;
- provider/model rewiring;
- advisory wiki as product runtime truth;
- plugin/control-plane output as product runtime truth.

Semantic cache remains blocked until evidence asset lineage, replay-safe
promotion, and metadata admission gates exist and a dedicated semantic-cache
gate explicitly opens.

## Role Order

PR-E0 uses coordinator-first execution with this role order:

1. `agent-coordinator`
2. `cursor-specialist-agent`
3. `architecture-specialist`
4. `rag-systems-agent`
5. `data-scientist-agent`
6. `security-auditor`
7. `qa-engineer-agent`
8. `bug-hunter`

The post-open review lane remains `qa-engineer-agent -> bug-hunter`.

## Validation

PR-E0 validation:

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
rg -n "Evidence Graph Runtime|semantic cache|Rail A|Rail B1|Rail B2" \
  AGENTS.md docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md docs/roadmap/BACKLOG_LEDGER.md
pre-commit run --all-files
make verify
```

Operator note: PR-E0 was allowed to start after an operator override while
current-head `main` CI was still settling after a merge. Merge readiness still
requires current-head PR evidence and the repo's canonical merge gates.
