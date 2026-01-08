# 🚀 Next PR Bootstrap Plan

## 🎯 Objective

Start the next development PR
**without architectural drift or scope creep**.

---

## 🧩 Allowed Focus Areas (Choose ONE per PR)

- BMI calculations (engine-level)
- BMI visualization
- BMI targets / interpretation
- i18n extensions
- API contracts

❌ No mixed PRs.

---

## 🛠️ PR Preparation Checklist

### 1. Scope
- What is added?
- What is explicitly NOT touched?

### 2. Risks
- Does this touch BMI math?
- Does this affect public API?
- Could this reduce coverage?

### 3. Tests
- What new behavior is tested?
- What invariants are guarded?

---

## 🧪 CI Rules

- Overall coverage ≥97%
- Diff-cover: 100% for PR-touched lines (hard gate)
- No new type: ignore without explanation (mandatory per project CI)
- No new test ignores (skip/xfail) without justification (mandatory per project CI)
- No flaky tests
- No test-only logic leaks

---

## 🧠 Review Strategy

- CodeRabbit: logic & duplication
- Cursor: structure & clarity
- Human: invariants & intent

---

## 🏁 Definition of Done

- PR merged
- Handoff updated if needed
- Next PR can start immediately

---

## 🔜 Candidate Directions for Next PR

- BMI visualization refinement
- Targets & recommendations layer
- Extended BMI interpretation logic
