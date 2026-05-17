---
name: pulseplate-orchestration-dispatch
description: Auto-dispatch PulsePlate orchestration agents from governance packets using the routing graph, context maps, and envelope protocol. Bridges 33 custom agent roles into Qoder's native subagent system.
license: MIT
metadata:
  author: PulsePlate
  version: '1.0.0'
---

# PulsePlate Orchestration Dispatch Skill

Automates multi-agent dispatch from governance packets, translating the
coordinator's declared role order into a sequence of Qoder subagent invocations.

## When to use

- When you receive a governance packet with a "Coordinator Role Order" section
- When the user provides a packet path and expects role-ordered agent dispatch
- When you need to auto-resolve which Qoder subagent type maps to a PulsePlate role
- When coordinating multi-agent review/implementation workflows defined in `docs/orchestration/`

## How to use

1. Run the bridge script to generate a dispatch manifest:
   ```bash
   python3 scripts/orchestration/qoder_dispatch_bridge.py --packet <packet_path> --pretty
   ```
2. Parse the JSON manifest output
3. For each entry in `dispatch_sequence`, dispatch a Qoder subagent:
   - **Type**: use `qoder_subagent_type` field
   - **Prompt**: include the agent's full definition (read from `agent_definition_path`),
     the `required_context_paths` content, packet constraints, and recommended skills
   - **Dependencies**: if `depends_on_previous: true`, wait for the previous agent to complete
   - **Parallelism**: agents listed in the same `parallelizable_groups` array can run concurrently
4. Feed each agent's output as context to the next agent in sequence
5. After all agents complete, synthesize results per the packet's DoD

## Inputs required

- Governance packet file path (e.g., `docs/orchestration/PHILOSOPHY_EPIC_V2_PR1_PACKET_2026-05-17.md`)
- OR explicit `--roles` list (comma-separated agent slugs)
- Optional: `--mode analysis|runtime` to influence type mapping

## Output format

- **Dispatch manifest JSON** (from bridge script) — deterministic, cacheable
- Each dispatched agent produces findings/output per their role definition
- Final synthesis follows the packet's Definition of Done (DoD)

## Hard rules

1. Always run `check_preflight.py` before dispatch
2. **Coordinator-first**: first agent in sequence must be `agent-coordinator`
   (or equivalent scope/synthesis role)
3. Skills are helpers, not authority — root `AGENTS.md` always wins
4. Read-only roles MUST use Research subagent type (never Coding)
5. Post-open mandatory pass (`qa-engineer-agent -> bug-hunter`) must always be last
6. Do NOT skip roles in the declared order unless coordinator explicitly removes them
7. Bridge output is deterministic — same packet always produces same manifest

## Related files

- `scripts/orchestration/qoder_dispatch_bridge.py` — manifest generator
- `docs/orchestration/AGENT_ROUTING_GRAPH.md` — canonical routing baseline
- `docs/orchestration/AGENT_CONTEXT_MAP.md` — per-role context requirements
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md` — role capabilities
- `.cursor/agents/` — agent definition files
