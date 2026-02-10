# Agent Message Protocol (Envelope v1)

**Purpose:** Make multi-agent orchestration **parseable and robust across models** by standardizing machine-readable envelopes for task packets, agent results, and repair requests.

**Status:** Canonical (dev-only). This protocol defines **format**, not runtime behavior.

---

## Core rule (non-negotiable)

When envelopes are used, an agent MUST return the required JSON **inside the required tags**.

- The coordinator parses **only** the substring between tags.
- Any text outside tags is ignored.

---

## Envelope types

### `<TASK_PACKET_V1>` (Coordinator → agent)

Minimum required keys:

- `protocol_version` (`"1.0"`)
- `task_id`
- `role`
- `mode`
- `request`
- `constraints[]`
- `inputs.must_read_paths[]`
- `output_requirements.must_return[]`
- `budgets` (optional, recommended)

### `<AGENT_RESULT_V1>` (Agent → coordinator)

Minimum required keys:

- `protocol_version` (`"1.0"`)
- `task_id` (must match)
- `status` (`ok` | `blocked` | `error`)
- `context_loaded_paths[]`
- `deliverables[]` (`type` + `summary`)
- `next_steps[]`

### `<REPAIR_REQUEST_V1>` (Coordinator → agent)

If parsing fails or required keys are missing, coordinator issues a repair request.
Agent must return **ONLY** a corrected `<AGENT_RESULT_V1>` as strict JSON (ASCII quotes), with required keys.

---

## Related documentation

- Workflow + security rule: `docs/orchestration/workflow.md`
- Handoff protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Parallel work protocol: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`
