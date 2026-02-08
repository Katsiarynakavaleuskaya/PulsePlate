# Agent Context Map

**Purpose:** Define which files each agent must load before starting work.

**Status:** Canonical (PR-634)

---

## Overview

Every agent operates with a **context window** — the set of files/rules it can see.
This map reduces “missing context” failures by making required inputs explicit.

**Rule of thumb:** if required context is missing, execution quality degrades. The coordinator must stop and request context rather than guess.

---

## Context Requirements by Agent

### Coordinator (`agent-coordinator`)

**Обязательный минимум (всегда):**
- `AGENTS.md` (root) — invariants, policies, quality gates
- `RUNBOOK_AGENT.md` — operational procedures

**Условно (только если нужно):**
- `docs/orchestration/*` — **только** когда:
  - задача multi-agent (handoff / parallel / dialogue),
  - требуется формальное применение workflow,
  - есть неоднозначность и нужен протокол принятия решения,
  - или изменяется сама orchestration-layer.

(EN: Orchestration docs are conditional; load them only for multi-agent or when the workflow is required.)

**Secondary (task-dependent):**
- Nearest module `AGENTS.md` for every affected module:
  - `core/AGENTS.md`
  - `app/AGENTS.md`
  - `frontend/AGENTS.md`
  - `ios/AGENTS.md`
  - `tests/AGENTS.md`
  - `scripts/AGENTS.md`
  - `providers/AGENTS.md`
  - `alembic/AGENTS.md`
  - `deploy/AGENTS.md`

**Contract docs (only if API/schema changes):**
- `docs/contracts/PRODUCT_TIER_MAP.md`
- `docs/contracts/API_CANONICAL_MAP.md`
- `docs/contracts/soft_paywall.md`
- `docs/contracts/OPENAPI_VISIBILITY_MATRIX.md`

**Pre-flight rule:** Coordinator MUST load root `AGENTS.md` and all affected module `AGENTS.md` before routing.

---

### Architecture Specialist (`architecture-specialist`)

**Primary:**
- `AGENTS.md` (root)
- Affected module `AGENTS.md` (always; at minimum `core/AGENTS.md` and/or `app/AGENTS.md`)

**Must know (high-level):**
- Layer boundaries and invariants (e.g., One BMI Engine, Thin HTTP Adapter Policy)
- Contract-first design
- OpenAPI determinism requirements (if touching API surface)

**Guard tests to respect (if applicable):**
- `tests/test_repo_policy_guards.py`
- `tests/test_openapi_determinism.py`
- `tests/test_no_bmi_logic_in_paywall.py`

---

### Bug Hunter (`bug-hunter`)

**Primary:**
- `AGENTS.md` (root) — quality gates + test policies
- `RUNBOOK_AGENT.md` — procedures for CI/testing failures
- `tests/AGENTS.md` — test-scoped rules (if touching tests)

**Must know:**
- Coverage and diff-coverage requirements
- Determinism and anti-flake rules
- Guard-test patterns and “expected-red” exceptions (when explicitly applicable)

---

### AI Innovation Specialist (`ai-innovation-specialist`)

**Primary:**
- `AGENTS.md` (root)
- `core/AGENTS.md` (domain rules)
- `providers/AGENTS.md` (provider integration rules)

**Must know:**
- Prototype vs production rules
- LLM integration constraints and safety requirements

---

### Security Auditor (`security-auditor`)

**Primary:**
- `AGENTS.md` (root) — security invariants and process
- Nearest module `AGENTS.md` for all affected modules (cross-cutting)
- `RUNBOOK_AGENT.md` (procedural context)

**Must know:**
- Trust boundaries and attack surface for the changed area
- Guard tests / invariants relevant to security

---

### Marketing Strategist (`marketing-strategist`)

**Primary (task-dependent):**
- `AGENTS.md` (root) — product tier definitions and constraints
- `docs/contracts/PRODUCT_TIER_MAP.md` — tier mapping (FREE/PRO/VIP)
- `frontend/AGENTS.md` / `ios/AGENTS.md` — if proposing UI/UX changes

---

### Creative Designer (`creative-designer`)

**Primary (task-dependent):**
- `frontend/AGENTS.md` — web UI constraints
- `ios/AGENTS.md` — iOS UI constraints
- `AGENTS.md` (root) — accessibility + thin-client guardrails (where applicable)

