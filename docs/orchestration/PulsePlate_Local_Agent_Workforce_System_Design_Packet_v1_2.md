# PulsePlate — Local Agent Workforce System Design Packet

**Version:** 1.2
**Date:** 2026-04-04
**Status:** implementation-ready architecture
**Focus:** local-first workforce + CAID-style orchestration

**Related repo docs:** [CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md](./CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md), [COORDINATOR_MERGE_READINESS_RULES.md](./COORDINATOR_MERGE_READINESS_RULES.md), root [`AGENTS.md`](../../AGENTS.md), [AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md](./AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md), [LOCAL_EXECUTION_SANDBOX_RUNBOOK.md](./LOCAL_EXECUTION_SANDBOX_RUNBOOK.md).

---

## 1. Executive summary

PulsePlate should be developed through **two synchronized but separate tracks**:

1. **Delivery track**
   - Codex + ChatGPT
   - backlog, PR roadmap, merge/readiness, release truth, current product lanes

2. **Workforce platform track**
   - Cursor / Composer + Ollama + MCP + external memory
   - a persistent local staff that monitors, analyzes, drafts, triages, and supports the delivery track

This workforce is **not** a chat with role prompts. It is a **semi-autonomous operating system** for the project.

The correct orchestration backbone for this staff is **CAID-style**:

- central manager
- dependency graph
- asynchronous delegation
- isolated worktrees
- explicit integration
- executable test-based verification

---

## 2. Why CAID matters for PulsePlate

The March 2026 CMU paper on **Centralized Asynchronous Isolated Delegation (CAID)** argues that long-horizon software tasks benefit more from structured coordination than from simply increasing single-agent loop count. The paper reports **+26.7% absolute** over single-agent baselines on PaperBench and **+14.3%** on Commit0, using centralized delegation, asynchronous execution, isolated workspaces, and structured branch-and-merge integration.

