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

## Related documentation

- KPP: `docs/memory/kpp_knowledge_promotion_pipeline.md`
- Message envelopes: `docs/orchestration/AGENT_MESSAGE_PROTOCOL.md`
