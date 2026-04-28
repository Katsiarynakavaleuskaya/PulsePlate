---
name: pulseplate-agent-product
description: Shape PulsePlate agent-product surfaces, operator workflows, and human-in-the-loop agent experiences without weakening coordinator authority, repo governance, or runtime safety boundaries.
---

# PulsePlate Agent Product Skill

## When To Use

Use this skill when the task productizes agent workflows:

- operator-facing agent UX,
- agent product specifications,
- human-in-the-loop review surfaces,
- orchestration-to-product handoffs,
- agent capability packaging,
- user-facing agent feature boundaries.

This skill is for product shaping and governance alignment. It is not a runtime
autonomy framework and it does not create a parallel orchestration layer.

## Inputs Required

- Coordinator packet or task goal.
- Candidate paths and nearest scoped `AGENTS.md`.
- Agent/product surface being changed.
- Source packet, protocol, or backlog item.
- Expected user/operator outcome.

## Procedure

1. Start from `agent-coordinator` output and keep the declared role order.
2. Read the governing orchestration/product contracts:
   - `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
   - `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
   - `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
   - `docs/orchestration/AGENT_EXPERIMENTATION_PROTOCOL.md`
   - `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`
   - `docs/dev/CODEX_SKILLS.md`
3. Define the product surface before proposing implementation:
   - user/operator,
   - permitted actions,
   - blocked actions,
   - evidence and audit trail,
   - handoff back to coordinator.
4. Keep agent capabilities bounded by repo source of truth, quality gates, and
   explicit human approval.
5. Record deferred autonomy, telemetry, or memory behavior in
   `docs/roadmap/BACKLOG_LEDGER.md`.

## Output Format

Report:

- agent-product surface,
- user/operator workflow,
- allowed and blocked actions,
- governance contracts referenced,
- risks and mitigations,
- gates to run,
- deferred follow-ups.

## Guardrails

- Passive helper only. Do not replace `agent-coordinator` or
  `scripts/orchestration/task_bootstrap.py`.
- Do not create a parallel control plane or hidden routing authority.
- Do not grant auto-merge, auto-resolve, deployment, billing, data export, or
  runtime tool execution without explicit operator approval and repo gates.
- Do not add hidden memory, silent learning, or canonical knowledge promotion
  outside the KPP source-of-truth flow.
- Do not widen production autonomy from docs or product copy alone.
- Keep `native_subagent_bridge` transport-only unless a separate approved PR
  changes that contract.

## Source Of Truth Links

- `AGENTS.md`
- `RUNBOOK_AGENT.md`
- `docs/dev/CODEX_SKILLS.md`
- `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
- `docs/orchestration/NATIVE_SUBAGENT_BRIDGE_PROTOCOL.md`
- `docs/roadmap/BACKLOG_LEDGER.md`
