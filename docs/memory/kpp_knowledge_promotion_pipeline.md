# Memory Capsule: Knowledge Promotion Pipeline (KPP)

**Topic:** Controlled “project learning” via repo artifacts
**Type:** Process invariant (SoT pointer)
**Last updated:** 8 February 2026

---

## What

KPP is the canonical process for turning reusable insights into durable repo memory **without** breaking Source of Truth.

Hard rule:

- Agents do not “learn” by silently storing canonical knowledge.
- “Self-learning” happens only via **promoting** insights into repo artifacts (docs/tests/ledger), with evidence.

---

## Why

KPP prevents:

- hidden memory becoming “truth”
- drift from duplicated wording across docs
- repeated rediscovery work between sessions

---

## Promotion rule (single path)

If a reusable insight is discovered, promote it into **exactly one** durable repo artifact:

- canonical doc / policy / ADR update, or
- guard test (preferred for invariants), or
- backlog item in `docs/roadmap/BACKLOG_LEDGER.md`, or
- memory capsule under `docs/memory/` (index: `docs/memory/index.md`)

---

## Evidence requirements (non-negotiable)

Every promoted claim must include one of:

- `file:line` pointers (prefer **single-line anchors**, avoid ranges), and/or
- reproducible commands + raw output + exit code

Forbidden:

- “common knowledge” as evidence
- “the model remembers”

---

## Anti-drift rule

If the same wording/policy appears in more than one place, create a single SoT doc and replace copies with links.

Example SoT:

- Wellness disclaimer wording: `docs/safety/WELLNESS_DISCLAIMER_CANONICAL.md`

---

## Who can promote to canonical

`agent-coordinator` is the final authority for promotions and decides the destination artifact.

---

## Links (canonical)

- Coordinator-first workflow: `AGENTS.md` → “Agent Coordination (Coordinator-First Rule)”
- Backlog ledger rules: `docs/roadmap/BACKLOG_LEDGER.md`
