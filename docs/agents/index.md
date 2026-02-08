# Agent Index (Canonical)

**Purpose:** Single entry point for discovering available Cursor agents and their capabilities.

**Canonical agent files:** `.cursor/agents/*.md`

**Model selection policy:** `docs/agents/model_policy.md`

---

## Available Agents

All agents default to `auto`; see `docs/agents/model_policy.md`.

| Agent | Model | Summary | Canonical Doc | When to Use |
|-------|-------|---------|---------------|-------------|
| agent-coordinator | auto | Routes tasks to appropriate agents, synthesizes multi-agent work | `.cursor/agents/agent-coordinator.md` | Start any task; coordinate multiple agents |
| ai-innovation-specialist | auto | AI/ML features, RAG, computer vision, LLM integration, research-backed innovations | `.cursor/agents/ai-innovation-specialist.md` | AI/ML features, research, computer vision |
| architecture-specialist | auto | Code structure, architectural patterns, invariant enforcement, design patterns | `.cursor/agents/architecture-specialist.md` | Architecture decisions, pattern design, invariant checks |
| bug-hunter | auto | Bug detection, CI failures, guard violations, coverage gaps | `.cursor/agents/bug-hunter.md` | Bugs, test failures, quality gates |
| creative-designer | auto | UI/UX design, brand assets, App Store visuals, marketing creatives | `.cursor/agents/creative-designer.md` | Design, visuals, brand assets |
| marketing-strategist | auto | ASO/SEO, growth strategy, positioning, conversion optimization | `.cursor/agents/marketing-strategist.md` | Marketing, growth, ASO/SEO |
| security-auditor | auto | Security reviews, vulnerabilities, threat modeling, compliance checks | `.cursor/agents/security-auditor.md` | Security audits, vulnerability scans |
| philosophy-agent | auto | Claim semantics, falsifiability, wellness boundaries; blocks unsafe/meaningless claims | `.cursor/agents/philosophy-agent.md` | Safety language, claim quality, “meaning” validation |
| logic-agent | auto | Contradiction detection, invariant checks for recommendations, guardable logic contracts | `.cursor/agents/logic-agent.md` | Consistency checks, rule contracts, contradiction audits |
| bayesian-uq-agent | auto | Uncertainty quantification, calibration, confidence contracts for AI outputs | `.cursor/agents/bayesian-uq-agent.md` | Confidence/uncertainty policies, reliability metrics |
| rag-systems-agent | auto | RAG architecture, recursive verification, budgets/stop conditions, grounding contracts | `.cursor/agents/rag-systems-agent.md` | RAG design, recursive retrieval policies, grounding audits |
| cv-agent | auto | Computer vision pipeline contracts (photo→items→confidence→nutrition mapping) | `.cursor/agents/cv-agent.md` | CV feature design, confidence scoring, privacy boundaries |
| ai-app-architect | auto | AI subsystem architecture: seams, feature flags, determinism, integration contracts | `.cursor/agents/ai-app-architect.md` | AI system design, integration planning, invariant alignment |
| data-scientist-agent | auto | Evaluation design, metrics, offline experiments planning, telemetry questions | `.cursor/agents/data-scientist-agent.md` | Evals, KPIs, A/B ideas, measurement plans |
| ml-engineer-agent | auto | Productionization: latency/cost budgets, caching, infra seams (policy-level) | `.cursor/agents/ml-engineer-agent.md` | Bringing AI to prod, performance budgets, reliability |
| nutritionist-agent | auto | Nutrition domain constraints, safe wording, non-medical boundaries | `.cursor/agents/nutritionist-agent.md` | Nutrition constraints, safe guidance, disclaimers |
| cbt-psychologist-agent | auto | CBT-inspired coaching language, safety boundaries (non-therapy) | `.cursor/agents/cbt-psychologist-agent.md` | Habit coaching, psychological safety, disclaimer enforcement |
| epistemology-discovery-agent | auto | Scientific discovery: falsifiable hypotheses, protocols, negative controls, promotion rules | `.cursor/agents/epistemology-discovery-agent.md` | Research-to-PR conversion, hypothesis/protocol design |
| physics-sensor-agent | auto | Sensor/physics priors for multimodal robustness and calibration (no “quantum magic”) | `.cursor/agents/physics-sensor-agent.md` | CV/voice robustness, calibration, sensor-grounded UQ |

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
