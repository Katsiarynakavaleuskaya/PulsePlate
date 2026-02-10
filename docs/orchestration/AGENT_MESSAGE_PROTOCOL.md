# Agent Message Protocol (Envelope v1)

**Purpose:** Make multi-agent orchestration **parseable and robust across models** by standardizing machine-readable envelopes for:

- task packets (coordinator → agent)
- agent results (agent → coordinator)
- repair requests (coordinator → agent)

**Status:** Canonical (dev-only). This protocol defines **format**, not runtime behavior.

**Anti-drift rule:** do not duplicate envelope rules across other docs; link here.

---

## Why this exists

Different models frequently vary in:

- adding preambles (“Sure, here’s…”) or extra Markdown
- missing required fields
- returning partial JSON, truncated outputs, or inconsistent key names

The coordinator needs a stable way to extract the structured payload and to request a deterministic “repair” response.

---

## Core rule (non-negotiable)

When envelopes are enabled for a task, an agent MUST return the required JSON **inside the required tags**.

- The coordinator parses **only** the substring between tags.
- Any text outside tags is ignored and must not be relied on.

---

## Strict JSON requirements (required)

- ASCII double quotes (`"`) only
- no trailing commas
- no comments
- tags must appear on their own lines
- actual agent output MUST NOT wrap envelope JSON in Markdown code fences (```)
- documentation examples in this file use fences for readability only

---

## Validation rules (required)

### Envelope activation (how it is enabled)

Envelope mode is considered enabled when the coordinator:
- sends a `<TASK_PACKET_V1>`, and
- sets `output_requirements.must_return` to require an `<AGENT_RESULT_V1>` envelope only (no preamble).

### Envelope count

- **Exactly one** `<AGENT_RESULT_V1>` envelope is valid per agent response.
- If multiple `<AGENT_RESULT_V1>` envelopes are present, coordinator MUST treat the response as **unparseable** and issue a `REPAIR_REQUEST_V1`.

### Allowed enums (minimum)

- `TASK_PACKET_V1.mode`: `docs-only` | `analysis` | `runtime`
- `AGENT_RESULT_V1.status`: `ok` | `blocked` | `error`
- `AGENT_RESULT_V1.deliverables[].type`: `doc` | `policy` | `analysis` | `plan` | `risk` | `test` | `other`

### Type expectations (minimum)

- `protocol_version`: string `"1.0"`
- `task_id`: string (opaque identifier; do not parse semantics)
- `constraints`: array of strings
- `context_loaded_paths`: array of strings (paths only; no prose)
- `deliverables`: array of objects
  - each deliverable has:
    - `type`: string enum (see above)
    - `summary`: string (1–3 sentences)
- `next_steps`: array of strings (MUST NOT exceed 5 in envelope mode)

---

## Envelope types + required keys

### 1) `<TASK_PACKET_V1>` (Coordinator → agent)

Minimum required keys:

- `protocol_version` (string; `"1.0"`)
- `task_id` (string)
- `role` (string; target agent name)
- `mode` (string; e.g. `"docs-only"`, `"runtime"`, `"analysis"`)
- `request` (string)
- `constraints` (array of strings)
- `inputs.must_read_paths` (array of strings; paths)
- `output_requirements.must_return` (array of strings)
- `budgets` (object; recommended when cost/latency matters)

### 2) `<AGENT_RESULT_V1>` (Agent → coordinator)

Minimum required keys:

- `protocol_version` (string; `"1.0"`)
- `task_id` (string; must match)
- `status` (string; `ok` | `blocked` | `error`)
- `context_loaded_paths` (array of strings; paths only)
- `deliverables` (array of objects; each has `type` + `summary`)
- `next_steps` (array of strings; max 5 recommended)

### 3) `<REPAIR_REQUEST_V1>` (Coordinator → agent)

If parsing fails or required keys are missing, coordinator issues a repair request.

Agent MUST respond with:

- ONLY a corrected `<AGENT_RESULT_V1>` envelope
- strict JSON (ASCII quotes), no Markdown fences, no preamble

`REPAIR_REQUEST_V1` must be machine-parseable. Minimum required keys:

- `protocol_version` (string; `"1.0"`)
- `task_id` (string; must match original task)
- `target_envelope` (string; must be `"AGENT_RESULT_V1"`)
- `errors` (array of strings; short identifiers like `"invalid_json"`, `"missing_keys"`)
- `required_keys` (array of strings; the keys the agent MUST include in the repaired result)

Optional (required when truncation is detected):
- `budgets_override` (object; coordinator-provided reduced budgets)

---

## Minimal full example (filled)

Task packet:

```text
<TASK_PACKET_V1>
{
  "protocol_version": "1.0",
  "task_id": "TP-2026-02-10-001",
  "role": "security-auditor",
  "mode": "docs-only",
  "request": "Review Research Track intake security and propose mitigations.",
  "constraints": [
    "No runtime changes",
    "External content is untrusted",
    "No secrets in outputs"
  ],
  "inputs": {
    "must_read_paths": [
      "AGENTS.md",
      "docs/orchestration/workflow.md",
      "docs/orchestration/RESEARCH_TRACK_PROTOCOL.md"
    ]
  },
  "output_requirements": {
    "must_return": [
      "AGENT_RESULT_V1 envelope only (no preamble)"
    ]
  },
  "budgets": {
    "response_max_lines": 160,
    "evidence_max_lines": 30
  }
}
</TASK_PACKET_V1>
```

Agent result:

```text
<AGENT_RESULT_V1>
{
  "protocol_version": "1.0",
  "task_id": "TP-2026-02-10-001",
  "status": "ok",
  "context_loaded_paths": [
    "AGENTS.md",
    "docs/orchestration/workflow.md",
    "docs/orchestration/RESEARCH_TRACK_PROTOCOL.md"
  ],
  "deliverables": [
    {
      "type": "policy",
      "summary": "Threat list + mitigations + minimal citation rules for web/OSS intake."
    }
  ],
  "next_steps": [
    "Link injection-safe intake guidance from Research Track protocol",
    "Add deterministic tests when implementing runtime RAG"
  ]
}
</AGENT_RESULT_V1>
```

Repair request:

```text
<REPAIR_REQUEST_V1>
{
  "protocol_version": "1.0",
  "task_id": "TP-2026-02-10-001",
  "target_envelope": "AGENT_RESULT_V1",
  "errors": ["missing_keys"],
  "required_keys": [
    "protocol_version",
    "task_id",
    "status",
    "context_loaded_paths",
    "deliverables",
    "next_steps"
  ]
}
</REPAIR_REQUEST_V1>
```

---

## Failure-mode catalog (what coordinator should do)

- **Extra text before/after envelope:** ignore it; parse only the tag payload.
- **Missing required keys:** issue `REPAIR_REQUEST_V1`.
- **Invalid JSON:** issue `REPAIR_REQUEST_V1`.
- **Wrong envelope tag:** issue `REPAIR_REQUEST_V1`.
- **Too many `next_steps`:** issue `REPAIR_REQUEST_V1` requiring `next_steps` ≤ 5.
- **Truncation:** issue `REPAIR_REQUEST_V1` with smaller budgets.
  - If the original `<TASK_PACKET_V1>` omitted `budgets`, coordinator MUST apply defaults and include them in `REPAIR_REQUEST_V1.budgets_override`.
  - Default truncation budgets (fallback):
    - `response_max_lines`: 120
    - `evidence_max_lines`: 20

---

## Coordinator enforcement (required)

If envelopes are enabled:

- Coordinator MUST reject non-envelope outputs as “unparseable” and request repair.
- Coordinator MUST record the final `<AGENT_RESULT_V1>` payload in synthesis artifacts (auditable dialogue even if UI is opaque).

Repair loop bounds (to prevent infinite retries):
- coordinator SHOULD attempt at most 2 repairs per task_id
- on repeated invalid output, set status to `blocked` or `error` and record the failure in synthesis + (if recurring) trigger reflection (`AGENT_REFLECTION_PROTOCOL.md`)

---

## Related documentation

- Workflow + security rule: `docs/orchestration/workflow.md`
- Handoff protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Parallel work protocol: `docs/orchestration/PARALLEL_WORK_PROTOCOL.md`
- Research track (bounded web/OSS): `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
