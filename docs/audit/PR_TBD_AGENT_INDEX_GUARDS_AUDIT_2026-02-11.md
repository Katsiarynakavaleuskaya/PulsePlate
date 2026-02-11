# PR Audit — Agent Index + Guard Tests (Analytics/Web block)

**Date:** 11 February 2026
**Scope:** tests + docs (guard-style tests for agent registry + canonical protocol references)
**Status:** Opinion + Evidence (commands are reproducible; outputs are examples)

---

## Summary

We now have multiple canonical “agent surfaces” that must stay in sync:

- `.cursor/agents/*.md` (canonical agent specs)
- `docs/agents/index.md` (canonical index)
- `docs/orchestration/AGENT_CONTEXT_MAP.md` (canonical required-reading map)

Drift between these surfaces is a recurring failure mode (new agent/spec added, but index or context map forgotten),
which directly reduces orchestration quality and increases “missing context” errors in multi-agent work.

This PR adds deterministic guard tests to prevent registry drift and accidental removal of canonical protocol links.

---

## Evidence (repo truth)

### 1) Canonical agent specs exist under `.cursor/agents/`

Command:

```bash
ls .cursor/agents
```

Example output (may drift as agents are added/removed):

```text
agent-coordinator.md
ai-app-architect.md
ai-innovation-specialist.md
architecture-specialist.md
bayesian-uq-agent.md
bug-hunter.md
cbt-psychologist-agent.md
creative-designer.md
cv-agent.md
data-scientist-agent.md
epistemology-discovery-agent.md
logic-agent.md
marketing-strategist.md
ml-engineer-agent.md
nutritionist-agent.md
philosophy-agent.md
physics-sensor-agent.md
rag-systems-agent.md
security-auditor.md
web-research-agent.md
AGENTS.md
```

Interpretation:

- `AGENTS.md` is a meta file (no YAML frontmatter); it is **not** an agent spec.
- Each real agent spec has YAML frontmatter including `name: ...`.

### 2) Index and context map are the required sync surfaces

Canonical registration path is documented in `docs/agents/UPDATE_INSTRUCTIONS.md`:

- agent spec: `.cursor/agents/<agent>.md`
- index: `docs/agents/index.md`
- context map: `docs/orchestration/AGENT_CONTEXT_MAP.md`

---

## Changes (what this PR enforces)

### Guard: agent registry sync

New test: `tests/test_agent_docs_registry_guard.py`

Enforces:

- Every agent spec in `.cursor/agents/*.md` with YAML `name:` is listed in `docs/agents/index.md`
- Every agent spec is listed in `docs/orchestration/AGENT_CONTEXT_MAP.md`
- No “extra” entries exist in index/context map without a corresponding agent spec

### Guard: canonical protocol references are not accidentally removed

Also enforces that both:

- `AGENTS.md`, and
- `docs/orchestration/workflow.md`

continue to reference the canonical protocols:

- `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
- `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`
- `docs/orchestration/RESEARCH_BRAINSTORMING_PROTOCOL.md`
- `docs/orchestration/AGENT_REFLECTION_PROTOCOL.md`

---

## Test plan

```bash
pytest -q tests/test_agent_docs_registry_guard.py
make verify
```

---

## Non-goals

- No runtime behavior changes
- No changes to the agent protocol semantics (only guard enforcement of registry consistency)
- No “auto-generation” of indexes (kept manual + enforced by tests to avoid hidden drift)
