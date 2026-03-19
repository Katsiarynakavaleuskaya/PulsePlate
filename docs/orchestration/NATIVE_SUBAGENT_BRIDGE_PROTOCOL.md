# Native Subagent Bridge Protocol

**Purpose:** Preserve PulsePlate repo-agent orchestration when the execution
runtime exposes its own native subagents (for example, transport labels such as
`worker`, `explorer`, or `default`).

**Status:** Canonical for the runtime adapter layer. This protocol does not
replace `AGENT_ROUTING_GRAPH.md`; it adapts that routing into a newer
subagent-capable runtime.

---

## 1. Why this exists

PulsePlate has two layers now:

1. **Canonical orchestration layer**
   - repo agent slugs from `.cursor/agents/*.md`
   - coordinator-first routing
   - SoT docs in `docs/orchestration/*`
2. **Runtime transport layer**
   - native executor types exposed by the host runtime
   - examples: `default`, `worker`, `explorer`

Hard rule:

- PulsePlate repo-agent slugs stay canonical.
- Native executor names are **transport-only** and must not replace repo-agent
  identity in packets, logs, or user-facing updates.

---

## 2. Canonical invariants

1. Routing still resolves through `docs/orchestration/AGENT_ROUTING_GRAPH.md`.
2. The coordinator still decides `primary_agent`, `secondary_agents`, and
   `reviewer`.
3. Native runtime subagents may be spawned only through coordinator-mediated
   dispatch.
4. Every spawned native subagent must carry the corresponding repo-agent
   instruction file from `.cursor/agents/<slug>.md`.
5. User-facing updates must identify the repo agent slug, not only the native
   executor type.

---

## 3. Task packet contract

`scripts/orchestration/task_bootstrap.py` must emit a
`native_subagent_bridge` object with:

- `protocol_version`
- `transport`
- `dispatch_policy`
- `primary`
- `secondary`
- `advisory`
- `reviewer`

Each role binding includes:

- `repo_agent_slug`
- `display_name`
- `native_agent_type`
- `execution_mode`
- `instruction_path`
- `transport_rationale`
- `dispatch_contract`

Advisory collaborators are visible in the packet for transparency, but they are
**not runnable native subagents** unless a later contract explicitly promotes
them.

This makes the adapter explicit and testable without changing the canonical
repo-agent routing contract.

---

## 4. Dispatch rules

When a runtime supports native subagents:

1. Read the task packet first.
2. Use `primary_agent` / `secondary_agents` / `reviewer` as the canonical role
   identities.
3. Read `native_subagent_bridge` only to choose the host runtime transport type.
4. Spawn only `primary`, executable `secondary`, and `reviewer` bindings.
5. Keep `advisory` bindings non-runnable unless a future promoted contract says
   otherwise.
6. Load the instruction path listed in the bridge entry.
7. Load `required_context` and `recommended_skills` from the same task packet.
8. In updates, describe the work using the repo-agent slug.

Example:

- Canonical role: `bug-hunter`
- Native transport: `worker`
- Correct user-facing update: `bug-hunter is triaging the regression`
- Incorrect update: `worker is running`

Reviewer rule:

- reviewer bindings must use a read-only transport (`explorer`) even when the
  base repo role is normally implemented via a write-capable transport.

---

## 5. Scope boundary

This protocol is an adapter only.

It must not:

- rewrite the routing graph,
- invent runtime-only agent names as canonical roles,
- bypass coordinator-first policy,
- bypass scoped `AGENTS.md` or quality gates.

---

## 6. Implementation reference

- Bridge module: `scripts/orchestration/native_subagent_bridge.py`
- Packet builder: `scripts/orchestration/task_bootstrap.py`
- Coordinator SoT: `.cursor/agents/agent-coordinator.md`
- Workflow SoT: `docs/orchestration/workflow.md`

---

## 7. Security Notes

- Native subagents must inherit the same repo constraints as the canonical
  agent role.
- The bridge must not create hidden autonomous routing outside coordinator
  control.
- Runtime executor labels must not be treated as permission grants.

---

## 8. Marketing & GTM

- This change protects PulsePlate operator ergonomics during platform updates:
  your team keeps the same agent language and SoT instead of retraining around
  runtime-internal labels.
- Clear repo-agent naming improves onboarding, debugging, and reviewability,
  which reduces execution friction for future AI-assisted releases.
