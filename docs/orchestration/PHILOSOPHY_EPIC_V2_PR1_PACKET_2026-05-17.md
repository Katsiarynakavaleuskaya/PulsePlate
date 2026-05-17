# Philosophy Epic V2 PR-1 Packet

**Date:** 2026-05-17
**Status:** Open governance packet (admission contract only)
**Branch:** `codex/philosophy-epic-v2-pr1-admission-contract`
**Prerequisite:** PR #1742 merged (`cb1db8b40`) — SC-G5 backend selection contract

## Goal

Land Philosophy Epic V2 PR-1 as a gate-closed philosophical admission contract that
defines which philosophical request classes may enter a **future** semantic-cache
path. PR-1 does not open the semantic-cache gate, does not duplicate SC-G5 backend
selection, and does not add runtime serving, Redis/GPTCache, embeddings, or
`/insight` cache wiring.

## Coordinator Role Order

1. `agent-coordinator` — scope, sequencing after #1742, DoD.
2. `architecture-specialist` — single SoT; reference SC-G5 without duplication.
3. `philosophy-agent` — wellness-safe admission language and blocked surfaces.
4. `rag-systems-agent` — semantic-cache gate alignment and verification-bundle boundaries.
5. `logic-agent` — guardable admission classes and verification-bundle requirements.
6. `security-auditor` — required because this PR touches `scripts/ci/**` governance.
7. Post-open mandatory pass: `qa-engineer-agent -> bug-hunter`.

Role-agent findings are closure-blocking for readiness: every P0/P1/P2 finding
from premortem, architecture, philosophy, RAG, logic, security, QA, and
bug-hunter review must be `FIXED`, `NOT-A-BUG`, or `DEFERRED` with backlog
evidence before any merge-ready claim.

## IN / OUT

### IN

- `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`
- `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.schema.json`
- `scripts/ci/check_semantic_cache_gate.py` validators for admission contract
- `scripts/ci/check_docs_phase1_gates.py` wiring
- `tests/test_philosophy_semantic_cache_admission_contract.py`
- Gate plan reference paragraph in `docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md`
- Backlog: close PR-0 packet item; add PR-1 tracking entry

### OUT

- Semantic-cache runtime, storage, providers, embeddings, vector search
- Redis/GPTCache imports, clients, connection strings, probes
- OpenAPI, DB, frontend, iOS, FitChef/CBT runtime changes
- Changes to `core/insight/philosophical_runtime.py` behavior
- Duplication of SC-G5 candidate labels or ranking matrix

## Validation Plan

```bash
python3 scripts/orchestration/check_preflight.py
python3 scripts/orchestration/check_agent_consistency.py
python3 scripts/ci/check_semantic_cache_gate.py
python3 -m pytest -q tests/test_philosophy_semantic_cache_admission_contract.py
python3 scripts/ci/check_docs_phase1_gates.py --files \
  docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md \
  docs/roadmap/PulsePlate_Semantic_Cache_Gate_and_Plan.md
pre-commit run --all-files
make validate-changed
```

## Premortem Finding Disposition

- `FIXED`: validator scan scope now distinguishes mention of forbidden claim
  classes from asserted live semantic-cache claims.
- `FIXED`: admission contract uses exact `No Redis imports`, `No GPTCache
  imports`, and `No embeddings` guard wording.
- `FIXED`: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission`
  exists and PR-0 is closed by reference to PR #1744.
- `FIXED`: wellness-only scope, falsifiability criteria, risk-class machine
  slug wording, and SC-G5 SHA update procedure are recorded in the contract.
- `NOT-A-BUG`: keeping `cb1db8b40` as a schema/checker const is intentional
  traceability for the PR #1742 SC-G5 merge anchor; if the anchor changes, the
  contract names the coordinated update set.

## Merge Readiness (Pre-Open)

- [ ] PR body includes `## Discussion Thread Pass`, `### Fixed in Commit Mapping`, `## Merge Readiness`
- [ ] `docs/review/PR_<N>_FIXED_MAPPING.md` created after PR number assigned
- [ ] Canonical CI current-head parity before merge-ready claim
- [ ] No semantic-cache gate markers changed to open

## Deferred / Follow-ups

- PR-A analytical module V2 — `docs/orchestration/PHILOSOPHY_EPIC_V2_PR0_PACKET_2026-05-13.md`
- Meaning-as-use cache key enrichment — only after gate-open PR + admission re-check
- Ledger: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-philosophy-epic-v2-pr1-admission`

## References

- PR-0 packet: `docs/orchestration/PHILOSOPHY_EPIC_V2_PR0_PACKET_2026-05-13.md` (merged #1744)
- SC-G5 contract: `docs/orchestration/contracts/SEMANTIC_CACHE_BACKEND_SELECTION_CONTRACT.md`
- Admission contract: `docs/orchestration/contracts/PHILOSOPHY_SEMANTIC_CACHE_ADMISSION_CONTRACT.md`
