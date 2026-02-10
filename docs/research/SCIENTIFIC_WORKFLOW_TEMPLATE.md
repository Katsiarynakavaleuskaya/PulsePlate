# Scientific Workflow Template (Research → Decision → Promotion)

**Purpose:** Provide a falsifiable, reproducible template for turning ideas into decision-ready research and then into
repo artifacts (PRs, tests, ledger entries).

**Status:** Canonical (dev-only). Complements:

- Orchestrator workflow: `docs/orchestration/workflow.md`
- Research track (web/OSS): `docs/orchestration/RESEARCH_TRACK_PROTOCOL.md`

---

## Template (copy/paste)

### Title

`<Short name of the research question>`

### Decision question (required)

What decision will this research enable?

### Hypothesis (required)

What do we believe will be true after we implement the change?

### Success criteria (required)

- [ ] Criterion 1 (measurable)
- [ ] Criterion 2 (measurable)
- [ ] Criterion 3 (measurable)

### Constraints (required)

- Determinism constraints (tests must be deterministic; no time-window flake)
- Budget constraints (sources/evidence/timebox/calls)
- Scope constraints (docs-only vs runtime PR)
- Safety constraints (wellness boundary, privacy boundary)

### Methods (required)

How will we test the hypothesis?

- **Repo evidence**: file:line pointers, existing tests/guards, existing protocols
- **External evidence** (optional): only via Research Track protocol + evidence log
- **Prototype plan** (optional): minimal sandbox steps, with stop conditions

### Negative controls (required)

How do we ensure we’re not “seeing what we want to see”?

- Counter-example inputs
- Known failure modes
- Alternative explanations to rule out

### Risks + mitigations (required)

- Risk 1 → mitigation
- Risk 2 → mitigation
- Risk 3 → mitigation

### Promotion plan (required)

If the hypothesis holds, what artifacts do we produce?

- PR scope (paths, modules)
- Tests/guards to add or update
- Ledger entries for deferred work (if any)
- ADR required? (yes/no; if yes, link)

### Stop conditions (required)

Define what makes us stop and re-scope:

- missing required context
- evidence cannot be obtained within budgets
- safety posture unclear
- scope grows beyond a focused PR
