# Kimi Native Subagent Bridge Protocol

**Purpose:** Define the canonical adapter layer for PulsePlate repo-agent
orchestration when the execution runtime is **Kimi Code CLI** (or another
Kimi-native executor).

**Status:** Canonical for the Kimi runtime adapter layer. This protocol does
not replace `AGENTS.md`, `AGENT_ROUTING_GRAPH.md`, or
`NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`; it specialises that generic bridge for
the Kimi transport.

---

## 1. Why this exists

PulsePlate orchestration supports multiple native execution runtimes:

1. **Codex-native subagents** — canonical transport `"codex-native-subagents"`
   (see `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`)
2. **Kimi-native subagents** — transport `"kimi-native-subagents"` (this doc)

Both transports share the **same** canonical repo-agent slugs, instruction
files, routing graph, and quality gates. The only difference is the
runtime-level transport label that helps the coordinator and telemetry
distinguish which native executor produced a given artifact.

---

## 2. Canonical invariants

1. Routing still resolves through `docs/orchestration/AGENT_ROUTING_GRAPH.md`.
2. The coordinator still decides `primary_agent`, `secondary_agents`, and
   `reviewer`.
3. Kimi runtime subagents may be spawned **only** through coordinator-mediated
   dispatch.
4. Every spawned Kimi subagent **must** carry the corresponding repo-agent
   instruction file from `.cursor/agents/<slug>.md`.  Kimi does **not** use a
   separate `.kimi/agents/` directory; agent definitions are single-sourced in
   `.cursor/agents/`.
5. User-facing updates must identify the **repo agent slug**, not only the
   native executor label (e.g. say "bug-hunter is triaging", not "Kimi is
   running").
6. Skills are loaded from `.agents/skills/` and follow the same
   `AGENT_SKILL_ROUTING_POLICY.md` rules as Codex-native execution.

---

## 3. Task packet contract

`scripts/orchestration/task_bootstrap.py` emits a `native_subagent_bridge`
object with `transport: "kimi-native-subagents"` when the runtime signals Kimi
support.  The rest of the packet structure is identical to the Codex bridge:

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
- `native_agent_type` — transport hint for Kimi (see mapping below)
- `execution_mode`
- `instruction_path` — always `.cursor/agents/<slug>.md`
- `transport_rationale`
- `dispatch_contract`

### Kimi native agent type mapping

| Canonical profile | `native_agent_type` | Kimi runtime semantics |
|-------------------|---------------------|------------------------|
| `ANALYSIS_PROFILE` | `default` | General Kimi task execution (analysis, routing, synthesis) |
| `CODEBASE_EXPLORER_PROFILE` | `explorer` | Read-mostly exploration (file search, codebase inspection) |
| `IMPLEMENTATION_PROFILE` | `worker` | Read-write implementation (editing, running checks, committing) |

Reviewer bindings always receive `native_agent_type: "explorer"` and
`execution_mode: "review_read_only"` regardless of the base role.

---

## 4. Dispatch rules

When the runtime is Kimi Code CLI:

1. Read the task packet first.
2. Use `primary_agent` / `secondary_agents` / `reviewer` as the canonical role
   identities.
3. Read `native_subagent_bridge` only to confirm `transport == "kimi-native-subagents"`.
4. Load the instruction path listed in the bridge entry (from `.cursor/agents/`).
5. Load `required_context` and `recommended_skills` from the same task packet.
6. In updates, describe the work using the repo-agent slug.

---

## 5. Scope boundary

This protocol is an adapter only. It must not:

- rewrite the routing graph,
- invent runtime-only agent names as canonical roles,
- bypass coordinator-first policy,
- bypass scoped `AGENTS.md` or quality gates,
- create a separate `.kimi/agents/` instruction directory.

---

## 6. Implementation reference

- Bridge module: `scripts/orchestration/native_subagent_bridge.py`
  - `KIMI_BRIDGE_TRANSPORT`
  - `build_kimi_native_subagent_bridge()` convenience wrapper
  - `build_native_subagent_bridge(transport=KIMI_BRIDGE_TRANSPORT)` generic API
- Packet builder: `scripts/orchestration/task_bootstrap.py`
- Coordinator SoT: `.cursor/agents/agent-coordinator.md`
- Generic bridge SoT: `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
- Workflow SoT: `docs/orchestration/workflow.md`

---

## 7. Security Notes

- Kimi subagents must inherit the same repo constraints as the canonical agent
  role.
- The bridge must not create hidden autonomous routing outside coordinator
  control.
- Kimi runtime executor labels must not be treated as permission grants.
- Sensitive files (`.env*`, secrets, CI auth config) remain immutable for Kimi
  subagents just as they are for Codex subagents.

---

## 8. Experiment Runner participation

When a Kimi runtime executes an experimentation loop:

- The Experiment Runner still joins **after** coordinator bootstrap.
- It does **not** replace `check_preflight.py`, `task_bootstrap.py`, or
  `agent-coordinator`.
- Oracle-only artifacts are written to
  `artifacts/orchestration/experiments/results/`.
- The canonical co-author trailer remains:
  ```text
  Co-authored-by: PulsePlate Experiment Runner <pulseplate@pm.me>
  ```

---

**Last updated:** 2026-05-22 (PR kimi-native-subagent-bridge-integration)
