# Task Analysis: RAG contract implementation

**Copy this template for each new task.**

---

## Task Analysis

**Task:** Implement RAG contract types, constants, and Insight response fields per BACKLOG_LEDGER entry "P1: RAG contract implementation" (sources[], confidence, budget constants). Add RAGChunk/RAGContext in core/rag, rag_constants.py, and extend Insight response schema with sources, confidence, rag_used, hops, latency_ms per docs/contracts/RAG_CONTRACT.md.

**Domain(s):** AI/ML, Architecture

**Complexity:** Moderate

**Priority:** P1

- **Priority track (P0-A / P0-B / P1):** P1 _(see [AGENTS.md](../../AGENTS.md) — Release readiness priorities)_

**Expected Outcome:**
- RAGChunk and RAGContext in core/rag/contracts.py; budget constants in core/rag/rag_constants.py.
- InsightResponse (or extended schema) includes sources, confidence, rag_used, hops, latency_ms.
- Deterministic tests for new types, constants, and response fields; `make verify` passes.
- BACKLOG_LEDGER DoD 1761 satisfied (or split across two PRs with clear DoD per PR).

**Invariants Affected:**
- [ ] One BMI Engine
- [ ] Thin HTTP Adapter Policy
- [x] Layer Separation (core/rag domain vs app schemas/routers)
- [x] Contract-First (RAG_CONTRACT.md is SoT)

**Domain hints (pick if relevant; links-only):**
- `core/rag/*`: RAG contract types and constants (see RAG_CONTRACT.md, BACKLOG_LEDGER 1761)
- `app/routers/*`, `legacy_app.py`: OpenAPI determinism, response_model, insight endpoint (see AGENTS.md)

**Risks:**
1. Breaking existing insight callers if response schema changes without backward compatibility — mitigate: extend schema with optional fields; default rag_used=false, sources=[], confidence=null when RAG not used.

**Proposed Approach:**
1. **PR-1 (this scope):** Add core/rag/contracts.py (RAGChunk, RAGContext) and core/rag/rag_constants.py; add tests in tests/test_rag_contracts.py. Optionally extend retrieve_context in core/rag/simple_rag.py to return RAGContext with backward-compatible overload or default args. No app/schemas or endpoint changes in PR-1.
2. **PR-2 (follow-up):** Extend Insight response schema (app/schemas or legacy_app InsightResponse) with sources, confidence, rag_used, hops, latency_ms; wire insight endpoint to populate from RAGContext when rag_used=true; add tests for new response fields; run make openapi and commit artifacts.
3. Decision: **Two PRs** — one focus per PR (audit §9.2). PR-1 = core/rag types + constants; PR-2 = API response schema + endpoint.

**Agent Assignment:**
- **Primary:** rag-systems-agent — contract compliance (RAG_CONTRACT §3–§4), safety and recursion budget.
- **Secondary:** ai-app-architect — RAG placement in pipeline, feature flags, OpenAPI/app boundary; backend-engineer — response schema and router wiring when doing PR-2.
- **Dependencies:** PR 928 merged (docs-only audit and RAG contract doc on main).

**Constraints:**
- One focus per PR; no mixing core/rag types with app-layer schema in same PR if splitting.
- Pre-commit and make verify required before push; OpenAPI determinism if response schema changes (PR-2).
- Insight endpoint remains tier-gated and rate-limited; no new endpoints in this task.

---

## File list (approved before branch)

| File | Action |
|------|--------|
| `core/rag/contracts.py` | create or update — RAGChunk, RAGContext (RAG_CONTRACT §3) |
| `core/rag/rag_constants.py` | create or update — MAX_RAG_HOPS, MAX_CHUNKS_PER_HOP, MAX_SOURCES_IN_RESPONSE, RAG_PIPELINE_TIMEOUT_SEC, MIN_CHUNK_SCORE, MAX_CHUNK_SIZE_CHARS (§4) |
| `core/rag/simple_rag.py` | optional in PR-1 — extend retrieve_context (default args) to return RAGContext, keep backward compat |
| `tests/test_rag_contracts.py` | create or update — tests for RAGChunk, RAGContext, constants |
| _(PR-2)_ `app/schemas/*` or Insight response definition | extend — sources, confidence, rag_used, hops, latency_ms |
| _(PR-2)_ `legacy_app.py` or app/routers (insight) | update — use extended schema, fill from RAGContext when rag_used=true |
| _(PR-2)_ `tests/*` (insight/rag response) | add — tests for new response fields |

**One vs two PRs:** Two. PR-1 = core/rag (contracts + constants + tests). PR-2 = Insight response schema + endpoint + openapi artifacts.

---

**Agent convening:** rag-systems-agent, ai-app-architect, backend-engineer — not invoked (mcp_task model unavailable). Proceeding with RAG_CONTRACT.md and AGENTS.md as authority.

**Analysis by:** agent-coordinator (fallback: manual per plan)
**Date:** 2026-02-27
