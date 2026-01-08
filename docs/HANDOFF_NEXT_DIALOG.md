# 🧭 PulsePlate — Next Dialog Handoff

## 🎯 Purpose

This document is the **starting context for the next chat**.
Nothing before this file needs to be reread.

**Related handoff documents:**
- [HANDOFF_PROJECT_STATUS_2026-01.md](./HANDOFF_PROJECT_STATUS_2026-01.md) — Canonical project state snapshot
- [NEXT_PR_BOOTSTRAP.md](./NEXT_PR_BOOTSTRAP.md) — Process for starting the next PR
- [PR_493_SUMMARY.md](./PR_493_SUMMARY.md) — Summary of this handoff PR

---

## 🟢 Starting Assumptions

- All BMI canonical work is merged
- Visualization contract is documented
- i18n strategy RU / EN / ES is fixed
- CI and prod are stable

---

## 🧱 Architectural Invariants (Do Not Re-discuss)

- One BMI Engine
- child ≠ teen
- visualization optional
- Free BMI is a first-class feature.
- coverage ≥97%

---

## 🛠️ Working Process (MANDATORY)

### Before Every PR
1. Read REQUIRED docs:
   - ENGINEERING_LESSONS.md — project lessons and hard-won invariants
   - RUNBOOK_AGENT.md — agent workflow and CI/debug playbooks
   - AGENTS.md — nearest context-specific agent guidance
2. Short plan discussion (goal, scope, non-goals)
3. Audit pass (Qoder mindset — pre-implementation audit of invariants, risks, and scope; see ENGINEERING_LESSONS.md / RUNBOOK_AGENT.md)
4. Confirm no invariant violations

### During Implementation
- Cursor-style incremental commits
- No speculative refactors
- Tests first or together with code

### Before Merge
- Diff-cover checked
- CodeRabbit comments addressed or explicitly deferred
- Clear PR summary written

---

## 🧭 Allowed Questions in Next Dialog

- Which next BMI surface to extend?
- Visualization vs targets priority
- API vs internal engine work

❌ Not allowed:
- Reopening BMI architecture decisions
- Rewriting merged logic (functional rewrites; refactoring or optimizations require explicit justification and a dedicated PR)

---

## ✅ Outcome of Next Dialog

By the end of the next dialog:
- A concrete PR plan exists
- Scope is frozen
- First commit is ready

This document is binding.
