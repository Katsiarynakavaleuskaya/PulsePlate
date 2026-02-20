# PR-P2: Dialogue Visualization (Mermaid) Audit

<!-- markdownlint-disable MD013 -->

**Status:** Draft audit (to be finalized during PR)
**Branch:** `docs/orchestration-dialogue-visualization`
**Date:** 2026-02-18

---

## Scope Validation

### In scope

- Mermaid interaction-graph contract for multi-agent dialogue.
- Canonical example visualization.
- Workflow cross-reference update.
- Docs-only planning and audit package.

### Out of scope

- Runtime code or API behavior.
- CI runtime logic changes.
- Telemetry scripts or graph generators.

---

## Evidence Anchors (Baseline)

- Backlog source item: `docs/roadmap/BACKLOG_LEDGER.md:1736`
- Dialogue hard-limit rule: `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md:36`
- Workflow protocol hub: `docs/orchestration/workflow.md:14`

---

## Recommended Execution Shape

1. Keep contract minimal and policy-aligned.
2. Represent both consensus and forced-decision outcomes.
3. Keep references centralized to avoid protocol duplication.

---

## Live Watch Checklist (CI + bot dialogue)

- [ ] Required checks are PASS on PR head.
- [ ] No unresolved review threads.
- [ ] CodeRabbit status is pass/no-actionables.
- [ ] Sourcery/Cubic statuses are pass/no-actionables.
- [ ] PR Body Phase2 gates pass.

---

## Command Evidence Skeleton

```bash
python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md
python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"
git diff --name-only origin/main...HEAD
```

Expected evidence format per command:

- exact command
- 1-3 raw output lines
- exit code

---

## Go/No-Go Criteria

- [ ] Mermaid contract is explicit and usable for audits.
- [ ] Example graph is present and reflects dialogue policy.
- [ ] Workflow references are updated and valid.
- [ ] PR scope remains docs-only.
- [ ] Required checks pass with no unresolved review threads.
