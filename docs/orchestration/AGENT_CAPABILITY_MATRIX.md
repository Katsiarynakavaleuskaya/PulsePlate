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

---

## Agent Capabilities

| Agent | Primary Layers | Primary Domains | Can Review | Can Delegate To |
|-------|----------------|-----------------|------------|-----------------|
| **Coordinator** | All | Routing, synthesis, orchestration | All agents | All agents |
| **Architecture** | `core/`, `app/`, `frontend/`, `ios/` | Design patterns, invariants, layer boundaries | Bug Hunter, Security | AI Innovation, Bug Hunter |
| **Bug Hunter** | `tests/`, CI | Test failures, coverage gaps, guard violations | Coordinator, Architecture | Architecture, Security |
| **AI Innovation** | `core/`, `providers/` | LLM, RAG, R&D, prototypes | Architecture, Security | Bug Hunter (for testing) |
| **Security** | All (cross-cutting) | Vulnerabilities, threats, hardening | Bug Hunter, Architecture | Architecture (for fixes) |
| **Marketing** | `docs/`, marketing materials | ASO/SEO, growth, positioning | Creative Designer | Coordinator |
| **Creative Designer** | `frontend/`, `ios/`, marketing | UI/UX, visuals, brand | Marketing | Coordinator |
| **Философский агент (`Philosophy Agent`)** | `docs/` (cross-cutting) | Claim semantics, falsifiability, wellness language boundaries | — | Coordinator |
| **Логический агент (`Logic Agent`)** | `docs/`, `core/` (cross-cutting) | Contradiction checks, invariants for recommendations | — | Coordinator, Bug Hunter (for testability) |
| **Байесовский агент / UQ (`Bayesian / UQ Agent`)** | `core/`, `providers/` | Uncertainty quantification, calibration, reliability metrics | — | Coordinator, AI Innovation |
| **RAG-агент (`RAG Systems Agent`)** | `core/`, `providers/` | Retrieval architecture, recursive verification, budgets/stop conditions | — | Coordinator, Security |
| **Web Research Agent** | `docs/` (cross-cutting) | Web/OSS intake, evidence logs, ECR + scorecards | — | Coordinator |
| **CV-агент (`CV Agent`)** | `core/`, `providers/` | Food recognition pipeline, confidence scoring, privacy boundaries | — | Coordinator, Security |
| **Архитектор AI-приложений (`AI App Architect`)** | `app/`, `core/`, `providers/` | Integration seams, feature flags, determinism constraints | Architecture, Security | Coordinator |
| **Дата-саентист (`Data Scientist`)** | `docs/`, experiments (future) | Metrics, eval design, offline benchmarks | — | Coordinator, ML Engineer |
| **ML-инженер (`ML Engineer`)** | `providers/`, infra seams (future) | Productionization, latency/cost budgets, caching | Architecture | Coordinator |
| **Нутрициолог-агент (`Nutritionist Agent`)** | `docs/`, `core/` | Nutrition domain constraints, safe wording, rule definitions | — | Coordinator |
| **CBT-психолог-агент (`CBT Psychologist Agent`)** | `docs/` | CBT-inspired coaching boundaries, safety language | — | Coordinator |
| **Эпистемолог-агент / Discovery (`Epistemology / Discovery Agent`)** | `docs/` (cross-cutting) | Hypotheses → protocols, negative controls, research-to-PR promotion rules | — | Coordinator, Data Scientist |
| **Физик-агент / Сенсоры (`Physics / Sensor Agent`)** | `docs/` (cross-cutting) | Sensor priors, multimodal robustness, calibration protocols | — | Coordinator, CV Agent |

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

---

## Related Documentation

- **Routing Graph (SoT):** `docs/orchestration/AGENT_ROUTING_GRAPH.md`
- Coordinator: `.cursor/agents/agent-coordinator.md`
- Handoff Protocol: `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md`
- Context Map: `docs/orchestration/AGENT_CONTEXT_MAP.md`

---

**Last updated:** 2026-02-10 (PR TBD)
**Status:** Advisory
