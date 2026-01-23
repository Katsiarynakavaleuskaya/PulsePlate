# Agent Model Selection Policy

**Canonical policy for model selection in `.cursor/agents/*.md` files.**

---

## Principles

1. **Default = `auto` for all agents.** Fixed models allowed **only** for: (a) repeatable reports, (b) benchmarks/replication, (c) cases where auto is unstable. Any model fixing requires separate PR + rationale.
2. **Coordinator = routing + links** → `auto` (no fixed model needed)
3. **Domain agents** → task-dependent (auto preferred, fixed only when justified)
4. **Security/Bug-hunter** → `auto` preferred; fixed model only if determinism required for specific task
5. **Creative/Innovation** → `auto` preferred (benefits from model variety)

---

## Current Model Assignments

| Agent | Model | Rationale |
|-------|-------|-----------|
| `agent-coordinator` | `auto` | Routing + links only; no need for fixed model; resolves Cursor UI compatibility |
| `ai-innovation-specialist` | `auto` | Research/innovation benefits from model flexibility |
| `architecture-specialist` | `auto` | Architecture patterns benefit from current model capabilities |
| `bug-hunter` | `auto` | Bug detection benefits from latest model improvements |
| `creative-designer` | `auto` | Creative tasks benefit from model variety |
| `marketing-strategist` | `auto` | Marketing strategy benefits from current model insights |
| `security-auditor` | `auto` | Security analysis benefits from latest security-focused models |

---

## Rationale

### Why `auto` for coordinator?

- **Coordinator role:** routing + delegation + links (not complex reasoning)
- **No drift risk:** routing logic is deterministic (agent capabilities → routing)
- **UI compatibility:** avoids Cursor UI warnings about unavailable models
- **Flexibility:** can leverage best available model without manual updates

### Why `auto` for domain agents?

- **Task-dependent:** different tasks may benefit from different model strengths
- **Model evolution:** latest models often improve on previous versions
- **Flexibility:** allows Cursor to select optimal model for current context

### When to use fixed models?

- **Security-critical:** when deterministic behavior is required (e.g., security audits)
- **Reproducibility:** when exact model behavior must be preserved across sessions
- **Specialized needs:** when a specific model has proven better for a domain

---

## Future Considerations

- **Model index:** track which models work best for which agent types
- **Performance metrics:** measure effectiveness of `auto` vs fixed models
- **Cost optimization:** consider model costs when selecting (if applicable)

---

**Last updated:** 2026-01-23
**Related:** `docs/agents/index.md`
