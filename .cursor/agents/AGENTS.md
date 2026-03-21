# Agent instructions (scope: .cursor/agents/ and subdirectories)

**Canonical rules:** See root `AGENTS.md` for project-wide policies (coordinator-first rule, quality gates, process).

This document defines **scoped rules** specific to Cursor agents in `.cursor/agents/`.

---

## Coordinator-First Invariant

**Hard rule:** Any new task MUST start with `agent-coordinator` for task analysis and agent routing.

**Reference:** Root `AGENTS.md` (Agent Coordination section) for full policy.

**Local implementation:** `.cursor/agents/agent-coordinator.md` is the canonical coordinator agent.

## Required pre-flight (SoT)

Before doing any work:
- Follow `docs/orchestration/workflow.md` → “Canonical Pre-flight Checklist (SoT)”.
- Load required context for the invoked role from `docs/orchestration/AGENT_CONTEXT_MAP.md`.
- Load `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md` when installed skills may materially improve the task or when changing orchestration/agent workflow docs.
- Always include root `AGENTS.md` + nearest module `AGENTS.md` for any files you touch.

---

## Orchestration Templates and Workflow

**Canonical workflow:** `docs/orchestration/workflow.md`

**Message protocol compliance (SoT):** `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`

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
- If business-cluster ownership changes, sync `.cursor/agents/business-strategist-agent.md`, `docs/orchestration/AGENT_INVENTORY.md`, `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`, `docs/orchestration/AGENT_CONTEXT_MAP.md`, and `docs/agents/index.md` in the same PR

---

## Coordinator Bootstrap Triggers

Coordinator-first behavior is command-driven through
`scripts/orchestration/task_bootstrap.py` + `scripts/orchestration/check_preflight.py`.

Use bootstrap when:

1. **Task creation:** build task packet and resolve domain/cluster/routing
2. **Execution start:** validate task scope and explicit routing in `execute` mode
3. **PR / merge prep:** validate local evidence and reviewer readiness in `merge` mode
4. **Release planning:** build release packet for QA + App Store + growth coordination

**Reference:** See `agent-coordinator.md` and `docs/orchestration/workflow.md`.

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

**Agent index:** `docs/agents/index.md` - single entry point for agent discovery.

---

## Key Principles

1. **Router-only coordinator:** Coordinator routes and synthesizes, doesn't duplicate capabilities
2. **Single source of truth:** Agent files own capabilities, coordinator references them
3. **No duplication:** Process in `AGENTS.md`, workflow in `docs/orchestration/`, capabilities in agent files
4. **Sync rules:** Changes to agent files trigger coordinator updates in same PR

---

**Last updated:** 2026-03-07 (PR-1000)
**Related:** Root `AGENTS.md`, `docs/orchestration/workflow.md`, `docs/agents/model_policy.md`
