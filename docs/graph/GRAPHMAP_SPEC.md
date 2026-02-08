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
