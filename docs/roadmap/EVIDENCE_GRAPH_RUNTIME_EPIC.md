<!-- markdownlint-disable MD013 -->
# PulsePlate Evidence Graph Runtime Epic

**Status:** PR-E5 merged; semantic-cache gate reconciliation current
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
the repo/runtime source of truth wins. Evidence: `AGENTS.md:351`,
`AGENTS.md:352`, and `docs/roadmap/BACKLOG_LEDGER.md:1961`.

## Asset Contract Baseline

PR-E0 freezes the governance shape only. The following are proposed required
fields for PR-E1+; PR-E1 owns the concrete Python contract and deterministic
semantics. Evidence: `docs/roadmap/BACKLOG_LEDGER.md:1951` and
`docs/roadmap/BACKLOG_LEDGER.md:1961`.

- `asset_type`: the evidence artifact class, such as `eval_run`,
  `verification_bundle`, or `knowledge_record`.
- `asset_id`: a deterministic identifier for the asset and versioned content.
- `version`: the asset contract or artifact version.
- `rail`: the rail where the asset is allowed to operate (`runtime`,
  `advisory`, or `control_plane`).
- `upstream_assets`: the immutable parent assets used to produce this asset.
- `fingerprint`: a deterministic, non-sensitive content or metadata digest.
- `policy_version`: the gate or admission policy version applied to the asset.
- `idempotency_key`: the deterministic key that makes repeated writes/replay
  safe.
- replay behavior: how the asset participates in deterministic dry-run replay.
- admission behavior: how metadata can allow or block execute/promote/serve
  decisions.

PR-E0 does not implement the contract in code. It freezes the governance shape
for later slices.

## PR Train

1. **PR-E1: Asset registry contracts**
   - Backlog owner: [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime).
   - Add minimal internal evidence asset references and fingerprint policy.
   - No DB migration, public API, or runtime behavior change.
   - Done when asset IDs, fingerprints, idempotency keys, rail separation, and
     policy versions are deterministic and covered by focused tests.

2. **PR-E2: Unified eval event schema**
   - Backlog owner: [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime).
   - Normalize RAG gate artifacts such as `traces.jsonl`,
     `metrics_summary.json`, and `gate_report.md` into an append-only event
     contract.
   - No Iceberg, Parquet-first requirement, dashboard, or second eval source of
     truth.
   - Done when JSONL events carry `event_id`, asset reference, created time,
     policy version, and append-only writer coverage.

3. **PR-E3: Evidence promotion ledger and replay scaffold**
   - Backlog owner: [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime).
   - Add deterministic promotion ledger entries, idempotency keys,
     supersession, dry-run replay, and promotion diff reporting over normalized
     eval events from PR-E2.
   - Depends on PR-E1 and PR-E2.
   - No user-facing runtime changes, persistent writers, eval runners,
     semantic cache, GraphRAG, or advisory-wiki authority.
   - Done when replay is idempotent, invalid/degraded source events cannot be
     promoted silently, and dry-run replay reports deterministic diffs.

4. **PR-E4: Active metadata admission**
   - Backlog owner: [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime).
   - Add deterministic decisions for `allow_execute`, `allow_promote`, and
     `allow_serve` using stale-upstream, policy, degraded-reason, fallback-rate,
     coverage, verification, and fingerprint checks.
   - Depends on PR-E1, PR-E2, and PR-E3.
   - No LLM call, hidden bypass flag, runtime writer, semantic cache, GraphRAG,
     or advisory-wiki authority.
   - Done when the contract can produce deterministic non-allowing decisions
     for execute/promote/serve candidates before any side effect; runtime
     integration remains deferred to a separate wiring PR.

