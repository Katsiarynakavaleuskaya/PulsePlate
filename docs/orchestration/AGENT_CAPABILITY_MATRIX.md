# Agent Capability Matrix

**Purpose:** Define recommended agent routing based on domain expertise.

**Status:** Advisory (not permissions) — final authority belongs to coordinator.

**Язык:** RU-first; английские термины — в скобках или `code` при первом упоминании.

---

## Overview

This matrix describes **recommended** agent assignments based on:
- Domain expertise
- Layer knowledge
- Review capabilities
- Delegation paths

**Important:** This is a **routing guide**, not a **permission system**.
Coordinator may assign agents outside their primary domain if justified.

**Cluster-first contract:** Coordinator resolves the canonical cluster from
`docs/orchestration/AGENT_ROUTING_GRAPH.md:39` and applies the routing rule in
`docs/orchestration/AGENT_ROUTING_GRAPH.md:85`; executable enforcement lives in
`scripts/orchestration/routing_graph_loader.py:205` and
`scripts/orchestration/route_with_telemetry.py:96`. These evidence anchors are
part of the contract and should be updated whenever the enforcement entrypoint
moves. This matrix remains an advisory guide for agent choice inside the routed
domain and does not define cluster ownership, permissions, or authority
boundaries.

---

## Agent Capabilities

Slug-first: first column = canonical agent slug (aligns with inventory and routing graph). Evidence: `docs/orchestration/AGENT_INVENTORY.md:12` (canonical slug list), `docs/orchestration/AGENT_ROUTING_GRAPH.md:36` (Domains → Agents table).

| Agent | Display | Primary Layers | Primary Domains | Can Review | Can Delegate To |
|-------|---------|----------------|-----------------|------------|-----------------|
| **agent-coordinator** | Coordinator | All | Routing, synthesis, orchestration | All agents | All agents |
| **backend-engineer** | Backend Engineer | `app/`, `core/` | FastAPI/core implementation, API contracts, policy-safe endpoints | Architecture, Security | Bug Hunter, Architecture |
| **frontend-engineer** | Frontend Engineer | `frontend/` | Web UI, thin-client rules, contract-safe updates | Architecture | Coordinator |
| **dev-operator** | Dev Operator | Terminal, CI | `make lint`, `make test-fast`, failure triage, evidence capture | Bug Hunter | Coordinator |
| **qa-engineer-agent** | QA Engineer | `tests/`, cross-surface | Acceptance gates, regression packs, release confidence, independent review | Backend, Frontend, Orchestration | Bug Hunter, Coordinator |
| **architecture-specialist** | Architecture | `core/`, `app/`, `frontend/`, `ios/` | Design patterns, invariants, layer boundaries | Bug Hunter, Security | AI Innovation, Bug Hunter |
| **bug-hunter** | Bug Hunter | `tests/`, CI | Test failures, coverage gaps, guard violations | Coordinator, Architecture | Architecture, Security |
| **security-auditor** | Security | All (cross-cutting) | Vulnerabilities, threats, hardening | Bug Hunter, Architecture | Architecture (for fixes) |
| **ai-app-architect** | AI App Architect | `app/`, `core/`, `providers/` | Integration seams, feature flags, determinism constraints | Architecture, Security | Coordinator |
| **ai-innovation-specialist** | AI Innovation | `core/`, `providers/` | LLM, RAG, R&D, prototypes | Architecture, Security | Bug Hunter (for testing) |
| **rag-systems-agent** | RAG Systems Agent | `core/`, `providers/` | Retrieval architecture, recursive verification, budgets/stop conditions | — | Coordinator, Security |
| **web-research-agent** | Web Research Agent | `docs/` (cross-cutting) | Web/OSS intake, evidence logs, ECR + scorecards | — | Coordinator |
| **data-scientist-agent** | Data Scientist | `docs/`, experiments (future) | Metrics, eval design, offline benchmarks | — | Coordinator, ML Engineer |
| **ml-engineer-agent** | ML Engineer | `providers/`, infra seams (future) | Productionization, latency/cost budgets, caching | Architecture | Coordinator |
| **bayesian-uq-agent** | Bayesian / UQ Agent | `core/`, `providers/` | Uncertainty quantification, calibration, reliability metrics | — | Coordinator, AI Innovation |
| **cv-agent** | CV Agent | `core/`, `providers/` | Food recognition pipeline, confidence scoring, privacy boundaries | — | Coordinator, Security |
| **philosophy-agent** | Philosophy Agent | `docs/` (cross-cutting) | Claim semantics, falsifiability, wellness language boundaries | — | Coordinator |
| **logic-agent** | Logic Agent | `docs/`, `core/` (cross-cutting) | Contradiction checks, invariants for recommendations | — | Coordinator, Bug Hunter (for testability) |
| **nutritionist-agent** | Nutritionist Agent | `docs/`, `core/` | Nutrition domain constraints, safe wording, rule definitions | — | Coordinator |
| **cbt-psychologist-agent** | CBT Psychologist Agent | `docs/` | CBT-inspired coaching boundaries, safety language | — | Coordinator |
| **epistemology-discovery-agent** | Epistemology / Discovery Agent | `docs/` (cross-cutting) | Hypotheses → protocols, negative controls, research-to-PR promotion rules | — | Coordinator, Data Scientist |
| **physics-sensor-agent** | Physics / Sensor Agent | `docs/` (cross-cutting) | Sensor priors, multimodal robustness, calibration protocols | — | Coordinator, CV Agent |
| **creative-designer** | Creative Designer | `frontend/`, `ios/`, marketing | UI/UX, visuals, brand | Marketing | Coordinator |
| **designer-artist-agent** | Designer / Artist Agent | `frontend/`, assets | Emblem/logo production: SVG geometry, Figma/Sora/Nano Banana packets | Creative Designer | Coordinator |
| **sora-prompt-engineer** | Sora Prompt Engineer | assets, `docs/sora/` | Sora prompt specs, anti-drift policy, visual QA gates | Creative Designer | Coordinator |
| **app-store-release-agent** | App Store Release | `ios/`, `frontend/`, release docs | App Store metadata, screenshots, submission packs, release readiness | QA Engineer, Marketing | Creative Designer, Marketing |
| **marketing-strategist** | Marketing | `docs/`, marketing materials | ASO/SEO, growth, positioning | Creative Designer | Coordinator |
| **wellness-analyst-agent** | Wellness Analyst | `docs/`, product strategy | Wellness opportunities, ethics notes, no-license entry ideas | — | Marketing, Business Strategist |
| **business-strategist-agent** | Business Strategist | `docs/`, roadmap | Market entry, monetization sequencing, low-capex strategy | — | Marketing, Coordinator |
| **ai-trend-reporter** | AI Trend Reporter | `docs/` | AI market reports (daily/weekly/monthly/quarterly), wellness GTM | — | Coordinator |
| **cursor-specialist-agent** | Cursor Specialist | `.cursor/agents/`, `scripts/`, `docs/orchestration/` | Task bootstrap, context-pack hygiene, workflow ergonomics | Orchestration, QA Engineer | Dev Operator, Coordinator |
| **tutor-mentor-agent** | Tutor / Mentor | `docs/`, onboarding artifacts | Explainability, onboarding, training guidance, role review | — | Coordinator |
| **generalpurpose** | General Purpose (mcp_task) | — | Research, code search, multi-step tasks | — | — |
| **explore** | Explore (mcp_task) | — | Fast codebase exploration, file/pattern search | — | — |
| **shell** | Shell (mcp_task) | — | Git, terminal, CI commands | — | — |
| **ci-watcher** | CI Watcher (mcp_task) | — | Watch GitHub CI, report pass/fail | — | — |

