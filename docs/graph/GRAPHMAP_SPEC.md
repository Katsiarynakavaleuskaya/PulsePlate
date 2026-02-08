# GraphMap Spec (SoT)

**Status:** Canonical spec (docs-only)
**Scope:** Dev-only visualization (read-only). Not runtime.
**Last updated:** 8 February 2026

---

## Purpose

GraphMap is a **read-only visualization** of relationships between canonical repo artifacts.

Hard rule:

> GraphMap visualizes relationships between canonical artifacts. It does not infer, decide, or validate.

GraphMap is **not**:

- a new Source of Truth
- a reasoning engine
- a knowledge base (RAG)
- a replacement for docs/ledger/tests

---

## Data contract

### `graph.json` schema (stable)

```json
{
  "schema_version": "1.0",
  "generated_from": {
    "repo_ref": "origin/main",
    "inputs": ["AGENTS.md", "docs/orchestration/*", "docs/agents/index.md", "docs/audit/*"]
  },
  "nodes": [
    {
      "id": "doc:AGENTS.md",
      "type": "document",
      "label": "AGENTS.md",
      "path": "AGENTS.md",
      "tags": ["project", "safety"]
    }
  ],
  "edges": [
    {
      "source": "agent:rag-systems-agent",
      "target": "doc:docs/orchestration/AGENT_CONTEXT_MAP.md",
      "type": "references",
      "evidence": ["docs/orchestration/AGENT_CONTEXT_MAP.md:1"]
    }
  ]
}
```

### Schema contract (normative)

GraphMap intentionally uses a **small, strict schema** to avoid implementation drift.

#### Root object

- **Required keys:** `schema_version`, `nodes`, `edges`
- **Optional keys:** `generated_from`
- **Additional keys:** forbidden

Constraints:

- `schema_version` is a stable string (e.g. `"1.0"`).
- `nodes` and `edges` are arrays; ordering is determinism-controlled (see below).

#### `generated_from` (optional)

- **Required keys (if present):** `repo_ref`, `inputs`
- **Additional keys:** forbidden
- `inputs` must contain repo-relative path patterns (strings).

#### Node object

- **Required keys:** `id`, `type`, `label`
- **Optional keys:** `path`, `tags`
- **Additional keys:** forbidden

Constraints:

- `id` must be unique and stable within the graph.
- `type` must be one of `NodeType` (see enums).
- If `path` is present, it must be **repo-relative** (no absolute paths).
- If `tags` is present, it may include one or more `Level` values (viewer filters) plus additional stable tags.
- No line ranges: if a consumer needs line precision, it must be represented as `path:line` inside `evidence` on edges.

#### Edge object

- **Required keys:** `source`, `target`, `type`
- **Optional keys:** `evidence`
- **Additional keys:** forbidden

Constraints:

- `source` and `target` must reference existing `nodes[].id`.
- `type` must be one of `EdgeType` (see enums).
- If `evidence` is present, it must be an array of repo-relative `path:line` anchors (single line only).

---

## Enums (strict)

### Node types

```yaml
NodeType:
  - topic
  - module
  - document
  - agent
  - invariant
  - test
  - risk
```

### Levels (viewer filters)

```yaml
Level:
  - theme
  - project
  - architecture
  - module
  - safety
  - execution
```

Notes:

- A node MAY have multiple levels via `tags`.
- Viewer MUST be able to filter by `Level` and `NodeType`.

### Edge types

```yaml
EdgeType:
  - defines
  - constrains
  - implements
  - validates
  - references
  - risks
```

---

## Allowed edge sources (deterministic)

Edges MUST only be created from explicit, parseable sources:

