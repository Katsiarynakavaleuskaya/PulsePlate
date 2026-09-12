# Agent instructions (scope: .cursor/agents/ and subdirectories)

**Canonical rules:** See root `AGENTS.md` for project-wide policies (coordinator-first rule, quality gates, process).

**Short startup path:** `docs/dev/AGENT_COMPATIBILITY_ONBOARDING.md`

This document defines **scoped rules** specific to Cursor agents in `.cursor/agents/`.

---

## Coordinator-First Invariant

**Hard rule:** Any new task MUST start with `agent-coordinator` for task analysis and agent routing.

**Machine-local launcher:** An opt-in host wrapper may front-load `check_preflight.py` and `task_bootstrap.py`; **coordinator-first authority** remains root `AGENTS.md` and the canonical workflow (`docs/orchestration/workflow.md`), not the launcher.

**Reference:** Root `AGENTS.md` (Agent Coordination section) for full policy.

**Local implementation:** `.cursor/agents/agent-coordinator.md` is the canonical coordinator agent.

**Advisory wiki compiler:** Operator-local compiled memory via `scripts/orchestration/wiki_ingest.py` (and related CLIs). It is **not** orchestration SoT and does not replace canonical `docs/**` or KPP; boundaries and commands are documented in `docs/orchestration/LOCAL_WIKI_SUPPORT_PLANE.md`.

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
- Include `readonly: true` unless a separate coordinator-owned PR explicitly
  grants write-capable runtime ownership for that role
- Include "Model Selection Rationale" section (2-5 bullets) - see `docs/agents/model_policy.md`
- Document capabilities and when to use
- Link to canonical docs (no duplication)

`readonly: true` is the safe default for role definitions. Runtime eligibility
is recorded through the packet-emitted
`role_dispatch_bridge.py --implementation-owner <role>` override in
`--mode runtime`; preserve every emitted eligible owner flag. Eligibility alone
does not select an implementation task. Follow the
[canonical admission sequence](../../docs/orchestration/workflow.md#admit-tracked-implementation)
for no-write preparation and each later active role/occurrence/file handoff.
The older `qoder_dispatch_bridge.py` name is compatibility-only.
Readonly is a role/action constraint, not proof of an OS sandbox. Native worker
transport and model choice do not grant implementation ownership.

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
- If business-cluster ownership changes, sync every file listed in **Business-Cluster Sync Targets** in the same PR

#### Business-Cluster Sync Targets

- `.cursor/agents/business-strategist-agent.md`
- `.cursor/agents/marketing-strategist.md`
- `.cursor/agents/agent-coordinator.md`
- `docs/orchestration/AGENT_INVENTORY.md`
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
- `docs/orchestration/AGENT_CONTEXT_MAP.md`
- `docs/agents/index.md`

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

**Canonical policy:** `docs/agents/model_policy.md` owns inherited native
dispatch and the explicitly enabled Astra/Sol mode. Frontmatter `model: auto`
does not select a Codex model or guarantee deterministic outputs.

**Per-agent rationale:** Each agent file contains "Model Selection Rationale" section (2-5 bullets).

---

## Quality Gates

Coordinator enforces project quality gates; see root `AGENTS.md` (policy) and `RUNBOOK_AGENT.md` (how-to).

**Summary (authoritative source: root `AGENTS.md`):**

- Follow the local narrow bundle and current-head CI/security requirements in
  root `AGENTS.md` → Hard Gates and `RUNBOOK_AGENT.md` → Quality Gates.
- Root owns coverage thresholds, failure interpretation and the local budget;
  role invocation does not authorize full local verification or broad reruns.

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
