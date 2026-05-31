# Agent Non-Routable Specialists

Explicit allowlist for specialist agents that are canonical, indexed, and documented,
but are not required to appear in `AGENT_ROUTING_GRAPH.md` as primary/secondary/reviewer nodes.

## Override contract

These specialists are **non-routable by default**, not forbidden.

**Precedence:** If a specialist appears in `AGENT_ROUTING_GRAPH.md` as primary, secondary,
or reviewer for the **currently routed domain**, task bootstrap treats the graph slot as
authoritative and may **promote** an explicit request (`requested_agents`) like any other
in-slot agent. The non-routable list applies when the agent is **outside** that domain's
slot set (required custom-role pass with legacy `advisory_non_routable`
disposition metadata). Evidence:
`scripts/orchestration/task_bootstrap.py:575` (graph slots before non-routable guard),
`tests/test_task_bootstrap.py:1856` (`test_build_task_packet_graph_slot_precedes_non_routable_specialist_list`).

Interpretation:

- Coordinator may keep them as **required readonly/custom-role passes** when the
  canonical routing graph already resolves a better domain primary.
- If a user explicitly requests one of these specialists, the coordinator must record
  that request in the task packet and either:
  - keep the specialist as a required custom-role pass with explicit rationale, or
  - promote it through a domain-specific follow-up contract introduced in a dedicated PR.
- Absence from the routing graph means "not graph-primary by default"; it does **not**
  mean "cannot be requested", "cannot be consulted", or "cannot appear in the task packet".

- `ai-app-architect`
- `bayesian-uq-agent`
- `cbt-psychologist-agent`
- `data-scientist-agent`
- `designer-artist-agent`
- `epistemology-discovery-agent`
- `ml-engineer-agent`
- `nutritionist-agent`
- `physics-sensor-agent`
- `sora-prompt-engineer`
- `tutor-mentor-agent`