**Primary reference:** [Effective Strategies for Asynchronous Software Engineering Agents (HF Papers 2603.21489)](https://huggingface.co/papers/2603.21489)

This maps unusually well to PulsePlate because the repo already enforces:

- worktree isolation (see [AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md](./AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md))
- PR-only promotion and merge governance (see [`AGENTS.md`](../../AGENTS.md) and [COORDINATOR_MERGE_READINESS_RULES.md](./COORDINATOR_MERGE_READINESS_RULES.md))
- deterministic validation before merge claims

A **design-bridge / sandbox precedent** (e.g. `pp-design-bridge` style configs: `cursor-local`, `sandbox/worktree`, local Ollama endpoint, `promotion_path: PR only`, `direct_runtime_mutation: FORBIDDEN`) may live outside this worktree; when present in the monorepo, link the canonical path here. The **intent** is already aligned: CAID is the right formalization of what the repo already wants.

---

## 3. System purpose

The local workforce system must do four things reliably:

1. monitor the project continuously
2. prepare trustworthy action packets
3. execute bounded low/medium-risk work in isolation
4. improve itself through reviewed self-reflection

It must **not**:

- silently mutate production
- silently expand permissions
- replace repo source of truth
- use cloud sandboxes for sensitive paths by default

---

## 4. Platform facts already validated

Canonical baseline for Cursor / Composer / Ollama / MCP in this repo: **[CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md](./CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md)**.

**Summary (see verified doc for links and `[VERIFY]` gaps):**

### Cursor

- Agent harness: instructions + tools + model
- Plan Mode explores, asks questions, builds a plan, waits for approval
- Static repo context: `.cursor/rules/`
- Reusable workflows: `.cursor/commands/`
- Worktrees as parallelization
- Cloud agents: remote sandboxes; not the default for privacy-sensitive local-first work

### Ollama

- Local REST API, structured outputs, tool calling, embeddings, OpenAI-compatible endpoints, `keep_alive`, configurable `num_ctx` (see verified doc)

### MCP

- Spec: `stdio` and Streamable HTTP; legacy HTTP+SSE for compatibility (see verified doc)

### Still `[VERIFY]`

Exact product matrix under your Cursor build:

- Rules taxonomy (Team / Project / User / Always / Auto / Manual / Agent)
- Custom Modes feature matrix
- MCP approval / auto-run behavior
- Memories scope and retention semantics

---

## 5. Design principles

1. **Repo-first truth** — contracts, ledger, ADRs, runbooks, review artifacts remain canonical
2. **External memory** — the model reasons; the system remembers outside the model
3. **Tool-mediated internet** — models do not “get internet”; approved tools do
4. **Asynchronous isolation by default** — no shared mutable workspace during active execution
5. **Explicit integration** — all agent outputs integrate through branch/merge/PR and tests
6. **Self-reflection without self-authorized power**
7. **Human gate on critical roles**
8. **Low blast radius first**

---

## 6. Core architecture

```text
Human owner / approver
        ↓
Director / Coordinator (semi-autonomous)
        ↓
Dependency graph + task router
        ↓
Asynchronous role agents in isolated worktrees
        ↓
Integration / merge / verification layer
        ↓
Repo truth + event log + memory stores
        ↓
Ollama local models + MCP tools
```

---

## 7. CAID-style orchestration model for PulsePlate

### 7.1 Central manager

The Director / Coordinator is the **only role** allowed to:

- decompose top-level objectives into subtasks
- build dependency graphs
- assign tasks to role agents
- sequence integration
- decide escalation to a human

### 7.2 Asynchronous execution

Role agents may run concurrently **only when the dependency graph allows it**.

Examples:

- Bug Hunter can triage CI while Memory Librarian updates incident context
- Security can review a patch while Backend Engineer drafts a narrow fix
- Business Analyst can gather metrics while Delivery roles are blocked on review

### 7.3 Isolated workspaces

Each execution agent works in:

- a separate worktree, or
- another explicit sandbox boundary.

This matches repo policy: integration via PR and merge-readiness checks ([COORDINATOR_MERGE_READINESS_RULES.md](./COORDINATOR_MERGE_READINESS_RULES.md)).

### 7.4 Integration layer

Agent output is not trusted until:

- tests run
- risk is classified
- review packet exists
- merge governance passes

### 7.5 Verification

All medium/high-impact outputs must go through executable verification:

- repo tests
- lints
- health checks
- packet consistency
- policy gates

---

## 8. Org structure

### Tier 0 — control plane

#### Director / Coordinator

**Mission:** task routing, dependency graph construction, phase planning, escalation, integration decisions
**Autonomy:** semi-autonomous only.

#### Memory Librarian / SoT Steward

**Mission:** context assembly, stale truth detection, canonical/advisory separation, event summaries
**Autonomy:** high; canonical edits still land via PR.

#### Release Manager

**Mission:** go/no-go packets, merge-readiness evidence, acceptance thresholds
**Autonomy:** semi-autonomous only.

### Tier 1 — reliability cell

#### Bug Hunter / Incident Analyst

**Mission:** reproduce failures, cluster regressions, prepare minimal safe fix packets
**Autonomy:** high in sandboxes.

#### Security / Cybersecurity Analyst

**Mission:** threat reviews, secret handling discipline, dependency/security triage, authz/authn drift
**Autonomy:** semi-autonomous only.

#### Deploy / SRE Agent

**Mission:** deploy diagnostics, CI/CD triage, env contract checks, rollback packet prep
**Autonomy:** semi-autonomous only.

### Tier 2 — delivery cell

- Backend Engineer Agent
- Frontend Engineer Agent
- iOS Engineer Agent
- QA / Verification Engineer
- Data / RAG Engineer

These roles may execute bounded implementation work in isolated worktrees.

### Tier 3 — product/business cell

- Business Analyst
- SEO / Growth Analyst
- Product Research Analyst

### Tier 4 — scientific / creative cell

- Scientific Insight Agent
- Creative Concept Agent

Introduce Tier 4 only after the reliability cell is stable.

---

## 9. Human-in-the-loop rules

The following roles must **never** become fully autonomous in this phase:

- Director / Coordinator
- Security Analyst
- Deploy / SRE
- Release Manager

They may:

- collect data
- run bounded checks
- propose actions
- draft runbooks and packets

They may not without approval:

- deploy to production
- rotate secrets
- merge protected branches
- weaken security policy
- delete data
- mark release-ready/incident-closed unilaterally

---

## 10. Memory architecture

### 10.1 Canonical memory

**Storage:** repo docs, backlog ledger, `AGENTS.md`, ADRs, contracts, PR mapping artifacts
**Owner:** humans + Memory Librarian
**Update path:** reviewed PR only

### 10.2 Operational memory

**Storage:** local SQLite/Postgres control-plane DB, task queue, run registry, approval registry
**Owner:** Director + Memory Librarian
**Update path:** automatic

### 10.3 Episodic memory

**Storage:** append-only event log, agent journals, action/result records
**Owner:** each role agent + Director

### 10.4 Research memory

**Storage:** `docs/research`, optional vector store, experiment registry
**Owner:** Scientific Insight / Creative / Data-RAG

### 10.5 Evaluation memory

**Storage:** benchmark results, false-positive log, rollback history, approval outcomes
**Owner:** Release Manager + Director

### 10.6 Hard rule

Cursor Memories are convenience context only. They are **not** canonical operational memory.

---

## 11. Self-reflection architecture

Every agent run should produce a reflection record with:

- objective
- assumptions
- evidence used
- uncertainty
- likely failure modes
- contradiction risk
- smallest safe next action
- confidence
- escalation reason

This reflection is written to episodic memory, not canonical memory.

---

## 12. Self-development architecture

The staff may improve itself, but only through reviewed packets.

### Allowed self-improvement

- role prompts
- checklists
- routing heuristics
- benchmark harnesses
- memory summarizers
- retrieval ordering
- incident templates

### Forbidden self-improvement

- silent permission expansion
- silent secret access expansion
- changing canonical truth without review
- weakening approval gates
- production control self-assignment

### Self-improvement loop

1. detect repeated failure pattern
2. propose improvement packet
3. benchmark current vs improved behavior
4. human review
5. merge if approved

---

## 13. Tool matrix

| Role | Repo Read | Repo Write | Terminal | Git/GH | Metrics/Logs | Browser/HTTP | MCP | Vector Memory | Prod actions |
|------|-----------|------------|----------|--------|--------------|--------------|-----|---------------|--------------|
| Director | yes | limited | limited | limited | yes | limited | yes | yes | no |
| Memory Librarian | yes | yes | limited | limited | no | no | yes | yes | no |
| Release Manager | yes | yes | yes | limited | yes | no | yes | yes | no |
| Bug Hunter | yes | yes (sandbox) | yes | limited | yes | limited | yes | yes | no |
| Security | yes | limited | yes | limited | yes | limited | yes | yes | approval only |
| Deploy/SRE | yes | limited | yes | limited | yes | limited | yes | yes | approval only |
| Backend Engineer | yes | yes | yes | limited | limited | no | yes | limited | no |
| Frontend Engineer | yes | yes | yes | limited | limited | limited | yes | limited | no |
| iOS Engineer | yes | yes | yes | limited | limited | limited | yes | limited | no |
| QA/Verification | yes | yes | yes | limited | yes | limited | yes | limited | no |
| Data/RAG Engineer | yes | yes | yes | limited | yes | limited | yes | yes | no |
| Business Analyst | yes | docs only | no | no | yes | yes | yes | yes | no |
| SEO/Growth | yes | docs only | no | no | yes | yes | yes | limited | no |
| Scientific Insight | yes | docs only | limited | no | limited | yes | yes | yes | no |
| Creative Concept | yes | docs only | no | no | limited | yes | yes | limited | no |

---

## 14. Cursor / Composer implementation model

### `.cursor/rules`

Use for: scoped machine-attached rules, role boundaries, folder-specific behavior, mode defaults.

### `AGENTS.md`

Use for: repo constitution, merge/readiness rules, PR governance, SoT order, delivery discipline.

### `.cursor/commands`

Use for: repeatable role workflows, packet generation commands, incident/debug commands.

### `.cursor/plans`

Use for: reviewed plans before complex execution; director-approved dependency graphs.

### Custom modes (create first)

- Director
- Memory Librarian
- Bug Hunter
- Security Review
- Deploy/SRE
- Backend Engineer
- Frontend Engineer
- iOS Engineer

### Hooks

Use only after explicit policy review. For PulsePlate they are a supply-chain surface and must be tightly limited.

### Cloud agents

Treat as optional and non-default: remote sandboxes are not the base for privacy-sensitive local-first operations.

---

## 15. MCP strategy

### Phase 0 MCP set

Start with only:

1. repo-search MCP
2. git/gh read-only MCP
3. CI/log adapter
4. metrics adapter
5. optional browser/HTTP adapter

### Preferred transport

- prefer `stdio` whenever possible
- use localhost HTTP only when daemon behavior is needed

### Avoid initially

- unrestricted shell MCP
- destructive DB tools
- secret store write adapters
- unbounded browser automation

---

## 16. Phase-by-phase rollout

### Phase 0 — foundation (week 1)

**Build:** `.cursor/rules` skeleton, first 5 custom modes, local control-plane DB schema, event-log schema, one repo-search MCP, one git/gh read-only MCP
**Success:** every role can produce a valid action packet; no role can silently mutate production

### Phase 1 — reliability workforce (weeks 2–3)

**Build:** Bug Hunter, Security Analyst, Deploy/SRE, Release Manager, CI/log collectors, reflection schema
**Success:** triage and reliability packets become automatic

### Phase 2 — CAID execution layer (weeks 3–5)

**Build:** dependency graph manager, isolated worktree worker launcher, branch naming policy, integration queue, merge/verification handoff
**Success:** tasks can run concurrently in isolation and integrate safely

### Phase 3 — memory upgrade (weeks 5–8)

**Build:** stale-truth detector, vector retrieval for selected docs (optional), advisory/canonical separator, episodic summarizer
**Success:** context quality improves materially

### Phase 4 — business/growth cell (weeks 8–12)

**Build:** Business Analyst, SEO/Growth Analyst, Product Research Analyst
**Success:** recurring metrics and growth packets become cheap

### Phase 5 — scientific/creative cell (after reliability stabilizes)

**Build:** Scientific Insight Agent, Creative Concept Agent, experiment packet schema
**Success:** innovation becomes bounded and testable, not noisy

---

## 17. Recommended first 5 agents

1. Bug Hunter
2. Deploy / SRE
3. Security Analyst
4. Memory Librarian
5. Director

**Why this order:** PulsePlate’s bottlenecks remain release/runtime closure, security, bugs, and memory drift rather than growth-first expansion. Align with project execution docs and backlog priorities.

---

## 18. Immediate implementation kit

Turn this packet into repo-ready assets:

1. `.cursor/rules/00_root_bootstrap.mdc`
2. `.cursor/rules/10_director_mode.mdc`
3. `.cursor/rules/20_bug_hunter.mdc`
4. `.cursor/rules/30_security_review.mdc`
5. `.cursor/rules/40_deploy_sre.mdc`
6. `.cursor/rules/50_memory_librarian.mdc`
7. `.cursor/commands/create_action_packet.md`
8. `.cursor/commands/create_reflection_packet.md`
9. `docs/orchestration/LOCAL_AGENT_CONTROL_PLANE.md`
10. `docs/orchestration/LOCAL_AGENT_EVENT_LOG_SCHEMA.md`
11. `docs/orchestration/LOCAL_AGENT_ACTION_PACKET_SCHEMA.md`
12. local control-plane DB schema (`sqlite` first) — `docs/orchestration/sql/local_agent_control_plane.sql`
13. JSON schemas — `docs/orchestration/schemas/` (`action_packet`, `event_log`, `memory_capsule`, `reflection_packet`)
14. PR-1 scope / DoD / next PRs — [COMPOSER_BOOTSTRAP_KIT_PR1.md](./COMPOSER_BOOTSTRAP_KIT_PR1.md)

**Repo status:** the paths above are implemented in this repository as the Phase 0 foundation slice (docs/tooling only; no production runtime).

---

## 19. Hard decisions

1. CAID-style coordination is the correct orchestration model for PulsePlate.
2. Director remains semi-autonomous.
3. Security / Deploy / Release remain semi-autonomous.
4. Worktrees are mandatory for concurrent execution.
5. Integration always happens through explicit tests + PR/merge governance.
6. Cursor Memories are not canonical memory.
7. Cloud agents are not the default execution surface for sensitive work.
8. Self-improvement is allowed only through reviewed packets.

---

## 20. References

- [CAID / Asynchronous SWE agents — HF Papers 2603.21489](https://huggingface.co/papers/2603.21489)
- [CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md](./CURSOR_COMPOSER_PLATFORM_FACTS_VERIFIED.md) (this repo)
- [COORDINATOR_MERGE_READINESS_RULES.md](./COORDINATOR_MERGE_READINESS_RULES.md)
- [AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md](./AGENT_KNOWLEDGE_LIBRARY_WORKTREE_RUNBOOK.md)
- [LOCAL_EXECUTION_SANDBOX_RUNBOOK.md](./LOCAL_EXECUTION_SANDBOX_RUNBOOK.md)
- Root [`AGENTS.md`](../../AGENTS.md)