- Markdown links to repo paths (e.g. `` `docs/orchestration/workflow.md` ``)
- Explicit “Primary:” / “Must know:” sections in agent/context docs
- Explicit `file:line` anchors (single-line anchors only)
- Canonical orchestration surfaces:
  - `docs/orchestration/AGENT_CONTEXT_MAP.md`
  - `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
  - `docs/agents/index.md`

Forbidden sources:

- embedding similarity
- semantic guessing (“AI inferred this relationship”)
- probabilistic edges
- LLM-only extraction without explicit rules

---

## Determinism requirements

Given the same repo revision and the same inputs, the generated `graph.json` MUST be identical.

Rules:

- No timestamps
- No UUIDs
- Stable sorting of nodes/edges by `id` and `(source, target, type)`
- Evidence anchors MUST be stable (prefer `path:line`, not ranges)

### Error handling (deterministic)

Builder behavior must be deterministic in the presence of missing/invalid data.

Single-path rules:

- If an input source cannot be parsed, **skip it** (no placeholder nodes).
- If an edge references a missing node id, **drop the edge**.
- If a node cannot be typed to a valid `NodeType`, **drop the node** (and all edges to/from it will be dropped by the rule above).
- The output `graph.json` must not contain warnings/errors; builders may log warnings to stdout/stderr (tooling-only).

---

## Click behavior (viewer)

Default click action:

- Open a GitHub link to the file path; if `evidence` contains `path:line`, open the anchored location.

Forbidden:

- opening local absolute paths
- embedding secrets or tokens in URLs

---

## Non-goals (explicit)

- No validation of correctness (“graph is not a truth engine”)
- No code import graph parsing in v1 (optional follow-up)
- No RAG ingestion or runtime memory features

---

## Implementation notes (future PR B)

PR B (tooling, dev-only) may add:

- `tools/graphmap/build_graph.py` (deterministic builder)
- `docs/graph/viewer/*` (static viewer using an OSS graph library, e.g. Cytoscape.js)

---

## Enum mapping examples (canonical)

This section reduces ambiguity by mapping enums to concrete repo artifacts.

### NodeType → repo examples

- `document`: `AGENTS.md`, `docs/graph/GRAPHMAP_SPEC.md`, `docs/orchestration/AGENT_CONTEXT_MAP.md`
- `agent`: `.cursor/agents/agent-coordinator.md`, `.cursor/agents/rag-systems-agent.md`
- `test`: `tests/test_repo_policy_guards.py`, `tests/test_openapi_determinism.py`
- `module`: `core/`, `app/`, `providers/`, `frontend/`, `ios/` (folder-level module node)
- `invariant`: a named rule living in a canonical doc section (e.g., an `AGENTS.md` “Hard rule” section)
- `topic`: “OpenAPI determinism”, “One BMI Engine”, “LLM quota/rate limiting” (concept nodes)
- `risk`: “Cost abuse amplification”, “Prompt injection via retrieval” (risk statement nodes)

### Level (`tags`) → repo examples

- `project`: `AGENTS.md` (repo-wide rules), `docs/roadmap/BACKLOG_LEDGER.md`
- `architecture`: `docs/architecture/*`, `docs/orchestration/*`
- `module`: module folders (e.g., `core/`, `app/`) and module-scoped docs
- `safety`: `docs/safety/*`, security policy docs, rate-limit/quota hard rules
- `execution`: tests/guards and CI gate docs
- `theme`: cross-cutting concepts spanning multiple areas (e.g., “determinism”, “thin adapters”)

### EdgeType → canonical examples

- `references`: agent/context docs link to required SoT docs
- `defines`: a doc defines a contract/schema/policy
- `constrains`: a policy constrains a module/agent behavior
- `validates`: a test validates a policy/module contract
- `implements`: a PR (future tooling) implements a spec/ledger item (out of scope for PR A)
- `risks`: a risk statement attached to a topic/module/policy

### Canonical mini-examples (JSON)

#### Example 1: Policy → tests (determinism)

```json
{
  "schema_version": "1.0",
  "nodes": [
    {"id": "doc:AGENTS.md", "type": "document", "label": "AGENTS.md", "path": "AGENTS.md", "tags": ["project"]},
    {"id": "test:tests/test_openapi_determinism.py", "type": "test", "label": "OpenAPI determinism test", "path": "tests/test_openapi_determinism.py", "tags": ["execution"]}
  ],
  "edges": [
    {"source": "test:tests/test_openapi_determinism.py", "target": "doc:AGENTS.md", "type": "validates", "evidence": ["AGENTS.md:668"]}
  ]
}
```

#### Example 2: Agent → context map

```json
{
  "schema_version": "1.0",
  "nodes": [
    {"id": "agent:agent-coordinator", "type": "agent", "label": "agent-coordinator", "path": ".cursor/agents/agent-coordinator.md", "tags": ["project"]},
    {"id": "doc:docs/orchestration/AGENT_CONTEXT_MAP.md", "type": "document", "label": "AGENT_CONTEXT_MAP", "path": "docs/orchestration/AGENT_CONTEXT_MAP.md", "tags": ["architecture"]}
  ],
  "edges": [
    {"source": "agent:agent-coordinator", "target": "doc:docs/orchestration/AGENT_CONTEXT_MAP.md", "type": "references", "evidence": ["docs/orchestration/AGENT_CONTEXT_MAP.md:1"]}
  ]
}
```

#### Example 3: Topic + risk

```json
{
  "schema_version": "1.0",
  "nodes": [
    {"id": "topic:openapi-determinism", "type": "topic", "label": "OpenAPI determinism", "tags": ["theme", "architecture"]},
    {"id": "risk:openapi-drift", "type": "risk", "label": "OpenAPI artifact drift breaks client types", "tags": ["risk", "execution"]}
  ],
  "edges": [
    {"source": "risk:openapi-drift", "target": "topic:openapi-determinism", "type": "risks"}
  ]
}
```
