# Agent instructions (scope: .cursor/agents/ and subdirectories)

**Canonical rules:** See root `AGENTS.md` for project-wide policies (coordinator-first rule, quality gates, process).

This document defines **scoped rules** specific to Cursor agents in `.cursor/agents/`.

---

## Coordinator-First Invariant

**Hard rule:** Any new task MUST start with `agent-coordinator` for task analysis and agent routing.

**Reference:** Root `AGENTS.md` (Agent Coordination section) for full policy.

**Local implementation:** `.cursor/agents/agent-coordinator.md` is the canonical coordinator agent.

---

## Orchestration Templates and Workflow

**Canonical workflow:** `docs/orchestration/workflow.md`

**Templates:**
- Task Analysis: `docs/orchestration/task_analysis.template.md`
- Work Review: `docs/orchestration/work_review.template.md`
- Synthesis: `docs/orchestration/synthesis.template.md`
- DoD: `docs/orchestration/dod.template.md`

**Usage:** Coordinator uses these templates during orchestration workflow (see `agent-coordinator.md` Integration section).

---

## Agent Responsibilities and Constraints

### Agent File Structure

Each agent file (`.cursor/agents/*.md`) must:
- Have frontmatter with `name`, `model`, `description`
- Include "Model Selection Rationale" section (2-5 bullets) - see `docs/agents/model_policy.md`
- Document capabilities and when to use
- Link to canonical docs (no duplication)

### Coordinator Role

`agent-coordinator.md` is **router-only**:
- Routes tasks to appropriate agents
- Synthesizes multi-agent work
- Enforces quality gates
- **NOT** an encyclopedia (capabilities live in individual agent files)
- **NOT** a process doc (process lives in `AGENTS.md` / `RUNBOOK_AGENT.md`)

### Sync Rules

- If agent file added/renamed: update coordinator "Available Agents" section in same PR
- If agent capabilities change: update agent file only (coordinator references, doesn't duplicate)
- If missing agent doc: record in `docs/roadmap/BACKLOG_LEDGER.md`

---

## Automatic Invocation Triggers

Coordinator is automatically invoked when:

1. **Task creation:** Any new task is created (coordinator analyzes and routes)
2. **Agent work completion:** Agent(s) complete work (coordinator reviews and synthesizes)
3. **PR opened:** PR is opened (coordinator coordinates review across agents)
4. **Release planned:** Release is planned (coordinator coordinates security + quality checks)

**Reference:** See `agent-coordinator.md` (Automatic invocation section) for details.

---

## Model Selection Policy

**Default:** `auto` for all agents (flexibility, latest capabilities).

**Fixed models:** Only when justified (repeatable reports, benchmarks, auto unstable).

**Canonical policy:** `docs/agents/model_policy.md`

**Per-agent rationale:** Each agent file contains "Model Selection Rationale" section (2-5 bullets).

---

## Quality Gates

Coordinator enforces project quality gates; see root `AGENTS.md` (policy) and `RUNBOOK_AGENT.md` (how-to).

**Summary (authoritative source: root `AGENTS.md`):**
- `make verify` (lint → typecheck → test-fast → diff-cov ≥97%)
- Guard tests pass (architectural invariants)
- Coverage ≥97% (total + diff-coverage)
- Security scans pass (bandit/pip-audit)

---

## Integration with Project Workflow

**Process rules:**
- Coordinator-first rule: Root `AGENTS.md` (Agent Coordination section)
- Runbook procedures: `RUNBOOK_AGENT.md` (Agent Coordination section)

**Agent index:** `docs/agents/index.md` (PR-567) - single entry point for agent discovery.

---

## Key Principles

1. **Router-only coordinator:** Coordinator routes and synthesizes, doesn't duplicate capabilities
2. **Single source of truth:** Agent files own capabilities, coordinator references them
3. **No duplication:** Process in `AGENTS.md`, workflow in `docs/orchestration/`, capabilities in agent files
4. **Sync rules:** Changes to agent files trigger coordinator updates in same PR

---

**Last updated:** 2026-01-23 (PR-566)
**Related:** Root `AGENTS.md`, `docs/orchestration/workflow.md`, `docs/agents/model_policy.md`
