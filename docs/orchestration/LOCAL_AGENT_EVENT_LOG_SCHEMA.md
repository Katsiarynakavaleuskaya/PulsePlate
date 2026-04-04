# Local Agent Event Log Schema

This document describes the event envelope for local workforce execution logs.

## Required fields

- `event_id`
- `timestamp`
- `task_id`
- `agent_id`
- `event_type`
- `status`

## Optional fields

- `branch`
- `sha`
- `files`
- `message`
- `risk_class`
- `human_approval_required`

## Canonical event types

- `task_created`
- `packet_emitted`
- `execution_started`
- `execution_finished`
- `verification_passed`
- `verification_failed`
- `promotion_proposed`
- `promotion_rejected`
- `promotion_accepted`
- `incident_detected`

## Status values

- `info`
- `success`
- `warning`
- `error`

## Notes

This is a local control-plane log, not the source of truth for repo policy.
Use it to track operational state, not to replace reviewed artifacts.

Machine-readable schema: [schemas/event_log.schema.json](./schemas/event_log.schema.json).
