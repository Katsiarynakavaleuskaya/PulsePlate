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

**Work Review Reference / Reviewed Material:** [Criterion evidence and outcome assessment]

- [ ] Every original requirement and DoD item is represented in the review
- [ ] Every criterion has observed evidence or an explicit evidence gap and outcome
- [ ] Every material criterion is individually achieved with evidence before claiming overall completion
- [ ] Any partial, unknown or not_achieved criterion prevents an overall completion claim

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
