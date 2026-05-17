# Envelope Protocol Reference

Structured communication format for agent dispatch and results.

## Overview

Three envelope types exist for structured agent communication:

| Envelope | Direction | Purpose |
|----------|-----------|---------|
| TASK_PACKET_V1 | dispatcher → agent | Assign work |
| AGENT_RESULT_V1 | agent → dispatcher | Return findings |
| REPAIR_REQUEST_V1 | dispatcher → agent | Request corrections |

## TASK_PACKET_V1

Minimum required fields:

```json
{
  "envelope": "TASK_PACKET_V1",
  "agent_slug": "architecture-specialist",
  "scope": "Verify alignment of evidence graph with knowledge promotion invariant",
  "constraints": ["read-only", "no file modifications"],
  "required_context_paths": ["docs/orchestration/AGENT_ROUTING_GRAPH.md"],
  "expected_output": "findings list with file:line references",
  "mode": "analysis"
}
```

## AGENT_RESULT_V1

Minimum required fields:

```json
{
  "envelope": "AGENT_RESULT_V1",
  "agent_slug": "architecture-specialist",
  "status": "completed",
  "findings": [],
  "artifacts_produced": [],
  "blockers": []
}
```

Status values: `completed` | `partial` | `blocked`

## REPAIR_REQUEST_V1

Sent when result is insufficient:

```json
{
  "envelope": "REPAIR_REQUEST_V1",
  "agent_slug": "architecture-specialist",
  "missing": ["No file:line references provided for finding #2"],
  "retry_constraints": ["Address only the listed gaps", "Do not re-analyze completed items"],
  "max_retries_remaining": 1
}
```

## Usage in Qoder Context

Envelope usage is **OPTIONAL**. Natural language prompts work fine for Qoder
subagents. Envelopes provide value for:

- **Cross-tool compatibility** — same packet works in Cursor, Codex, Qoder
- **Structured output parsing** — deterministic field extraction
- **Audit trail** — machine-readable dispatch/result log
- **Replay** — re-run the same dispatch with identical inputs

When not using envelopes, ensure the equivalent information is present in
the natural language prompt (scope, constraints, expected output format).
