# Task Analysis: P2 Dialogue Visualization (Interaction Graph)

---

## Task Analysis

**Task:** Define canonical Mermaid interaction-graph contract for multi-agent dialogue and add reference example.

**Domain(s):** Multiple (Orchestration Docs | Developer Workflow | QA Auditability)

**Complexity:** Low-Moderate

**Priority:** P2

- **Priority track (P0-A / P0-B / P1 / P2):** P2

**Expected Outcome:**

- Canonical Mermaid output format is explicitly defined.
- Example visualization is present in orchestration docs.
- Workflow docs reference the visualization contract.
- PR is docs/process only with zero runtime impact.

**Invariants Affected:**

- [x] Layer Separation (docs-only, no runtime behavior change)
- [x] Deterministic process contract
- [x] Coordinator-first workflow consistency
- [ ] Contract-First API surface
- [ ] Thin HTTP Adapter Policy
- [ ] One BMI Engine

**Risks:**

1. Visualization schema becomes too abstract and non-actionable.
2. Mermaid example diverges from dialogue iteration hard-limit rules.
3. Scope creep into telemetry/tooling implementation (out of scope).

**Proposed Approach:**

1. Reuse current dialogue protocol terminology and iteration model (<=3).
2. Define minimal required nodes/edges/metadata for Mermaid output.
3. Add one concise canonical example and forced-decision branch rule.
4. Update workflow references to avoid protocol fragmentation.

**Agent Assignment:**

- **Primary:** `agent-coordinator`
- **Secondary:** `architecture-specialist`, `data-scientist-agent`
- **Dependencies:** Existing orchestration SoT docs and backlog item at `BACKLOG_LEDGER`.

**Constraints:**

- Docs-only PR scope.
- No code/runtime/CI behavior changes.
- Keep wording aligned with RU-first orchestration docs style.
- Preserve dialogue hard limit policy (<=3 iterations).

---

**Analysis by:** agent-coordinator (synthesized)
**Date:** 2026-02-18
