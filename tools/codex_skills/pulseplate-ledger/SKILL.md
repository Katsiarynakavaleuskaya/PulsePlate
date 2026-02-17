---
name: pulseplate-ledger
description: Record deferred work in the canonical backlog ledger with enforceable DoD fields.
---

# PulsePlate Ledger

## When to use

- Deferring any scoped work from current PR/task.
- Capturing temporary skips, guard disables, or follow-ups.
- Updating status of tracked technical debt items.

## Inputs required

- Deferral reason.
- Owner.
- Priority (`P0`, `P1`, `P2`).
- Target PR (number or placeholder).
- DoD acceptance criteria.

## Procedure (commands)

1. Open canonical ledger:

   ```bash
   sed -n '1,260p' docs/roadmap/BACKLOG_LEDGER.md
   ```

2. Add/update item with required fields:
   - Owner
   - Priority
   - Target PR
   - Reason
   - Links
   - DoD
3. Verify links and evidence anchors:

   ```bash
   rg -n "Owner:|Priority:|Target PR:|Reason:|DoD:" docs/roadmap/BACKLOG_LEDGER.md
   ```

4. If docs/audit or docs/security were changed, validate docs gate:

   ```bash
   python scripts/ci/check_docs_phase1_gates.py --files docs/audit/<FILE>.md
   ```

## Output format

- `Ledger action`: created/updated item title.
- `Traceability`: PR/task linkage and references.
- `DoD`: explicit acceptance list.
- `Status`: open/merged/won't do.

On failure include:

- Raw failing lines.
- `file:line:error` pointers.
- Minimal correction steps.

## Guardrails

- Never defer work without ledger entry.
- Never omit owner, priority, target PR, or DoD.
- Do not use ad-hoc skip reasons when policy requires standardized reasons.
- Keep ledger English-first for canonical maintainability.

## SoT links

- `docs/roadmap/BACKLOG_LEDGER.md`
- `AGENTS.md`
- `scripts/ci/check_docs_phase1_gates.py`
- `docs/audit/`
- `docs/security/`
