# 🧭 PulsePlate — Next Dialog Handoff

## 🎯 Purpose

This document is the **starting context for the next chat**.
Nothing before this file needs to be reread.

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
- Free BMI is first-class feature
- coverage ≥97%

---

## 🛠️ Working Process (MANDATORY)

### Before Every PR
1. Read REQUIRED docs (ENGINEERING_LESSONS.md, RUNBOOK_AGENT.md, nearest AGENTS.md)
2. Short plan discussion (goal, scope, non-goals)
3. Audit pass (Qoder mindset)
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
- Rewriting merged logic

---

## ✅ Outcome of Next Dialog

By the end of the next dialog:
- A concrete PR plan exists
- Scope is frozen
- First commit is ready

This document is binding.
