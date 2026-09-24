# Task Analysis Template

**Copy this template for each new task.**

---

## Task Analysis

**Task:** [Brief description of what needs to be done]

**Domain(s):** [AI/ML | Architecture | Bugs | Design | Marketing | Security | Multiple]

**Complexity:** [Simple | Moderate | Complex]

**Priority:** [P0 | P1 | P2]

- **Priority track (P0-A / P0-B / P1):** ____ _(see [AGENTS.md](../../AGENTS.md) — Release readiness priorities)_

**Expected Outcome:** [What success looks like - specific, measurable]

**Goal Owner:** [Human owner of the accepted goal]

**Accepted Criteria Reference / Version:** [Stable anchor in this analysis or lane runbook]

**Original Requirements / Complete DoD Reference:** [Existing source and version]

**Before → After:** [Observed baseline → intended observable result]

**Review Depth:** [Validated Teleology full/compact, or not supplied]

Follow [Goal-to-outcome review](workflow.md#goal-to-outcome-review), including
its user-path rubric, grouping and untrusted-evidence procedure.

**User Impact / Preserved Semantics:** [Apply the linked rubric to affected UI, backend/user behavior, marketing or other user-facing promise, and policy/legal text; for a mechanical change explain what user-visible meaning is preserved]

**Required Human Acceptance:** [Before work, name which owner decisions and visual checkpoints apply, or give a reasoned N/A for each. Required decisions need explicit affirmative owner acceptance of the exact shown state/version; rejection is not_achieved. A new substantial visual choice requires proposal acceptance before implementation and actual acceptance before completion; a minor existing-visual change may require final acceptance alone. Plan any needed professional review of current material separately, including its completed outcome; it cannot replace owner affirmation.]

| Criterion reference | Original requirement / DoD references | Observable acceptance criterion | Planned evidence |
| --- | --- | --- | --- |
| [Stable criterion ID] | [Explicit source items covered] | [Expected result] | [Test, observation or reviewed artifact] |

**Rollback / Recovery:** [Existing reversal or compensation plan]

**Goal Change Record:** [Explicit owner change and previous reference, or none]

**Material / Counterexample Recheck:** [Affected criterion IDs, old evidence made stale, and planned targeted recheck; or none yet]

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
