---
description: Create a bounded PulsePlate action packet
---

# Create Action Packet

Emit one narrow execution packet using the canonical fields below.

## Required fields

- `task_id`
- `track`
- `owner`
- `agent_role`
- `requested_agents`
- `objective`
- `scope_in`
- `scope_out`
- `constraints`
- `risk_class`
- `verification`
- `promotion_target`
- `notes`

## Output format

```yaml
task_id: TASK-...
track: workforce
owner: ...
agent_role: ...
requested_agents: []
objective: ...
scope_in:
  - ...
scope_out:
  - ...
constraints:
  - ...
risk_class: low|medium|high
verification:
  - ...
promotion_target:
  type: docs|rules|schema|tooling|pr|artifact
  path: ...
notes:
  - ...
```

Keep packets narrow, reviewable, and rollback-safe.
