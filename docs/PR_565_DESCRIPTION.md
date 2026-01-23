# PR-565: Dev Orchestrator Layer (Phase 1 - P0)

**Type:** `docs-only` / `dev-process`
**Runtime Impact:** ❌ **None** (explicitly dev-only)
**Scope:** Phase 1 (P0) only

> This PR introduces a **dev-only orchestration layer** for coordinating Cursor agents.
> It does **not** affect runtime, product behavior, or delivery paths.

---

## 🎯 Purpose

Introduce **Dev Orchestrator Layer** to structure task start, agent coordination, and systematic tracking of postponed work.

**This PR implements Phase 1 (P0) only** — core orchestration templates and documentation updates.

---

## ✅ What's Included (Phase 1 - P0)

### New Files

1. **`docs/orchestration/workflow.md`**
   - Canonical workflow: Task → Task Analysis → Agent Assignment → Work Review → Synthesis → DoD
   - Integration points with AGENTS.md and RUNBOOK_AGENT.md

2. **Templates (copy-paste ready):**
   - `docs/orchestration/task_analysis.template.md`
   - `docs/orchestration/work_review.template.md`
   - `docs/orchestration/synthesis.template.md`
   - `docs/orchestration/dod.template.md`

### Updated Files

1. **`AGENTS.md`**
   - Added "Agent Coordination (Coordinator-First Rule)" section
   - Links to orchestration templates
   - Rule: Any new task MUST start with `agent-coordinator`
   - Rule: Postponed items MUST be recorded in `BACKLOG_LEDGER.md`

2. **`RUNBOOK_AGENT.md`**
   - Updated "Agent Coordination" section with:
     - Links to orchestration templates
     - Instructions for starting tasks
     - DoD verification steps

3. **`docs/roadmap/BACKLOG_LEDGER.md`**
   - Added postponed items:
     - PR-566 (Phase 2): Coordinator cleanup (P1)
     - PR-567 (Phase 3): Agent index + model rationale (P2)

---

## ❌ What's NOT Included (Explicitly Postponed)

**Phase 2 (P1) — Postponed to PR-566:**
- Coordinator cleanup (reduce duplication in `agent-coordinator.md`)
- See: `docs/roadmap/BACKLOG_LEDGER.md` (PR-566)

**Phase 3 (P2) — Postponed to PR-567:**
- Agent index (`docs/agents/index.md`)
- Model selection rationale documentation
- See: `docs/roadmap/BACKLOG_LEDGER.md` (PR-567)

---

## 📋 Definition of Done

- [x] All changes are **docs-only** (no runtime code)
- [x] `make verify` green (lint → typecheck → test-fast → diff-cov ≥97%)
- [x] markdownlint OK (no errors in new files)
- [x] `AGENTS.md` and `RUNBOOK_AGENT.md` synchronized
- [x] Postponed items recorded in `BACKLOG_LEDGER.md`
- [x] PR description contains dev-only disclaimer

---

## 🔗 Related

- **Audit:** `docs/audit/PR_565_DEV_ORCHESTRATOR_AUDIT.md`
- **Context Handoff:** `docs/CONTEXT_HANDOFF_2026-01-23.md`
- **Coordinator Agent:** `.cursor/agents/agent-coordinator.md`

---

## 📝 Deferred / Follow-ups

**Postponed to separate PRs:**

1. **PR-566 (Phase 2): Coordinator cleanup**
   - Reduce duplication in `agent-coordinator.md` (capabilities descriptions)
   - Replace full descriptions with links to agent files
   - See: `docs/roadmap/BACKLOG_LEDGER.md` (PR-566)

2. **PR-567 (Phase 3): Agent index + model rationale**
   - Create `docs/agents/index.md` with agent capabilities matrix
   - Document model selection rationale in each agent file
   - See: `docs/roadmap/BACKLOG_LEDGER.md` (PR-567)

---

## 🚀 After Merge

**New canonical process:**
- Any new task MUST start with `agent-coordinator` for task analysis
- Use orchestration templates for structured workflow
- Postponed items MUST be recorded in `BACKLOG_LEDGER.md` immediately

**Next PRs:**
- PR-566: Coordinator cleanup (Phase 2)
- PR-567: Agent index + model rationale (Phase 3)

---

**Note:** Coordinator behavior is unchanged in this PR; cleanup and deduplication are explicitly deferred to PR-566.

**Last updated:** 2026-01-23
**Status:** ✅ Ready for review
