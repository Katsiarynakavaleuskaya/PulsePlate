# Agent Non-Routable Specialists

Explicit allowlist for specialist agents that are canonical, indexed, and documented,
but are not required to appear in `AGENT_ROUTING_GRAPH.md` as primary/secondary/reviewer nodes.

## Override contract

These specialists are **non-routable by default**, not forbidden.

Interpretation:

- Coordinator may keep them **advisory-only** when the canonical routing graph already
  resolves a better domain primary.
- If a user explicitly requests one of these specialists, the coordinator must record
  that request in the task packet and either:
  - keep the specialist as an advisory collaborator with explicit rationale, or
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
