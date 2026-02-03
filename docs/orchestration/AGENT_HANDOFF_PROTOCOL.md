# Agent Handoff Protocol

**Purpose:** Formal protocol for delegating tasks between agents.

**Status:** Canonical (PR-634)

---

## Overview

When a task requires multiple agents, **explicit handoffs** ensure:
- No context loss
- Clear deliverables
- Expected returns

**Critical:** Handoffs must be **explicit** and **structured** (not informal).

---

## When to Use Handoff

Use handoff when:
- Task spans multiple domains (e.g., backend + frontend)
- Agent lacks expertise (e.g., Architecture → AI Innovation for RAG)
- Review needed (e.g., Bug Hunter → Security for exploit analysis)

Do not use handoff when:
- A single agent can complete the task end-to-end
- The task is trivial coordination (use Synthesis instead)

---

## Handoff Format

### Step 1: Agent A initiates handoff

```markdown
## Handoff to [Agent B]

**Context:**
- **Task:** [Original task description]
- **Work completed by Agent A:** [Summary]
- **Dependencies:** [What B needs to know]
- **Files involved:** [List of files]
- **Constraints:** [Invariants, quality gates, deadlines]

**What Agent B needs to do:**
- [Specific subtask for B]
- [Expected deliverable]
- [Format/structure requirements]

**Return to Agent A:**
- [What A expects back from B]
- [Format/structure of return]
- [Any specific checks A will perform]

**Questions for Agent B (optional):**
- [Clarifications if needed]
```

---

### Step 2: Agent B acknowledges handoff

```markdown
## Handoff Received from [Agent A]

**Understood:**
- Task: [Confirm understanding of subtask]
- Dependencies: [Confirm context loaded]
- Deliverable: [Confirm what A expects]

**Questions (if any):**
- [Clarifications needed before starting]

**Starting work...**
```

**Critical:** Agent B must confirm understanding before starting. If confused, ask immediately.

---

### Step 3: Agent B completes work and returns

```markdown
## Work Complete → [Agent A]

**Deliverable:**
- [What was produced — code, docs, tests, etc.]
- [Location: file paths or artifact links]

**Quality checks performed:**
- [What B verified — tests, lint, coverage, etc.]

**Issues encountered (if any):**
- [Blockers, conflicts, edge cases]
- [Workarounds applied]

**Next steps for Agent A:**
- [What A should do with this output]
- [Any integration points]

**Questions for Agent A (if any):**
- [Clarifications on return expectations]
```

---

## Anti-Patterns (DON'T DO THIS)

### ❌ Bad Handoff Example

```markdown
Hey Bug Hunter, check the tests.
```

Problems:
- No context (which tests? why?)
- No deliverable (what should Bug Hunter produce?)
- No return expectation (what does the original agent expect back?)

---

### ✅ Good Handoff Example

```markdown
## Handoff to Bug Hunter

**Context:**
- Task: Implement RAG endpoint (`/api/v1/vip/rag/query`)
- Work completed: RAG endpoint implemented, manual testing passed
- Dependencies: OpenAPI schema updated, response model defined
- Files involved: `app/routers/rag.py`, `core/rag/query.py`
- Constraints: Coverage ≥97%, mypy strict mode

**What Bug Hunter needs to do:**
- Write contract tests for RAG endpoint
- Verify request/response schema matches OpenAPI
- Verify error handling (401, 424, 500)
- Verify coverage ≥97% on new code

**Return to Architecture:**
- Test file: `tests/test_rag_contract.py`
- pytest output (green + coverage report)
- Any failures or edge cases found

**Questions for Bug Hunter:**
- Do you need example request/response fixtures?
```

Why this is good:
- Clear context (what was done, what’s needed)
- Specific deliverable (test file + pytest output)
- Explicit return expectation
- Constraints documented (coverage ≥97%)

---

## Multi-Agent Handoff (Chain)

When a task requires 3+ agents, use sequential handoffs:

```text
Coordinator
 ↓ Handoff
Architecture (design API)
 ↓ Handoff
Bug Hunter (write tests)
 ↓ Handoff
Security (audit)
 ↓ Return
Coordinator (synthesis)
```

**Critical:** Each handoff must be explicit (use the template above).

---

## Parallel Handoff (Tracks)

When subtasks are independent, use parallel tracks:

```text
Coordinator
 ├─ Handoff → Architecture (backend)
 ├─ Handoff → Creative Designer (frontend)
 └─ Handoff → Bug Hunter (tests)

[Sync Point: All tracks complete]

Coordinator (synthesis)
```

See `PARALLEL_WORK_PROTOCOL.md` for parallel execution rules.

---

## Verification Checklist

Before accepting a handoff, the receiving agent must verify:
- [ ] Context is clear (understand what was done)
- [ ] Dependencies identified (what is needed)
- [ ] Deliverable defined (what to produce)
- [ ] Return expectation clear (what to send back)
- [ ] Constraints known (quality gates, deadlines)

If any item is unclear, ask questions immediately.

---

## Related Documentation

- Parallel Work: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`
- Dialogue: `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md`
- Context Map: `docs/orchestration/AGENT_CONTEXT_MAP.md`
- Coordinator: `.cursor/agents/agent-coordinator.md`

---

**Last updated:** 2026-02-03 (PR-634)
**Status:** Canonical
