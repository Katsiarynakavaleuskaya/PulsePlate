# Brainstorming: Orchestration Dialogue Visualization (Mermaid)

<!-- markdownlint-disable MD013 -->

**Date:** 2026-02-18
**Scope:** Define a practical, canonical interaction-graph contract for agent dialogue audits.

---

## Problem Frame

Current dialogue protocol is structured but hard to scan quickly during reviews and postmortems.
We need a lightweight visual format that:

- preserves the 3-iteration hard limit,
- makes convergence vs forced decision explicit,
- remains docs-only and implementation-agnostic.

Evidence anchors:

- `docs/roadmap/BACKLOG_LEDGER.md:1736`
- `docs/orchestration/AGENT_DIALOGUE_TEMPLATE.md:36`

---

## Candidate Tracks

1. **Minimal Mermaid contract (recommended)**
   - Required fields and fixed flow shape.
   - One canonical example.
   - Fast adoption, low ambiguity.

2. **Schema-heavy contract**
   - Add strict JSON schema first, Mermaid second.
   - Better machine validation, slower adoption.

3. **Tool-first generator**
   - Build script that emits Mermaid from dialogue logs.
   - Higher value later, out of scope for this docs PR.

---

## Quick Option Scoring

| Option | Delivery speed | Audit value | Risk | Recommendation |
| --- | --- | --- | --- | --- |
| Minimal Mermaid contract | High | High | Low | ✅ Primary |
| Schema-heavy contract | Medium | Medium | Medium | Deferred |
| Tool-first generator | Low | High | Medium | Deferred |

---

## Guarded Decisions

- Keep this PR docs-only.
- Keep visualization aligned to existing dialogue semantics; do not redefine protocol.
- Ensure graph explicitly supports both `consensus` and `forced-decision` outcomes.
- Avoid telemetry/tooling scope in this PR.

---

## Next-Step Bundle

1. Add visualization contract section to `AGENT_DIALOGUE_TEMPLATE.md`.
2. Add canonical Mermaid template + example snapshot.
3. Add workflow cross-reference in `workflow.md`.
4. Include task-analysis/execution/audit/PR-body skeleton package.
