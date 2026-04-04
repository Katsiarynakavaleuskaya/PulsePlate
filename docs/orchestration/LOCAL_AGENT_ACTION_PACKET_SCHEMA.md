# Local Agent Action Packet Schema

This document describes the canonical packet shape for local workforce tasks.

## Required fields

- `task_id`
- `track`
- `owner`
- `agent_role`
- `objective`
- `scope_in`
- `scope_out`
- `constraints`
- `risk_class`
- `verification`
- `promotion_target`

## Optional fields

- `human_approval_required` (required and must be `true` when `risk_class = high`)
- `requested_agents`
- `notes`

## Track values

- `delivery`
- `workforce`
- `research`
- `design`
- `ops`

## Risk values

- `low`
- `medium`
- `high`

## Promotion target

```yaml
promotion_target:
  type: docs|rules|schema|tooling|pr|artifact
  path: ...
```

## Approval signaling

```yaml
human_approval_required: false
```

For high-risk packets:

```yaml
risk_class: high
human_approval_required: true
```

## Hard rules

- packets must stay narrow
- packets must separate scope-in from scope-out
- high-risk packets must explicitly signal human approval need
- packets cannot silently widen into product runtime work from workforce track

Machine-readable schema: [schemas/action_packet.schema.json](./schemas/action_packet.schema.json).
