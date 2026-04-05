# Agent Reflection Protocol (KPP-aligned, dev-only)

**Purpose:** Define “reflection / self-learning” as **promotion into repo artifacts** (KPP), not model memory.

**Status:** Canonical (dev-only).

---

## Canonical constraint

Agents do not “learn” by silently storing canonical knowledge.

Canonical process: `docs/memory/kpp_knowledge_promotion_pipeline.md`.

---

## Triggers

Reflect when any occurs:

- protocol drift / contradictory docs
- multi-model parse failure
- evidence gap
- repeat failure (same class ≥2 times)
- safety boundary risk (wellness-only)
- budget breach
- bootstrap envelope vs skill-routing mismatch (for example `message_envelope.mode` is `docs-only` while execution plans or recommended skills imply runtime code change, or `skill_routing.envelope_mode_hint` disagrees with envelope derivation for the same `candidate_paths`)

---

## Bootstrap and routing awareness (local workforce lane)

Coordinator and review agents should treat the canonical task packet as the only orchestration SoT:

- `inputs.message_envelope.mode` (`docs-only` vs `analysis`) is a **derived view** over the same path signals as `skill_routing.envelope_mode_hint` (`docs_only` vs `analysis` in `bootstrap_sync_policy.resolve_analysis_envelope_mode`). Evidence: `scripts/orchestration/task_bootstrap.py:814`, `scripts/orchestration/skill_router.py` (return payload includes `envelope_mode_hint`).
- When triaging repeat failures or doc/code drift, if routing output and envelope disagree for identical inputs, reflect using the artifact format below and promote a **single** fix: either path normalization, policy doc correction, or deterministic router/bootstrap tests — not ad-hoc parallel contracts.

This section does not authorize a second reflection schema; it extends **when** to reflect for orchestration hygiene.

---

## Incident types (suggested taxonomy)

- **Format drift:** extra preamble, wrong keys, Markdown fences around JSON
- **Truncation:** partial envelope or missing tail keys
- **Evidence failure:** claims without `file:line` or reproducible command evidence
- **Safety boundary:** wellness-only wording violated or ambiguous
- **Budget breach:** timebox/limits exceeded; recursion/hops unbounded
- **Routing/envelope mismatch:** docs-only envelope paired with implementation skills, or `envelope_mode_hint` inconsistent with `message_envelope.mode` for the same path set

---

## Reflection artifact (format)

```markdown
## Reflection: <short title>

**Trigger:** <type>
**Observed failure mode:** <what happened>
**Root cause hypothesis:** <why>
**Immediate mitigation:** <smallest safe change>
**Systemic mitigation:** <guard/test/doc>
**Evidence:** <file:line and/or commands + raw output + exit code>
**Promotion target (KPP):** <ONE destination>
```

---

## Weekly synthesis (recommended)

Once per week (or after a repeat failure), coordinator produces a short synthesis:

- top 3 recurring incident types
- what changed (doc/protocol/guard) to prevent recurrence
- what is deferred (must be recorded in `docs/roadmap/BACKLOG_LEDGER.md`)

This synthesis is dev-only; promotion to canonical rules follows KPP.

---

## Promotion rule (KPP)

Coordinator promotes to exactly ONE destination:

- canonical doc / policy update
- guard test (preferred when enforceable)
- backlog item in `docs/roadmap/BACKLOG_LEDGER.md`
- memory capsule under `docs/memory/` (pointer-only)

Canonical process: `docs/memory/kpp_knowledge_promotion_pipeline.md`.

---

## Related documentation

- KPP: `docs/memory/kpp_knowledge_promotion_pipeline.md`
- Message envelopes: `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
