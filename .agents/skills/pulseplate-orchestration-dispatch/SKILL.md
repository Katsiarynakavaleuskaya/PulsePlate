---
name: pulseplate-orchestration-dispatch
description: Auto-dispatch PulsePlate orchestration agents from governance packets using the routing graph, context maps, and envelope protocol. Bridges 33 custom agent roles into native subagent transports (Kimi, Codex, Qoder).
license: MIT
metadata:
  author: PulsePlate
  version: '1.2.0'
---

# PulsePlate Orchestration Dispatch Skill

Automates multi-agent dispatch from governance packets, translating the
coordinator's declared role order into a sequence of native subagent invocations.

## When to use

- When you receive a governance packet with a "Coordinator Role Order" section
- When the user provides a packet path and expects role-ordered agent dispatch
- When you need to auto-resolve which native subagent type maps to a PulsePlate role
- When coordinating multi-agent review/implementation workflows defined in `docs/orchestration/`

## Supported transports

- **Kimi Code CLI** (`kimi-native-subagents`) — uses `default` / `explorer` / `worker` native types
- **Codex** (`codex-native-subagents`) — uses `default` / `explore` / `coder` native types
- **Qoder** — legacy compatibility via `qoder_dispatch_bridge.py`

Canonical entrypoint for all transports: `scripts/orchestration/role_dispatch_bridge.py`

## How to use

1. Run the bridge script to generate a dispatch manifest:
   ```bash
   python3 scripts/orchestration/role_dispatch_bridge.py --packet <packet_path> --pretty
   ```
   For one JSON packet-backed occurrence that needs exact full context, opt in:
   ```bash
   python3 scripts/orchestration/role_dispatch_bridge.py \
     --packet <packet_path> \
     --role-context-order <one-based-order> \
     --instruction-file tools/codex_skills/pulseplate-workflow/SKILL.md \
     --pretty
   ```
2. Parse the JSON output. Default mode returns the manifest directly; exact
   mode places it under the envelope's `manifest` field.
3. For each entry in `dispatch_sequence`, dispatch a native subagent:
   - **Type**: use `qoder_subagent_type` field (transport-mapped in the bridge)
   - **Prompt**: ordinarily include the agent's full definition, required context,
     packet constraints, and explicitly loaded skill instructions
   - **Dependencies**: if `depends_on_previous: true`, wait for the previous agent to complete
   - **Parallelism**: agents listed in the same `parallelizable_groups` array can run concurrently
4. Feed each agent's output as context to the next agent in sequence
5. After all agents complete, synthesize results per the packet's DoD

## Inputs required

- Governance packet file path (e.g., `artifacts/orchestration/task_packet_*.json`)
- OR explicit `--roles` list (comma-separated agent slugs)
- Optional: `--mode analysis|runtime` to influence type mapping

## Output format

- Default invocation returns the unchanged v2 dispatch manifest.
- `--role-context-order N` returns a separate
  `pulseplate.role-context-output.v1` envelope containing that unchanged
  manifest, the selected dispatch entry, exact full source contents, the
  current dynamic packet, and read metrics.
- Exact delivery is bounded to 128 regular single-link sources, 2 MiB per
  source and 8 MiB total. It rejects unsafe or changed sources. A glob or
  directory returns an explicit incomplete manual-loading result.
- Exact delivery is not persisted and has no cache CLI control.
- Each dispatched agent produces findings/output per their role definition
- Final synthesis follows the packet's Definition of Done (DoD)

## Hard rules

1. Always run `check_preflight.py` before dispatch
2. **Coordinator-first**: first agent in sequence must be `agent-coordinator`
   (or equivalent scope/synthesis role)
3. Skills are helpers, not authority — root `AGENTS.md` always wins
4. Read-only roles MUST use `explorer` / `Research` subagent type (never `coder` / `Coding`)
5. Post-open mandatory pass (`qa-engineer-agent -> bug-hunter -> security-auditor`) must always be last
6. Do NOT skip roles in the declared order unless coordinator explicitly removes them
7. Bridge output is deterministic — same packet always produces same manifest
8. Exact delivery never summarizes or truncates selected required sources
9. Recommended skill names never imply instruction loading; use explicit
   `--instruction-file` paths from admitted repository skill roots

## Related files

- `scripts/orchestration/role_dispatch_bridge.py` — canonical manifest generator
- `scripts/orchestration/qoder_dispatch_bridge.py` — Qoder compatibility facade
- `docs/orchestration/AGENT_ROUTING_GRAPH.md` — canonical routing baseline
- `docs/orchestration/AGENT_CONTEXT_MAP.md` — per-role context requirements
- `docs/orchestration/AGENT_CAPABILITY_MATRIX.md` — role capabilities
- `.cursor/agents/` — canonical agent definition files (single source for all runtimes)
