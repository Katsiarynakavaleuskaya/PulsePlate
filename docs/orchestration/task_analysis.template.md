# Task Analysis Template

**Copy this template for each new task.**

---

## Task Analysis

**Task:** [Brief description of what needs to be done]

**Domain(s):** [AI/ML | Architecture | Bugs | Design | Marketing | Security | Multiple]

**Complexity:** [Simple | Moderate | Complex]

**Priority:** [P0 | P1 | P2]

**Expected Outcome:** [What success looks like - specific, measurable]

**Invariants Affected:**
- [ ] One BMI Engine
- [ ] Thin HTTP Adapter Policy
- [ ] Layer Separation
- [ ] Contract-First
- [ ] Other: [specify]

**Domain hints (pick if relevant; links-only):**
- `core/bmi/*`: One BMI Engine + guards-first (see `AGENTS.md`, `docs/BMI_CANONICAL_HANDOFF.md`)
- `app/routers/*`: OpenAPI determinism + `response_model` hygiene + import hygiene (see `AGENTS.md`)
- `frontend/` or `ios/`: thin-client only (no BMI logic on clients; DTO/contract-first) (see `frontend/AGENTS.md`,
  `ios/AGENTS.md`)

**Risks:**
1. [Risk description and mitigation]

**Proposed Approach:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Agent Assignment:**
- **Primary:** [agent-name] - [reason]
- **Secondary:** [agent-name] - [reason] (if multi-agent)
- **Dependencies:** [what needs to happen first]

**Constraints:**
- [Constraint 1]
- [Constraint 2]

---

**Analysis by:** agent-coordinator
**Date:** [YYYY-MM-DD]
