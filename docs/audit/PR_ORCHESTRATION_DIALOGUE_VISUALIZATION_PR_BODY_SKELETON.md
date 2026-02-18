# PR Body Skeleton: Orchestration Dialogue Visualization (Mermaid)

## Summary

- Add a canonical Mermaid visualization contract for multi-agent dialogue.
- Add an example interaction graph that includes consensus and forced-decision branches.
- Reference the new visualization contract from the canonical orchestration workflow.
- Keep scope docs-only (no runtime/CI behavior change).

Evidence anchors:

- `docs/roadmap/BACKLOG_LEDGER.md:1577`
- `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md:36`
- `docs/orchestration/workflow.md:14`

## Scope

### IN

- Dialogue visualization contract section in orchestration docs.
- Canonical Mermaid template and example snapshot.
- Workflow cross-reference update.
- Task-analysis/brainstorming/audit artifacts.

### OUT

- Telemetry and generator tooling.
- Runtime/backend/frontend code changes.
- CI logic changes.

## Risks / Mitigations

- Ambiguous graph semantics -> define required fields and edge metadata.
- Drift from dialogue policy -> include explicit forced-decision branch rule.
- Scope creep -> docs-only file list and scope lock.

## Test Plan

- `python scripts/ci/check_docs_phase1_gates.py --files docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md`
- `python scripts/ci/check_pr_body_phase2_gates.py --body "<PR_BODY>"`
- `git diff --name-only origin/main...HEAD`

## Discussion Thread Pass

- [ ] Discussion-thread pass completed
- [ ] Fixed in commit mapping completed

### Fixed in Commit Mapping

- [ ] Mermaid visualization contract section added
- [ ] Example graph added
- [ ] Workflow reference updated
- [ ] Docs package artifacts added

## Deferred / Follow-ups

- [ ] Optional: schema/tooling for automatic graph generation (separate PR)