5. **PR-E5: Advisory wiki evidence bridge**
   - Backlog owner: [`ledger-p1-evidence-graph-runtime`](./BACKLOG_LEDGER.md#ledger-p1-evidence-graph-runtime).
   - Link advisory wiki artifacts to evidence assets while preserving the rule
     that wiki pages are planning memory, not runtime truth.
   - Proceeds after PR-E1/PR-E2/PR-E3/PR-E4 contracts are stable.
   - No wiki compiler rewrite, product RAG change, eval runner, semantic cache,
     GraphRAG, runtime rail mapping, or advisory wiki authority.
   - Done when existing wiki artifact metadata can map to advisory evidence
     assets and advisory admission inputs without granting runtime authority to
     wiki pages.

## Sequencing

```text
PR-E0 first:
  docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md
  docs/roadmap/BACKLOG_LEDGER.md
  AGENTS.md invariant

Then:
  PR-E1 asset registry contracts
  PR-E2 eval event schema

After PR-E1 + PR-E2:
  PR-E3 promotion ledger and replay

After PR-E1 + PR-E2 + PR-E3:
  PR-E4 active metadata admission

After PR-E4:
  PR-E5 advisory wiki evidence bridge

After PR-E5:
  docs(ai-runtime): reconcile semantic cache gate after Evidence Graph E5

After semantic-cache gate reconciliation:
  Verification Bundle Provenance Attestation v1 follow-up; semantic cache still requires a dedicated gate
```

## Operator-Selected Follow-Up

PR `#1884` is the merged Verification Bundle Provenance Attestation v1
baseline. It adds internal-only digest/count metadata to existing
`VerificationBundle` decisions so the product AI runtime can identify the
redacted input, prompt, context items, final answer, prompt trim state, and
verification hop/call counts that shaped an admission decision. Evidence:
`core/verification/contracts.py:16`, `core/verification/contracts.py:45`,
`core/verification/registry.py:161`, and
`core/verification/registry.py:194`.

The current follow-up is Verification Provenance Admission Report v1. It adds a
deterministic internal report/schema/validator over the PR `#1884` provenance
metadata and records path coverage for RAG pre-generation, RAG plus
philosophical runtime merge, direct/local answer provenance, runtime-disabled
passthrough, and fail-closed missing-bundle behavior. Evidence:
`docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.json`,
`docs/orchestration/contracts/VERIFICATION_PROVENANCE_ADMISSION_REPORT.schema.json`,
and `scripts/ci/check_verification_provenance_admission_report.py`.

These follow-ups do not change public response DTOs, OpenAPI, DB persistence,
provider selection, frontend, iOS, semantic cache, GraphRAG, Slack/operator
authority, or runtime-serving behavior. Evidence:
`core/insight/philosophical_runtime.py:195`,
`core/insight/philosophical_runtime.py:208`,
`app/services/insight_application_service.py:202`,
`docs/roadmap/BACKLOG_LEDGER.md:2591`, and
`docs/review/PR_1884_FIXED_MAPPING.md`.

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
gate explicitly opens. Evidence: `AGENTS.md:354`,
`docs/roadmap/BACKLOG_LEDGER.md:1964`, and
`docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`.

Evidence Graph E1-E5 reduces the risk of a future cache rollout but does not
approve cache implementation. The gate remains closed until the dedicated
semantic-cache gate document changes its machine-checkable markers through a
reviewed gate-open PR.

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
rg -n -F "Evidence Graph Runtime invariant" AGENTS.md
rg -n "^## Rail Boundaries$" docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md
rg -n "^## Hard Boundaries$" docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md
sed -n '1,121p' docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md | rg -n -F "Rail A | Product AI runtime"
sed -n '1,121p' docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md | rg -n -F "Rail B1 | Advisory wiki / compiled memory"
sed -n '1,121p' docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md | rg -n -F "Rail B2 | Plugin/control-plane"
rg -n -F "ledger-p1-evidence-graph-runtime" docs/roadmap/BACKLOG_LEDGER.md
sed -n '1,121p' docs/roadmap/EVIDENCE_GRAPH_RUNTIME_EPIC.md | rg -n -F "**Canonical backlog anchor:**"
rg -n -F "Semantic cache is forbidden" AGENTS.md
pre-commit run --all-files
make verify
```

Operator note: merge readiness for PR-E0 must rely on current-head PR evidence,
review-thread disposition mapping, and the repo's canonical merge gates.
