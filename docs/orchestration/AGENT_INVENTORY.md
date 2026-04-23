# Agent Inventory (Canonical)

**Purpose:** Single source of truth for all PulsePlate agents and their functions.
**Status:** Reference — routing uses `AGENT_ROUTING_GRAPH.md` and `AGENT_CAPABILITY_MATRIX.md`.

---

## Orchestration

| Agent | Function |
|-------|----------|
| **agent-coordinator** | Routes tasks to agents, synthesizes multi-agent work, enforces quality gates, pre-flight checklist |

---

## Execution & Quality

| Agent | Function |
|-------|----------|
| **backend-engineer** | FastAPI/core implementation, API contracts, policy-safe endpoints |
| **frontend-engineer** | Web UI, frontend contract-safe updates, thin-client rules |
| **bug-hunter** | Bug detection, CI failures, guard violations, coverage gaps |
| **dev-operator** | Terminal-first: `make lint`, `make test-fast`, failure triage, evidence capture |
| **qa-engineer-agent** | Acceptance criteria, regression packs, release-readiness verification, independent review |

---

## Architecture & Security

| Agent | Function |
|-------|----------|
| **architecture-specialist** | Code structure, invariants, design patterns, layer boundaries |
| **security-auditor** | Security reviews, vulnerabilities, threat modeling, compliance |
| **ai-app-architect** | AI subsystem seams, feature flags, determinism, integration contracts |

---

## AI / ML / Research

| Agent | Function |
|-------|----------|
| **ai-innovation-specialist** | AI/ML features, RAG, CV, LLM integration, research-backed innovations |
| **rag-systems-agent** | RAG architecture, recursive verification, grounding contracts |
| **web-research-agent** | Web/OSS intake, evidence logs, ECR + scorecards |
| **data-scientist-agent** | Evals, metrics, offline experiments, measurement plans |
| **ml-engineer-agent** | Productionization, latency/cost budgets, caching, infra seams |
| **bayesian-uq-agent** | Uncertainty quantification, calibration, confidence contracts |
| **cv-agent** | CV pipeline contracts (photo→items→confidence→nutrition); graph-primary for routing domain `cv` |

---

## Domain Experts (Safety / Logic)

| Agent | Function |
|-------|----------|
| **philosophy-agent** | Claim semantics, falsifiability, wellness language boundaries |
| **logic-agent** | Contradiction checks, invariants for recommendations |
| **nutritionist-agent** | Nutrition constraints, safe wording, non-medical boundaries |
| **cbt-psychologist-agent** | CBT-inspired coaching boundaries, psychological safety |
| **epistemology-discovery-agent** | Hypotheses→protocols, negative controls, research-to-PR promotion |
| **physics-sensor-agent** | Sensor priors, multimodal robustness, calibration protocols |

---

## Design & Marketing

| Agent | Function |
|-------|----------|
| **creative-designer** | UI/UX, brand assets, App Store visuals, marketing creatives |
| **designer-artist-agent** | Emblem/logo production: SVG geometry, Figma/Sora/Nano Banana packets |
| **sora-prompt-engineer** | Sora prompt specs, anti-drift policy, visual QA gates |
| **app-store-release-agent** | App Store metadata, submission packaging, release checklists, asset readiness |
| **marketing-strategist** | ASO/SEO, growth, positioning, conversion optimization |
| **wellness-analyst-agent** | Wellness opportunity analysis, low-capex product ideas, ethics/regulatory notes |
| **business-strategist-agent** | Director-level business ownership: portfolio framing, B2B packaging, monetization sequencing, investor/partner narrative governance, KPI ownership |
| **ai-trend-reporter** | AI market reports (daily/weekly/monthly/quarterly), wellness GTM |

---

## Enablement & Workflow

| Agent | Function |
|-------|----------|
| **cursor-specialist-agent** | Coordinator bootstrap ergonomics, context-pack hygiene, prompt packet conventions |
| **tutor-mentor-agent** | Onboarding explanations, role review, internal enablement guidance |

---

## Utility (mcp_task)

| Type | Function |
|------|----------|
| **generalPurpose** | Research, code search, multi-step tasks |
| **explore** | Fast codebase exploration, file/pattern search |
| **shell** | Git, terminal, CI commands |
| **ci-watcher** | Watch GitHub CI, report pass/fail |

---

## Canonical Sources

- Agent files: `.cursor/agents/*.md`
- Index: `docs/agents/index.md`
- Capability matrix: `docs/orchestration/AGENT_CAPABILITY_MATRIX.md`
- Routing graph: `docs/orchestration/AGENT_ROUTING_GRAPH.md`

---

**Last updated:** 2026-03-07 (PR #996)
