# Agent Role Contracts (Docs-only)

**Status:** Advisory (contracts for future runtime PRs)
**Scope:** Universal (applies to orchestration-layer work)
**Last updated:** 8 February 2026 (PR #691)

---

## Source of Truth (SoT)

- Canonical orchestration workflow: `docs/orchestration/workflow.md`
- Coordinator-first rule + repo hard gates: `AGENTS.md`
- Agent registry: `docs/agents/index.md`
- Agent definitions: `.cursor/agents/*.md`

---

## Universal Role Contract (applies to all agents)

Each agent must explicitly provide:

1. **Context loaded**: which SoT documents were consulted (paths only).
2. **Hard boundaries**: what the agent will not do.
3. **Deliverable**: what is returned to `agent-coordinator` (artifact types, not vibes).
4. **Evidence contract**: how claims are supported:
   - `file:line` pointers for repo policy assertions, and/or
   - reproducible commands + raw output + exit codes (when applicable).

---

## Authority model (non-negotiable)

- `agent-coordinator` is the **single decision authority** and owns final synthesis and DoD.
- All other agents are **advisory** unless a document explicitly grants a narrow veto/stop condition.

---

## Per-agent contracts (canonical pointers)

This repo keeps per-agent contracts in `.cursor/agents/`. For details, reference the agent file directly:

- Philosophy: `.cursor/agents/philosophy-agent.md`
- Logic: `.cursor/agents/logic-agent.md`
- Bayesian/UQ: `.cursor/agents/bayesian-uq-agent.md`
- RAG systems: `.cursor/agents/rag-systems-agent.md`
- CV: `.cursor/agents/cv-agent.md`
- AI app architect: `.cursor/agents/ai-app-architect.md`
- Data scientist: `.cursor/agents/data-scientist-agent.md`
- ML engineer: `.cursor/agents/ml-engineer-agent.md`
- Nutritionist: `.cursor/agents/nutritionist-agent.md`
- CBT psychologist: `.cursor/agents/cbt-psychologist-agent.md`
- Epistemology & discovery: `.cursor/agents/epistemology-discovery-agent.md`
- Physics & sensor modeling: `.cursor/agents/physics-sensor-agent.md`
