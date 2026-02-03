# Parallel Work Protocol

**Purpose:** Protocol for coordinating multiple agents working in parallel.

**Status:** Canonical (PR-634)

---

## Overview

When a task has independent subtasks, agents can work in parallel to:
- Reduce total completion time
- Leverage multiple domain experts simultaneously
- Maintain quality through structured sync points

**Critical:** Parallel work requires an explicit dependency graph and sync points.

---

## When to Parallelize

Use parallel work when:
- Subtasks are independent (no blocking dependencies)
- Interfaces between tracks are clear
- Multiple agents are available

Do not parallelize when:
- Subtasks are sequential (A must finish before B starts)
- A single agent can complete faster than coordination overhead
- Interfaces are unclear (high integration conflict risk)

---

## Work Split Process

### Step 1: Coordinator defines tracks

Use this track definition format:

```markdown
**Track [N]: [Agent(s)]**
- **Goal:** [What this track produces]
- **Deliverable:** [Specific output]
- **Files:** [List of files modified/created]
- **Sync point:** [When this track must be complete]
- **Dependencies:** [What this track needs from other tracks]
```

---

### Step 2: Identify sync points

Sync Point = checkpoint where tracks converge.

Examples:
- SP1: Backend API ready → Frontend can generate types
- SP2: Backend + Frontend ready → Tests can verify integration
- SP3: All tracks complete → Coordinator synthesizes into PR

---

### Step 3: Build dependency graph

Visual representation:

```text
Track 1 (Backend)
 ↓
SP1 (API ready)
 ↓
Track 2 (Frontend) ← depends on SP1
 ↓
SP2 (Both ready)
 ↓
Track 3 (Tests) ← depends on SP2
 ↓
SP3 (All done) → Coordinator synthesis
```

---

## Sync Point Template

Use this template at each sync point:

```markdown
## Sync Point [N]: [Name]

**Status:** ✅ Ready | ⏳ In Progress | ❌ Blocked

**Deliverables from this sync point:**
- [ ] [Item 1 — which track produces this]
- [ ] [Item 2 — which track produces this]

**Verification:**
- [ ] [Check 1 — how to verify deliverable]
- [ ] [Check 2 — how to verify deliverable]

**Blockers (if any):**
- [Description of what’s blocking]
- [Which track is blocked]
- [Resolution plan]

**Next agent(s):**
- [Which agent(s) can proceed after this sync point]

**Coordinator decision (if blocked):**
- [Coordinator’s plan to unblock or resequence]
```

---

## Example: RAG Endpoint (3 Tracks)

### Track Definitions

#### Track 1: Backend (Architecture + AI Innovation)

- **Goal:** Implement RAG query endpoint
- **Deliverable:** `/api/v1/vip/rag/query` with response model
- **Files:** `app/routers/rag.py`, `core/rag/query.py`, `app/schemas/rag.py`
- **Sync point:** SP1 (OpenAPI schema ready)
- **Dependencies:** None (starts immediately)

---

#### Track 2: Frontend (Creative Designer)

- **Goal:** RAG query UI component
- **Deliverable:** `RagQueryView.tsx` with loading/error states
- **Files:** `frontend/src/components/RagQueryView.tsx`
- **Sync point:** SP2 (UI ready for integration)
- **Dependencies:** SP1 (needs OpenAPI types)

---

#### Track 3: Tests (Bug Hunter)

- **Goal:** Contract tests for RAG endpoint
- **Deliverable:** `tests/test_rag_contract.py` (green + coverage ≥97%)
- **Files:** `tests/test_rag_contract.py`
- **Sync point:** SP3 (all tests green)
- **Dependencies:** SP1 + SP2 (needs backend + frontend ready)

---

### Dependency Graph

```text
Track 1 (Backend: Architecture + AI Innovation)
 ↓
SP1 (OpenAPI schema ready)
 ├─ Deliverable: openapi.json updated
 ├─ Verification: `make openapi-check` passes
 └─ Next: Track 2 can start

Track 2 (Frontend: Creative Designer)
 ├─ Depends on: SP1
 ↓
SP2 (Frontend UI ready)
 ├─ Deliverable: RagQueryView.tsx component
 ├─ Verification: `npm run build` passes
 └─ Next: Track 3 can start

Track 3 (Tests: Bug Hunter)
 ├─ Depends on: SP1 + SP2
 ↓
SP3 (All tests green)
 ├─ Deliverable: tests/test_rag_contract.py
 ├─ Verification: `pytest -v tests/test_rag_contract.py` green + coverage ≥97%
 └─ Next: Coordinator synthesis

Coordinator Synthesis
 ├─ Depends on: SP3
 ├─ Synthesizes: Backend + Frontend + Tests
 └─ Produces: PR-ready changeset
```

---

### Sync Point Execution

#### SP1: OpenAPI Schema Ready

**Status:** ✅ Ready

**Deliverables:**
- [x] `openapi.json` updated with `/api/v1/vip/rag/query`
- [x] Response model: `RagQueryResponse` in schema

**Verification:**
- [x] `make openapi-check` passes (determinism OK)
- [x] `openapi.json` contains `/api/v1/vip/rag/query` path

**Blockers:** None

**Next agent:** Creative Designer (Track 2 can start)

---

#### SP2: Frontend UI Ready

**Status:** ✅ Ready

**Deliverables:**
- [x] `RagQueryView.tsx` component implemented
- [x] Loading/error states handled
- [x] TypeScript types generated from OpenAPI

**Verification:**
- [x] `npm run build` passes (no TS errors)
- [x] Manual test: component renders

**Blockers:** None

**Next agent:** Bug Hunter (Track 3 can start)

---

#### SP3: All Tests Green

**Status:** ✅ Ready

**Deliverables:**
- [x] `tests/test_rag_contract.py` (contract tests)
- [x] pytest green (all tests pass)
- [x] Coverage ≥97% on new code

**Verification:**
- [x] `pytest -v tests/test_rag_contract.py` green
- [x] `make cov-check` passes (coverage ≥97%)

**Blockers:** None

**Next agent:** Coordinator (synthesis)

---

## Blocked Sync Point Example

### SP2: Frontend UI Ready

**Status:** ❌ Blocked

**Deliverables:**
- [ ] `RagQueryView.tsx` component implemented
- [x] Loading/error states handled
- [ ] TypeScript types generated from OpenAPI

**Verification:**
- [ ] `npm run build` passes (currently failing)
- [ ] Manual test: component renders

**Blockers:**
- TypeScript error: `RagQueryResponse` type missing from schema.ts
- Root cause: OpenAPI schema missing response model details
- Blocked track: Track 2 (Frontend)

**Coordinator decision:**
1. Notify Architecture (Track 1): fix response model in OpenAPI
2. Track 2 waits for SP1 re-verification
3. Track 3 cannot start until SP2 is unblocked

---

## Verification Checklist

Before starting parallel work, verify:
- [ ] All tracks have clear deliverables
- [ ] All sync points identified
- [ ] Dependency graph is acyclic (no circular dependencies)
- [ ] Each track has assigned agent(s)
- [ ] Interfaces between tracks are clear

If any item is unclear, resequence or simplify.

---

## Related Documentation

- Handoff Protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Dialogue Template: `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md`
- Coordinator: `.cursor/agents/agent-coordinator.md`

---

**Last updated:** 2026-02-03 (PR-634)
**Status:** Canonical
