# Local Agent Control Plane

## Purpose

Provide a **local-first SQLite starter control plane** for the PulsePlate workforce platform track.

This schema is not a production system.
It is a bounded local control surface for:

- task registration
- packet storage
- event logging
- memory capsule storage
- approval tracking by convention

## Design rules

1. Repo artifacts remain canonical.
2. SQLite is a starter local control-plane only.
3. High-risk actions still require human approval.
4. Event logs are append-oriented.
5. Promotion is explicit; no silent auto-promotion.

## Tables

### `tasks`

Minimal task registry.

### `action_packets`

Stores one canonical packet JSON per task.

### `agent_events`

Append-only event stream for execution and review milestones.

### `memory_capsules`

Stores classified memory capsules (`canonical`, `working`, `advisory`, `historical`).

## Event flow

1. create task
2. emit action packet
3. start isolated execution
4. record verification result
5. propose promotion
6. require human approval for medium/high-risk promotion

## Risk policy

- `low` = docs, rules, schemas, safe tooling
- `medium` = bounded non-prod code/tooling changes
- `high` = deploy, secrets, authz, release, production state

## Suggested next step after bootstrap

Add a small local adapter that:

- writes packets to SQLite
- validates them against JSON schema
- appends event records
- refuses promotion without required verification fields

## Related artifacts

- [LOCAL_AGENT_EVENT_LOG_SCHEMA.md](./LOCAL_AGENT_EVENT_LOG_SCHEMA.md)
- [LOCAL_AGENT_ACTION_PACKET_SCHEMA.md](./LOCAL_AGENT_ACTION_PACKET_SCHEMA.md)
- [schemas/](./schemas/) (JSON Schema)
- [sql/local_agent_control_plane.sql](./sql/local_agent_control_plane.sql)