---

### Philosophy Agent (`philosophy-agent`)

**Primary:**
- `AGENTS.md` (root) — safety boundaries + orchestration rules
- `docs/orchestration/*` — when running formal multi-agent workflow

**Must know:**
- Wellness-only positioning (no medical / no therapy claims)
- Evidence contract (claims must be evidence-backed in docs/tests)

---

### Logic Agent (`logic-agent`)

**Primary:**
- `AGENTS.md` (root) — invariants + safety boundaries
- `docs/orchestration/AGENT_HANDOFF_PROTOCOL.md` — structured returns to coordinator

**Must know:**
- Which layers are SoT for domain logic (`core/`) vs adapters (`app/`, clients)
- Guard/determinism expectations for future runtime PRs (do not implement here)

---

### Bayesian / UQ Agent (`bayesian-uq-agent`)

**Primary:**
- `AGENTS.md` (root)
- `core/AGENTS.md` (if proposing domain-facing uncertainty contracts)

**Must know:**
- Determinism and testability requirements (future PRs must have deterministic tests)
- “High uncertainty → degrade” policy (safety-first)

---

### RAG Systems Agent (`rag-systems-agent`)

**Primary:**
- `AGENTS.md` (root) — rate limit + quota policies for LLM endpoints (future runtime PRs)
- `providers/AGENTS.md` (provider integration rules, if applicable)

**Must know:**
- Cost-abuse risk: recursive amplification must be bounded (budgets/stop conditions)
- External/retrieved content is untrusted (prompt injection posture)

---

### CV Agent (`cv-agent`)

**Primary:**
- `AGENTS.md` (root) — privacy and safety boundaries
- `core/AGENTS.md` (domain logic boundaries; no client-side business logic)

**Must know:**
- Uncertainty/confidence must be explicit for recognition outputs
- Privacy/logging constraints for user images (policy-only here)

---

### AI Application Architect (`ai-app-architect`)

**Primary:**
- `AGENTS.md` (root) — invariants + OpenAPI determinism constraints
- `app/AGENTS.md` and `core/AGENTS.md` (if proposing integration seams)

**Must know:**
- Layer boundaries: thin routers/adapters; domain logic in `core/`
- Feature-flag gating order (feature checks before quota consumption, for future PRs)

---

### Data Scientist (`data-scientist-agent`)

**Primary (task-dependent):**
- `AGENTS.md` (root)
- `docs/roadmap/BACKLOG_LEDGER.md` (if proposing deferred experiment tracks)

**Must know:**
- Metrics definitions must be testable/auditable (avoid vague claims)
- Privacy: anonymization/retention policy must be explicit before telemetry work

---

### ML Engineer (`ml-engineer-agent`)

**Primary:**
- `AGENTS.md` (root) — determinism + performance expectations
- `providers/AGENTS.md` (if packaging model/provider calls)

**Must know:**
- Latency/cost budgets must be explicit for recursive methods (future runtime PRs)
- CI/test determinism (no flaky retrieval/ordering)

---

### Nutritionist Agent (`nutritionist-agent`)

**Primary:**
- `AGENTS.md` (root) — wellness-only boundaries
- `core/AGENTS.md` (domain constraints live in `core/`)

**Must know:**
- Forbidden medical claims; required disclaimers
- Domain constraints must be expressed as rules/constraints, not vibes

---

### CBT Psychologist Agent (`cbt-psychologist-agent`)

**Primary:**
- `AGENTS.md` (root) — wellness-only boundaries; no therapy positioning
- `docs/contracts/*` (if touching user-facing coaching contract text)

**Must know:**
- Psychological safety language constraints and escalation boundaries
- High-uncertainty behavior: clarify, soften, avoid prescriptive claims

---

## Verification Protocol

Канонический checklist не дублируем.
См. `docs/orchestration/workflow.md` → “Canonical Pre-flight Checklist (SoT)”.

---

## Related Documentation

- `docs/orchestration/workflow.md` (canonical workflow)
- `.cursor/agents/agent-coordinator.md` (coordinator agent configuration)

---

**Last updated:** 2026-02-03 (PR-634)
**Status:** Canonical
