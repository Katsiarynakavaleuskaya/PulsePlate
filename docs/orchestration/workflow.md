# Dev Orchestrator Workflow (Canonical)

**Purpose:** Canonical workflow for starting and completing any development task using agent coordination.

**Status:** dev-only, no runtime impact

---

## Canonical References (single source of truth)

- **Coordinator-first rule + definition of "task":** see `AGENTS.md` (Agent Coordination section)
- **Quality gates / thresholds / required commands:** see `AGENTS.md` (Quality Gates section)
- **Operational runbook:** see `RUNBOOK_AGENT.md` (Quality Gates section)
- **Orchestration protocols:** see `docs/orchestration/AGENT_*.md` (context, capability, handoff, dialogue, parallel)

---

## Workflow Overview

```text
Task
 → Task Analysis
 → Agent Assignment
 → Work Review
 → Post-flight Verification
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

**Pre-flight Checklist (SoT):** See “Canonical Pre-flight Checklist (SoT)” below (mandatory).

---

## Canonical Pre-flight Checklist (SoT)

**Канон:** этот чек-лист — единственный source of truth для “Pre-flight Checklist”.
Все остальные документы **не дублируют пункты**, а **ссылаются сюда**.

(EN: This checklist is the single source of truth; other docs must link here.)

### Pre-flight Checklist

#### 1) Context loading
- [ ] Загружен root `AGENTS.md` (инварианты, quality gates, запреты)
- [ ] Загружен `RUNBOOK_AGENT.md` (операционные команды/проверки)
- [ ] Определены затронутые модули (core/app/frontend/ios/tests/…)
- [ ] Загружены `AGENTS.md` для **каждого** затронутого модуля

#### 2) Contract docs (если меняется API/схемы/tiers)
- [ ] Загружены релевантные contract-docs (например `API_CANONICAL_MAP`, `PRODUCT_TIER_MAP`,
  `OPENAPI_VISIBILITY_MATRIX`, `soft_paywall`)

#### 3) Quality gates
- [ ] Ясно какие проверки обязательны (pytest/coverage/mypy/lint/openapi determinism/guards)
- [ ] Список guard-тестов для задачи понятен

#### 4) Routing readiness
- [ ] Назначен primary agent
- [ ] Назначены secondary agents (если multi-domain)
- [ ] Проставлены зависимости / handoff / sync points (если multi-agent)

**Stop condition:** если есть хоть один незакрытый пункт — execution запрещён.

---

## Step 2: Agent Assignment

**When:** After Task Analysis

**Action:** Coordinator routes to appropriate agent(s)

**Patterns:**
- **Single-agent:** Direct assignment to best-fit agent
- **Multi-agent:** Sequential or parallel workflow
- **Dependencies:** Clear handoff points

**Reference:** See `AGENTS.md` for canonical agent coordination rules and links to orchestration templates.

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

## Step 4: Post-flight Verification (NEW)

**When:** After Work Review, before Synthesis

**Action:** Coordinator verifies all execution requirements were met.

**Verification checklist:**

```markdown
## Post-flight Verification

### Parallel Work (if applicable)
- [ ] All Sync Points passed (see `PARALLEL_WORK_PROTOCOL.md`)
- [ ] All tracks returned deliverables
- [ ] No blocking conflicts between tracks

### Sequential Work (if applicable)
- [ ] All handoffs completed (see `AGENT_HANDOFF_PROTOCOL.md`)
- [ ] Each agent returned expected deliverable
- [ ] No unresolved questions from handoffs

### Dialogue (if applicable)
- [ ] Consensus reached OR coordinator forced decision (≤3 iterations)
- [ ] Trade-offs documented
- [ ] No open debates

### Quality
- [ ] All quality gates pass (see `RUNBOOK_AGENT.md`)
- [ ] All guard tests pass (if applicable)
- [ ] Coverage ≥97% (if applicable)

### Postponed Items
- [ ] All postponed items recorded in `BACKLOG_LEDGER.md`
```

**Failure condition:** If any item is unchecked → task is incomplete; do not proceed to Synthesis.

---

## Step 5: Synthesis

**When:** After Post-flight Verification

**Action:** Coordinator synthesizes outputs into coherent solution

**Template:** See `docs/orchestration/synthesis.template.md`

**Output:**
- Final decision
- Rationale
- Follow-ups (if any)

---

## Step 6: DoD (Definition of Done)

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

### Orchestration Protocols
- Context Map: `docs/orchestration/AGENT_CONTEXT_MAP.md`
- Capability Matrix: `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
- Handoff Protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Dialogue Template: `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md`
- Parallel Work Protocol: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`

---

## Key Principles

1. **Coordinator-first:** See `AGENTS.md` (Agent Coordination section) for canonical rule
2. **Quality gates:** See `RUNBOOK_AGENT.md` (Quality Gates section) for canonical checklist
3. **Documentation:** Update AGENTS.md/RUNBOOK if workflow changes
4. **Postponed items:** Always record in BACKLOG_LEDGER
5. **Dev-only:** This workflow is for development, not runtime product
6. **Pre-flight enforcement:** Coordinator must complete Pre-flight Checklist before starting
7. **Post-flight verification:** Coordinator must verify execution requirements before Synthesis

---

**Last updated:** 2026-02-03 (PR-634)
**Related:** `AGENTS.md` (Agent Coordination section), `RUNBOOK_AGENT.md` (Quality Gates section)