---

## Семантика review (Formal vs Advisory)

**Formal review** разрешён ТОЛЬКО агентам, перечисленным в колонке **Can Review**.
Все остальные участия — это **advisory consultation** (консультация), а не formal review.

(EN: Formal review is limited to agents listed in “Can Review”; others may only provide advisory consultation.)

---

## Routing Examples

### Example 1: Pure Backend Task

**Task:** “Implement new BMI calculation for pregnant users”

**Routing:**
- **Primary:** Architecture Specialist
  - Reason: Core domain logic + invariant (One BMI Engine)
  - Files: `core/bmi/engine.py`, `core/bmi/risk.py`
- **Secondary:** Bug Hunter
  - Reason: Coverage ≥97% + contract tests
  - Files: `tests/test_bmi_pregnant.py`
- **Review:** Security Auditor (optional)
  - Reason: Health data + calculation accuracy

---

### Example 2: Multi-Domain Task (Backend + Frontend)

**Task:** “Add soft paywall hook to BMI results page”

**Routing (Parallel Tracks):**
- **Track 1 (Backend):** Architecture Specialist
  - Subtask: Define soft paywall schema + API endpoint
  - Files: `app/schemas/bmi.py`, `app/routers/_helpers.py`
- **Track 2 (Frontend):** Creative Designer
  - Subtask: Design paywall UI component
  - Files: `frontend/src/components/SoftPaywall.tsx`
  - Depends on: Track 1 (OpenAPI schema ready)
- **Track 3 (Tests):** Bug Hunter
  - Subtask: Contract tests for soft paywall
  - Files: `tests/test_soft_paywall_contract.py`
  - Depends on: Track 1 + Track 2

Coordinator synthesizes all tracks at final Sync Point.

---

### Example 3: Research / R&D задача

**Задача:** “Оценить RAG для персонализации недельного плана”

**Роутинг:**
- **Primary:** AI Innovation Specialist
  Deliverable: ADR + PoC (dev-only)

- **Advisory consultation:** Architecture Specialist
  Цель: проверить соответствие архитектурным инвариантам
  Статус: ❗ консультация, НЕ formal review

- **Advisory consultation:** Security Auditor
  Цель: оценить риски (data leakage, prompt injection)
  Статус: ❗ консультация, НЕ formal review

**Formal Review:**
- ❌ Не назначается (R&D задача, dev-only)

**Rationale:**
R&D задачи могут получать консультации от других доменов,
но formal review выполняется **только агентами, разрешёнными матрицей**.

---

## Flexibility Rules

Coordinator may assign agents outside primary domain if:

1. Primary agent unavailable
2. Cross-domain expertise needed
3. Learning opportunity (explicitly documented)

**Exception process:**
- Coordinator documents the reason in Task Analysis
- Coordinator provides extra context/handoff to the non-primary agent
- Coordinator assigns a reviewer from the primary domain when needed

---

## Authority Clarification

**Capability Matrix = recommended routing.**
**Final authority = `agent-coordinator`.**

This matrix does not grant “permission” or “rights” to agents.
It exists to help the coordinator route work efficiently.

Skill selection is a separate step and is governed by
`docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`.

---

## Related Documentation

- **Routing Graph (SoT):** `docs/orchestration/AGENT_ROUTING_GRAPH.md`
- **Skill Routing Policy:** `docs/orchestration/AGENT_SKILL_ROUTING_POLICY.md`
- Coordinator: `.cursor/agents/agent-coordinator.md`
- Handoff Protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Context Map: `docs/orchestration/AGENT_CONTEXT_MAP.md`

---

**Last updated:** 2026-03-07 (PR #996)
**Status:** Advisory
