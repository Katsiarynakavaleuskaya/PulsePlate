# PR-P2: Dialogue Visualization (Mermaid) Execution Plan

<!-- markdownlint-disable MD013 -->

**Status:** execution-ready (docs/process only)
**Branch:** `docs/orchestration-dialogue-visualization`
**Date:** 2026-02-19

---

## Scope

### IN

- Add canonical Mermaid visualization contract for agent dialogue.
- Add minimal example graph for quick auditability.
- Update orchestration workflow references to this contract.
- Add planning/audit package in the same style as prior orchestration PRs.

### OUT

- Telemetry collection implementation.
- Auto-generated graph tooling/script.
- Runtime product or backend/frontend logic changes.
- CI workflow behavior changes.

---

## Coordinator-First Execution Skeleton

### Phase 1 - Contract freeze

- Freeze mandatory graph entities: participants, iterations, edges, outcome.
- Align with dialogue hard limit (`<=3`) and forced decision semantics.

### Phase 2 - Documentation implementation

- Add `Dialogue Visualization Contract` section to `AGENT_DIALOGUE_TEMPLATE.md`.
- Add one canonical Mermaid template and one snapshot example.
- Add explicit forced-decision path rule.

### Phase 3 - Workflow integration

- Update `docs/orchestration/workflow.md` to reference the visualization contract section.
- Keep links single-source and avoid duplicate protocol text.

### Phase 4 - Audit + PR packaging

- Fill task analysis + brainstorming + audit + PR body skeleton artifacts.
- Ensure all files stay docs-only and traceable to backlog item.

---

## Brainstorming-to-Execution Track

1. **Minimal contract option (recommended):** strict required fields + one example.
2. **Extended contract option:** include optional edge timing/status metadata.
3. **Tool-first option:** define schema + script generator (deferred).
4. **Runbook-first option:** keep template minimal, put examples in runbook (not needed now).

---

## Negative Scenario Matrix

| # | Failure scenario | Risk | Guard |
| --- | --- | --- | --- |
| 1 | Mermaid section exists without required fields | low utility | explicit input/output contract |
| 2 | Example misses forced-decision branch | policy mismatch | mandatory no-path rule |
| 3 | Workflow points to stale/non-canonical docs | drift | direct section reference in workflow |
| 4 | Scope expands to telemetry implementation | scope creep | docs-only IN/OUT lock |

---

## Deterministic Validation Commands (Docs PR)

```bash
python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"
git diff --name-only origin/main...HEAD
```

---

## DoD

- [ ] Mermaid output format is defined with required fields and structure.
- [ ] Example visualization exists in orchestration docs.
- [ ] `workflow.md` references the visualization contract section.
- [ ] PR remains docs-only and passes required docs/PR-body gates.
- [ ] Thread mapping and bot discussion closure follow project canon.
