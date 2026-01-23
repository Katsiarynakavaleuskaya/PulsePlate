# Agent Index (Canonical)

**Purpose:** Single entry point for discovering available Cursor agents and their capabilities.

**Canonical agent files:** `.cursor/agents/*.md`

**Model selection policy:** `docs/agents/model_policy.md`

---

## Available Agents

| Agent | Model | Summary | Canonical Doc | When to Use |
|-------|-------|---------|---------------|-------------|
| agent-coordinator | auto | Routes tasks to appropriate agents, synthesizes multi-agent work | `.cursor/agents/agent-coordinator.md` | Start any task; coordinate multiple agents |
| ai-innovation-specialist | auto | AI/ML features, RAG, computer vision, LLM integration, research-backed innovations | `.cursor/agents/ai-innovation-specialist.md` | AI/ML features, research, computer vision |
| architecture-specialist | auto | Code structure, architectural patterns, invariant enforcement, design patterns | `.cursor/agents/architecture-specialist.md` | Architecture decisions, pattern design, invariant checks |
| bug-hunter | auto | Bug detection, CI failures, guard violations, coverage gaps | `.cursor/agents/bug-hunter.md` | Bugs, test failures, quality gates |
| creative-designer | auto | UI/UX design, brand assets, App Store visuals, marketing creatives | `.cursor/agents/creative-designer.md` | Design, visuals, brand assets |
| marketing-strategist | auto | ASO/SEO, growth strategy, positioning, conversion optimization | `.cursor/agents/marketing-strategist.md` | Marketing, growth, ASO/SEO |
| security-auditor | auto | Security reviews, vulnerabilities, threat modeling, compliance checks | `.cursor/agents/security-auditor.md` | Security audits, vulnerability scans |

---

## Usage

1. **Find agent:** Use table above to identify appropriate agent for your task
2. **Read capabilities:** Click canonical doc link for full capabilities and usage
3. **Check model rationale:** Each agent file contains "Model Selection Rationale" section
4. **Start task:** Use coordinator-first rule (see `AGENTS.md`)

---

## Sync Rule

If an agent file is added/renamed in `.cursor/agents/`, update this index in the same PR.

---

**Last updated:** 2026-01-23
**Related:** `AGENTS.md` (Agent Coordination section), `docs/agents/model_policy.md`
