# Dev Orchestrator Workflow (Canonical)

**Purpose:** Canonical workflow for starting and completing any development task using agent coordination.

**Status:** dev-only, no runtime impact

---

## Workflow Overview

```text
Task
 → Task Analysis
 → Agent Assignment
 → Work Review
 → Synthesis
 → DoD
```

---

## Step 1: Task Analysis

**When:** At the start of any new task

**Action:** Use `agent-coordinator` to analyze the task

**Template:** See `docs/orchestration/task_analysis.template.md`

**Output:**
- Domain(s) identified
- Complexity assessed
- Priority assigned (P0/P1/P2)
- Agent(s) assigned
- Expected outcome defined

---

## Step 2: Agent Assignment

**When:** After Task Analysis

**Action:** Coordinator routes to appropriate agent(s)

**Patterns:**
- **Single-agent:** Direct assignment to best-fit agent
- **Multi-agent:** Sequential or parallel workflow
- **Dependencies:** Clear handoff points

**Reference:** See `.cursor/agents/agent-coordinator.md` for agent capabilities mapping

---

## Step 3: Work Review

**When:** After agent(s) complete work

**Action:** Coordinator reviews agent outputs

**Template:** See `docs/orchestration/work_review.template.md`

**Checks:**
- Requirements met
- Project conventions followed (AGENTS.md, guard tests)
- Quality gates pass (see `RUNBOOK_AGENT.md` Quality Gates section)
- No conflicts with other work

---

## Step 4: Synthesis

**When:** After Work Review (especially for multi-agent tasks)

**Action:** Coordinator synthesizes outputs into coherent solution

**Template:** See `docs/orchestration/synthesis.template.md`

**Output:**
- Final decision
- Rationale
- Follow-ups (if any)

---

## Step 5: DoD (Definition of Done)

**When:** Before PR merge

**Action:** Verify all DoD criteria are met

**Template:** See `docs/orchestration/dod.template.md`

**Required:**
- Scope respected
- Quality gates pass (see `RUNBOOK_AGENT.md` Quality Gates section)
- Documentation updated (if needed)
- Postponed items recorded in `BACKLOG_LEDGER.md`

---

## Integration Points

### AGENTS.md
- **Coordinator-first rule:** See canonical definition in `AGENTS.md` (Agent Coordination section)
- This workflow assumes the canonical Coordinator-First Rule

### RUNBOOK_AGENT.md
- Quick reference for starting tasks
- Links to orchestration templates
- Quality gates (canonical): See `RUNBOOK_AGENT.md` (Quality Gates section)

### BACKLOG_LEDGER.md
- Postponed items must be recorded here
- See `docs/roadmap/BACKLOG_LEDGER.md`

---

## Key Principles

1. **Coordinator-first:** See `AGENTS.md` (Agent Coordination section) for canonical rule
2. **Quality gates:** See `RUNBOOK_AGENT.md` (Quality Gates section) for canonical checklist
3. **Documentation:** Update AGENTS.md/RUNBOOK if workflow changes
4. **Postponed items:** Always record in BACKLOG_LEDGER
5. **Dev-only:** This workflow is for development, not runtime product

---

**Last updated:** 2026-01-23 (PR-565)
**Related:** `.cursor/agents/agent-coordinator.md`, `AGENTS.md`, `RUNBOOK_AGENT.md`
