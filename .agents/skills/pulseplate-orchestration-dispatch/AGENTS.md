# Orchestration Dispatch — Agent Instructions

Root `AGENTS.md` owns authority, required roles and validation budgets.
`docs/orchestration/workflow.md` owns staged startup; this scope consumes the
existing packet and bridge under `SKILL.md`.

## Envelopes and sources

Use the existing `TASK_PACKET_V1`, `AGENT_RESULT_V1` and `REPAIR_REQUEST_V1`
envelopes when the canonical message protocol requires them. A generated
packet, partial result or native transport label grants no execution authority.

The bridge's validated manifest owns ordered occurrences and permissions;
the packet's native bindings own transport types. Do not maintain a copied
role/type table or a manual Markdown parser. Follow `rules/packet-parsing.md`
and `rules/role-mapping.md`.

## Context loading

Follow `rules/context-loading.md`. The coordinator resolves wildcard/directory
navigation through the canonical context map into task-applicable concrete
paths with reasons, without dropping literal mandatory files. Full selected
role/authority/context sources, the current packet, accepted criteria and
predecessor evidence must reach the child. Summaries may cover optional
references; they do not replace mandatory instructions to fit a budget.

For supported JSON packets, `--role-context-order <N>` requests exact full
context for one existing occurrence. Use a complete successful delivery
directly. `complete=false` requires manual loading before claiming complete
context; errors remain fail-closed. Exact delivery has no persisted cache.

## Serial execution and phases

Preserve `dispatch_sequence`, including repeated slugs, and
`parallel_execution_allowed=false`. Group metadata grants no parallel work.
Carry each predecessor's evidence to its dependent occurrence. Do not append
post-open roles to an earlier phase or skip a required readonly role.

The later post-open role pass and conditions for repeating it are owned by root
`AGENTS.md` → Role-Agent Order Contract. New comments require disposition and
targeted validation, not an automatic new role chain or provider invocation.

## Results and model selection

Use root `AGENTS.md` → Command results and failure scope. An unresolved
prerequisite blocks its dependent action; partial evidence is not a passed gate.
Native model/effort inheritance, opt-in routing, unavailability and escalation
follow `docs/agents/model_policy.md`; this skill adds no retry budget.
