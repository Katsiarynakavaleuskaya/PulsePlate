# Definition of Done (DoD) Template

**Copy this template before PR merge to verify completion.**

---

## Definition of Done

**PR:** [PR number or branch name]

**Task:** [Original task description]

### Scope

- [ ] Scope respected (dev-only, no runtime impact if applicable)
- [ ] No scope creep (P1/P2 items postponed → `BACKLOG_LEDGER.md`)

### Goal Outcome

Follow [Goal-to-outcome review](workflow.md#goal-to-outcome-review).

**Accepted Criteria Reference / Version:** [Same reference used by ordinary QA]

**Work Review Reference / Reviewed Material:** [Ordinary QA reviewer, exact current material/version, criterion evidence and outcome assessment]

- [ ] Every original requirement and DoD item is represented in the review
- [ ] Every criterion has observed evidence or an explicit evidence gap and outcome
- [ ] Every original requirement and DoD item is explicitly covered by an individually achieved criterion with evidence before claiming overall completion
- [ ] Any partial, unknown or not_achieved criterion prevents an overall completion claim
- [ ] Material changes and new counterexamples have targeted rechecks; stale evidence is not counted as achieved
- [ ] Coordinator recorded required owner decisions and visual checkpoints before work; a new substantial visual choice has distinct affirmative proposal-before-implementation and actual-before-completion decisions, while a minor existing-visual change may need final acceptance alone with reasoned proposal N/A
- [ ] Every required visual, legal or other owner decision is explicitly affirmative for the exact shown state/version; missing, ambiguous or stale is unknown, explicit rejection is not_achieved, and reasoned N/A applies only when no decision is required
- [ ] Proven skipped required visual order is not_achieved; needed professional review has recorded completion and outcome for current material before achieved, missing/stale review is unknown, adverse review prevents achieved and requires correction; it cannot replace owner affirmation or other criterion evidence

### Code Quality

See canonical Quality Gates: `RUNBOOK_AGENT.md` (Quality Gates section)

- [ ] Quality gates pass (see RUNBOOK_AGENT.md for authoritative checklist)
- [ ] No dead code added

### Documentation

- [ ] `AGENTS.md` updated (if workflow/rules changed)
- [ ] `RUNBOOK_AGENT.md` updated (if procedures changed)
- [ ] Module-specific `AGENTS.md` updated (if applicable)
- [ ] `BACKLOG_LEDGER.md` updated (postponed items recorded)

### Process

- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] CI green (if applicable)
- [ ] PR description complete (scope, non-scope, dev-only disclaimer if applicable)

### Security & Architecture

- [ ] No architectural violations (guard tests)
- [ ] No security issues (bandit/pip-audit if applicable)
- [ ] Layer boundaries respected
- [ ] Invariants maintained

---

**Verified by:** [agent-coordinator | reviewer]
**Date:** [YYYY-MM-DD]
