# Orchestration Improvements Plan (2026)

**Purpose:** Detailed execution plan for closing architectural gaps identified in orchestration audit and external review.

**Branch:** `worktree/orchestration-improvements`
**Worktree:** `worktrees/orchestration_improvements`
**Canonical:** All work per `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`

---

## 1. Executive Summary

The orchestration audit and external review identified **3 critical gaps** and **4 enhancement tracks**:

| Priority | Item | Status |
|----------|------|--------|
| P1 | Worktree isolation policy | Backlog added |
| P1 | AGENT_KNOWLEDGE_MAP.md (agent → RAG corpus SoT) | Backlog added |
| P2 | Pre-flight auto-verification script | Backlog added |
| P2 | Agent Context Cache | Already in backlog |
| P2 | Orchestration Telemetry | Already in backlog |
| P2 | Agent routing graph | Backlog added |
| P3 | Agent clusters (scaling) | Backlog added |

---

## 2. P1 — Worktree Isolation Policy

### 2.1 Problem

- Agent works in its own worktree; human edits same files → merge conflicts → orchestration chaos.
- No explicit rule: "human cannot edit agent worktree."
- Integration flow exists (PR promotion) but operational law is missing.

### 2.2 Solution

**A) Runbook section** (`AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`):

- Add "Worktree Isolation Policy" section.
- Define worktree states: `active` / `abandoned` / `merged`.
- Allowed human intervention: create new branch from agent branch; do NOT edit in-place inside `worktrees/...`.

**B) AGENTS.md hard rule** (short excerpt):

- "Do not edit files inside `worktrees/...`."
- "Integration only via PR."
- "If human must intervene: new branch from agent branch (not in-place edit)."

### 2.3 DoD

- [ ] Policy section in runbook
- [ ] Hard-rule excerpt in root `AGENTS.md`
- [ ] Example "human intervention via new branch" documented

---

## 3. P1 — AGENT_KNOWLEDGE_MAP.md

### 3.1 Problem

- `AGENT_CONTEXT_MAP` and `AGENT_CAPABILITY_MATRIX` exist.
- `AGENT_CORPUS_MAP` exists in `core/rag/contracts.py` (runtime).
- No docs-level SoT: agent → corpus → RAG index policy.
- RAG retrieval is untrusted; prompt-injection posture needs policy clarity.

### 3.2 Solution

Create `docs/orchestration/AGENT_KNOWLEDGE_MAP.md`:

- **Purpose:** Policy SoT for agent → knowledge corpus → RAG index.
- **Content:**
  - Which agent has access to which corpus.
  - What is indexed / not indexed.
  - Security posture (retrieved content untrusted).
  - Link to `core/rag/contracts.py:AGENT_CORPUS_MAP`.
- **Exit criteria:** Single source for agent→corpus policy; runtime implementation references this doc.

### 3.3 DoD

- [ ] Document created
- [ ] References `AGENT_CORPUS_MAP` policy
- [ ] Boundaries + indexing scope + security posture described

---

## 4. P2 — Pre-flight Auto-verification Script

### 4.1 Problem

- Pre-flight Checklist is manual.
- Coordinator "mentally checks" docs.
- Risk of drift over time.

### 4.2 Solution

Create `scripts/orchestration/check_preflight.py` (or similar):

- Verifies required context files exist.
- Checks repo hygiene (no tracked `worktrees/`).
- Prints PASS/FAIL for coordinator.
- Scoped to orchestration workflow; does not block unrelated tasks.

### 4.3 DoD

- [ ] Script exists
- [ ] Failure mode explicit
- [ ] Documented in runbook or workflow

---

## 5. P2 — Agent Routing Graph

### 5.1 Problem

- Capability matrix exists but is advisory.
- No automatic routing: task → domain classifier → agent set.

### 5.2 Solution

- Define routing graph (task → domains → agents).
- Document in `docs/orchestration/` or extend capability matrix.
- Example: task "optimize API endpoint" → domains: backend, performance → agents: backend-agent, performance-agent, qa-agent.

### 5.3 DoD

- [ ] Routing graph spec or document
- [ ] Linked from coordinator / capability matrix

---

## 6. P2 — Agent Context Cache

### 6.1 Status

Already in BACKLOG_LEDGER (Orchestration Enhancements).

### 6.2 DoD (unchanged)

- Coordinator has explicit caching strategy
- Cache invalidation rules documented

---

## 7. P2 — Orchestration Telemetry

### 7.1 Status

Already in BACKLOG_LEDGER (Orchestration Enhancements).

### 7.2 Metrics (from review)

- `agent_latency`
- `handoff_count`
- `failure_rate`
- `retry_rate`
- `parallel_efficiency`

---

## 8. P3 — Agent Clusters

### 8.1 Problem

- 26 agents; coordinator routes to each.
- At scale (40+ agents) routing becomes unwieldy.

### 8.2 Solution

- Introduce agent clusters: backend, frontend, ml, research, security.
- Coordinator routes to clusters first, then to agents within cluster.
- Document in capability matrix or new doc.

### 8.3 DoD

- [ ] Cluster definitions
- [ ] Routing logic updated (or documented for future)

---

## 9. Execution Order

1. **P1 Worktree isolation** — docs-only PR (runbook + AGENTS.md).
2. **P1 AGENT_KNOWLEDGE_MAP** — docs-only PR (new doc).
3. **P2 Pre-flight script** — tooling PR.
4. **P2 Routing graph** — docs-only PR.
5. **P2 Context cache** — separate PR (coordinator/tooling).
6. **P2 Telemetry** — separate PR (spec + optional recording).
7. **P3 Agent clusters** — future PR (when scaling needed).

---

## 10. Architecture Diagram (Conceptual)

See Mermaid flowchart from orchestration audit (SoT → Protocols → Templates → Execution → Worktree → RAG).

Key flows:
- SoT/Governance → Coordinator
- Protocols (CTX, CAP, MSG) → Coordinator
- Coordinator → Templates → Agent pool → Work Review → Synthesis → DoD
- Coordinator → Worktree Runbook → worktrees/ → PR → Ledger
- Coordinator -.optional.-> RAG (simple_rag, vector_rag, philosophy_pipeline)

## 11. References

- `docs/orchestration/workflow.md`
- `docs/orchestration/AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md`
- `docs/contracts/RAG_CONTRACT.md`
- `core/rag/contracts.py` (AGENT_CORPUS_MAP)
- `docs/roadmap/BACKLOG_LEDGER.md` (Orchestration Enhancements section)

---

**Last updated:** 2026-03-05
**Owner:** @katsiaryna_kavaleuskaya
