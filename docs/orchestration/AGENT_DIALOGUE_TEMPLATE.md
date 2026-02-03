# Agent Dialogue Template

**Purpose:** Formal protocol for multi-agent brainstorming and decision-making.

**Status:** Canonical (PR-634)

---

## Overview

When a task has **multiple valid approaches**, agents engage in a structured dialogue to:
- Explore alternatives
- Identify trade-offs
- Reach consensus (or escalate to coordinator)

**Critical:** Dialogue is time-boxed (≤3 iterations) to prevent infinite debate.

---

## When to Use Dialogue

Use dialogue when:
- Multiple valid design approaches exist
- Trade-offs are unclear
- Cross-domain expertise is needed

Do not use dialogue when:
- A single approach is obvious
- Coordinator already decided
- The task is trivial

---

## Dialogue Hard Limit

**Max iterations:** 3 total (across all agents in the dialogue)

**Escalation path:**
1. Iteration 1–2: brainstorm, propose alternatives, discuss trade-offs
2. Iteration 3: converge or state blockers explicitly
3. After iteration 3: coordinator makes the final decision and closes discussion

No exceptions: if consensus is not reached after 3 iterations:
- Coordinator synthesizes the best available solution
- Documents trade-offs and risks
- Proceeds with an explicit “forced decision” marker

Rationale: prevent infinite LLM debate loops; ensure task completion.

---

## Dialogue Format

### Problem Statement

[What are we solving? What’s unclear?]

**Constraints:**
- [Invariants affected]
- [Quality gates]
- [Deadlines]

**Success criteria:**
- [What would a “good solution” look like?]

---

### Iteration 1: Initial Proposals

#### Agent A (e.g., Architecture)

**Proposal:**
- [Design idea or approach]

**Pros:**
- [What’s good about this approach]

**Cons:**
- [What’s risky or unclear]

**Invariants affected:**
- [Which rules this approach touches]

**Questions for Agent B:**
- [Specific question for B’s domain]

---

#### Agent B (e.g., Bug Hunter)

**Response to Agent A:**
- [Answer to A’s question]

**Proposal:**
- [Alternative or refinement of A’s approach]

**Pros:**
- [What’s good]

**Cons:**
- [What’s risky]

**Testing strategy:**
- [How to verify this approach]

**Questions for Agent C (if 3+ agents):**
- [Specific question for C’s domain]

---

### Iteration 2: Refinement

#### Agent A (refined)

**Response to Agent B:**
- [Address B’s concerns]

**Updated proposal:**
- [Refined approach incorporating B’s feedback]

**Trade-offs accepted:**
- [What we’re willing to sacrifice]

**Remaining questions:**
- [Unresolved blockers]

---

#### Agent B (refined)

**Response to Agent A:**
- [Address A’s updates]

**Convergence check:**
- ✅ Agreement reached: [Describe consensus]
- ⏳ Still discussing: [What’s blocking consensus]
- ❌ Disagreement: [Fundamental conflict]

---

### Iteration 3: Final Decision or Escalation

If consensus reached:

#### Agent A + Agent B (joint)

**Final approach:**
- [Combined solution]

**Rationale:**
- [Why this approach was chosen]

**Trade-offs:**
- [What we accept]

**Implementation plan:**
- [Next steps]

---

If consensus not reached:

#### Coordinator (forced decision)

**Escalation reason:**
- [Why agents could not converge]

**Final decision:**
- [Coordinator’s choice]

**Rationale:**
- [Why this option chosen despite disagreement]

**Risks accepted:**
- [Known trade-offs]

**Follow-up:**
- [Review plan if decision proves wrong]

**Forced decision marker:** ⚠️ Coordinator override (iteration 3 limit)

---

## Multi-Agent Dialogue (3+ agents)

When 3+ agents participate:

Iteration structure:
1. Round 1: each agent proposes (parallel)
2. Round 2: each agent responds to others (sequential)
3. Round 3: convergence or escalation

**Critical:** still ≤3 total iterations (not 3 per agent).

---

## Example: RAG Implementation Dialogue

### Problem Statement

Should we use a vector DB (Pinecone) or local embeddings (ChromaDB) for RAG?

**Constraints:**
- Must work offline (optional requirement)
- Budget: prefer low-cost
- Latency: <500ms query time

**Success criteria:**
- Accurate retrieval (≥80% relevance)
- Maintainable (no vendor lock-in)

---

### Iteration 1

#### Architecture Specialist

**Proposal:** Use ChromaDB (local embeddings)

**Pros:**
- No API costs
- Works offline
- No vendor lock-in

**Cons:**
- Slower than Pinecone
- Need to manage embedding model

**Questions for AI Innovation:**
- Can ChromaDB meet <500ms latency?

---

#### AI Innovation Specialist

**Response to Architecture:**
- ChromaDB can meet <500ms with cached embeddings (tested)

**Proposal:** Hybrid approach — ChromaDB for dev, Pinecone for prod

**Pros:**
- Best of both worlds
- Dev independence
- Prod performance

**Cons:**
- Dual config complexity
- Testing both paths

**Questions for Security:**
- Data residency concerns with Pinecone?

---

#### Security Auditor

**Response to AI Innovation:**
- Pinecone has EU/US data centers (acceptable)
- But: API key management risk

**Proposal:** ChromaDB only (avoid external dependency)

**Pros:**
- No data exfiltration risk
- Simpler security model

**Cons:**
- Performance trade-off

---

### Iteration 2

#### Coordinator Synthesis

**Convergence check:** ⏳ still discussing (performance vs security)

Refined question:
- Can we meet latency with ChromaDB + optimization?

#### AI Innovation (test results)

**Benchmark:**
- ChromaDB + LRU cache = 350ms avg latency ✅
- Meets requirement

**Recommendation:** ChromaDB only (no hybrid needed)

---

### Iteration 3

#### All Agents (consensus)

**Final approach:** ChromaDB (local embeddings)

**Rationale:**
- Meets latency requirement (350ms < 500ms)
- No API costs
- No vendor lock-in
- Simpler security model

**Trade-offs accepted:**
- Slightly slower than Pinecone (acceptable)
- Need to manage embedding model (acceptable)

**Implementation plan:**
1. Install ChromaDB
2. Implement embedding cache
3. Benchmark with real data
4. Document rollback to Pinecone if latency degrades

---

## Verification Checklist

Before starting dialogue, verify:
- [ ] Problem is well-defined
- [ ] Multiple valid approaches exist
- [ ] Trade-offs are unclear
- [ ] All relevant agents identified

If any item is unclear, clarify before starting.

---

## Related Documentation

- Handoff Protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Parallel Work: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`
- Coordinator: `.cursor/agents/agent-coordinator.md`

---

**Last updated:** 2026-02-03 (PR-634)
**Status:** Canonical
