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

**Primary (always required):**
- `AGENTS.md` (root) — invariants, policies, quality gates
- `RUNBOOK_AGENT.md` — operational procedures
- `docs/orchestration/*` — workflow + templates + protocols

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

## Pre-flight Context Verification (Coordinator)

Use this checklist before routing.

```markdown
## Pre-flight Context Verification

- [ ] Root `AGENTS.md` loaded
- [ ] `RUNBOOK_AGENT.md` loaded
- [ ] All affected module `AGENTS.md` loaded
- [ ] Contract docs loaded (only if API/schema changes)
- [ ] Relevant guard tests identified
```

**Failure condition:** if any required item is missing → stop and request context (do not guess).

---

## Related Documentation

- `docs/orchestration/workflow.md` (canonical workflow)
- `.cursor/agents/agent-coordinator.md` (coordinator agent configuration)

---

**Last updated:** 2026-02-03 (PR-634)
**Status:** Canonical
