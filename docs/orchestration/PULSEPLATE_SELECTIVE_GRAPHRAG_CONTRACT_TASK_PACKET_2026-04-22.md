# PulsePlate Selective GraphRAG Contract Task Packet

**Date:** 2026-04-22 (`America/New_York`)
**Mode:** coordinator-first, worktree-isolated, docs-only ADR lane
**Worktree:** `worktrees/selective-graphrag-contract`
**Branch:** `docs/selective-graphrag-contract`
**Ledger:** [`ledger-p1-rag-release-gates-lane`](../roadmap/BACKLOG_LEDGER.md#ledger-p1-rag-release-gates-lane)

## Decision Question

How should PulsePlate define a selective GraphRAG contract for nutrition
reasoning without widening into runtime GraphRAG, semantic cache, provider
behavior, or a second evaluation rail?

## Summary

This lane is a narrow docs/ADR follow-up on the canonical evidence and
evaluation spine.

It introduces one bounded architecture contract that says:

- where GraphRAG is justified
- where GraphRAG is not justified
- how graph work stays subordinate to canonical release-gates and companion
  RAGAS boundaries

It does not implement graph retrieval, graph evaluation, or semantic cache.

## Success Criteria

1. A committed ADR defines selective GraphRAG as a bounded future reasoning
   surface, not a default retrieval strategy.
2. The ADR is the source of truth for the approved future graph use cases,
   exclusions, and starter graph boundary so this packet does not become a
   competing copy of that contract.
3. The ADR freezes starter graph node/edge boundaries and ties them back to
   existing PulsePlate evidence surfaces.
4. The ADR explicitly subordinates graph work to the canonical release-gates
   lane and the companion report-only RAGAS lane.
5. The lane introduces no runtime/request-path/provider/semantic-cache changes.

## Role Order (mandatory)

Execute in this order for the lane:

1. `agent-coordinator`
2. `architecture-specialist`
3. `data-scientist-agent`
4. `ai-innovation-specialist`
5. `backend-engineer`

Privileged-surface reviewer:

1. `security-auditor`

Post-open mandatory review lane:

1. `qa-engineer-agent`
2. `bug-hunter`

## Skill / Plugin Routing

Required skills:

- `pulseplate-workflow`
- `docs-sync`
- `pulseplate-gates`

Recommended skills:

- `agents-md`
- `bug-triage`

Required plugin surfaces:

- `GitHub` for live PR/check/review truth
- `CodeRabbit` for post-open review truth

Optional read-only plugin surfaces only if the ADR needs fresh external
citations beyond the local repo corpus:

- `Hugging Face`
- `Life Science Research`

Explicitly out of scope:

- `Computer Use`
- `Figma`
- `Jam`
- `Cloudflare`
- `build-ios-apps`
- `build-macos-apps`
- `build-web-apps`
- `Expo`

## Scope

### In scope

- `docs/architecture/ADR_SELECTIVE_GRAPHRAG_CONTRACT_2026-04-22.md`
- this packet
- `docs/review/PR_<N>_FIXED_MAPPING.md` after PR open

### Out of scope

- `app/**`
- `core/**`
- `llm.py`
- `evals/ragas/**`
- `scripts/evals/**`
- runtime/provider/request-path changes
- semantic cache implementation or gate widening
- GraphRAG runtime rollout
- graph-specific thresholds, runners, or artifact schema
- a second evaluation rail

## Architecture Decision

### Canonical ownership

- `docs/evals/PULSEPLATE_RAG_RELEASE_GATES.md` remains the canonical owner of:
  - threshold vocabulary
  - gate checks
  - release decisions
  - `PASS` / `NO-GO` semantics
- `docs/evals/RAGAS_SETUP.md` remains the companion report-only surface for
  local RAGAS metrics

### Selective GraphRAG boundary

The canonical selective-use and exclusion lists live in the ADR:
`docs/architecture/ADR_SELECTIVE_GRAPHRAG_CONTRACT_2026-04-22.md`
(`Decision` and `Starter Graph Boundary`). This packet adopts that ADR as the
source of truth instead of restating the full list here. Operationally, that
means only a narrow future reasoning subset is graph-eligible, while default
retrieval and ordinary product flows remain explicitly non-graph in this lane.

### Provenance and fail-closed contract

Future graph work must:

- keep source fingerprints and citations first-class
- stay subordinate to evidence selection and safety guards
- avoid treating graph structure as canonical truth by itself
- inherit repo fail-closed behavior
- avoid bypassing current runtime preparation/orchestration seams or widening
  `app/**`, `core/**`, `llm.py`, route, DTO, or OpenAPI truth unless a later
  separately approved bounded PR opens that scope

## Risks

- accidental wording that reads like a runtime roadmap instead of a bounded ADR
- accidental creation of a second graph-eval rail
- semantic-cache drift through loosely worded "future optimization" language
- review noise from unnecessary edits outside the ADR and packet

## Mitigations

- keep the diff to ADR + packet only unless review feedback proves otherwise
- state explicitly that graph evaluation is deferred follow-up only
- state explicitly that semantic cache remains governed by its own gate
- keep release-gates and companion RAGAS ownership unchanged

## Validation

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
pre-commit run --all-files
make validate-min
```

Before any merge-ready claim:

```bash
make verify
```

## DoD

- ADR is committed and uses repo ADR style
- packet is committed and names the lane role order and boundaries
- graph work is explicitly selective and deferred from runtime
- semantic cache remains deferred-only
- no second evaluation rail is implied
- post-open `qa-engineer-agent -> bug-hunter` lane is executed after PR open
