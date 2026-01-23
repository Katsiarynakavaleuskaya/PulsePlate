# Definition of Done (DoD) Template

**Copy this template before PR merge to verify completion.**

---

## Definition of Done

**PR:** [PR number or branch name]

**Task:** [Original task description]

### Scope

- [ ] Scope respected (dev-only, no runtime impact if applicable)
- [ ] No scope creep (P1/P2 items postponed → `BACKLOG_LEDGER.md`)

### Code Quality

- [ ] `make verify` green (lint → typecheck → test-fast → diff-cov ≥97%)
- [ ] Guard tests pass (architectural invariants)
- [ ] Coverage ≥97% (total + diff-coverage)
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
