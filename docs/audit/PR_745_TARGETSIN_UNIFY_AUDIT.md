# PR-745 Audit — Unify `TargetsIn` schemas

(legacy ↔ canonical)

**Date:** 14 February 2026
**PR:** 745 (planned)
**Publication note:** This audit document is published as **PR #0**
(documentation/audit phase), and **PR #745** is the subsequent
implementation PR that will contain the actual code changes.
**Type:** Backend contract remediation (P1, narrow scope)
**Scope owner:** @katsiaryna_kavaleuskaya

---

## Summary

This is an audit-first packet before code edits for the next narrow P1:
unify `TargetsIn` schema usage so there is one canonical contract and no
legacy drift.

Target outcome:

- Single source of truth for `TargetsIn`
- Legacy compatibility preserved via thin adapter/alias behavior
- Deterministic validation parity and no OpenAPI contract inflation

---

## Current state (evidence-backed)

### Verified commands

1. Find `TargetsIn` class definitions

- Command:
  - `rg -n "class\\s+TargetsIn" --glob "*.py"`
- Raw output (excerpt):
  - `app/schemas/nutrition_targets.py:37:class TargetsIn(BaseModel):`
  - `app/models/nutrition.py:9:class TargetsIn(BaseModel):`
- Exit code: `0`

1. Find canonical import/use footprint

- Command:
  <!-- markdownlint-disable-next-line MD013 -->
  - `rg -n "from\\s+app\\.schemas\\.nutrition_targets\\s+import\\s+TargetsIn|nutrition_targets\\.TargetsIn|TargetsIn\\(" --glob "*.py"`
- Raw output (excerpt):
  - `legacy_app.py:73:from app.schemas.nutrition_targets import TargetsIn as CanonicalTargetsIn`
  - `app/routers/pro.py:25:from app.schemas.nutrition_targets import TargetsIn`
  - `app/routers/premium_week.py:21:from app.schemas.nutrition_targets import TargetsIn`
  - `tests/test_targets_in_parity.py:8:from app.schemas.nutrition_targets`
  - `import TargetsIn as CanonicalTargetsIn`
- Exit code: `0`

1. Verify app facade legacy delegation remains in place

- Command:
  - `rg -n "legacy_app" app/__init__.py`
- Raw output (excerpt):
  - `app/__init__.py:1:"""App package - shim facade for legacy_app backward compatibility.`
  - `app/__init__.py:51:    legacy = importlib.import_module("legacy_app")`
  - `app/__init__.py:60:    """Resolve attribute lazily from local exports or legacy_app.`
- Exit code: `0`

---

## Problem framing

- There are at least two `TargetsIn` model declarations in the repository:
  - `app/schemas/nutrition_targets.py:37`
  - `app/models/nutrition.py:9`
- Canonical router paths already import canonical schema directly:
  - `app/routers/pro.py:25`
  - `app/routers/premium_week.py:21`
- Legacy layer already imports canonical schema alias:
  - `legacy_app.py:73`

Risk: if multiple model definitions remain behaviorally divergent, request
validation can drift by path and produce inconsistent `422` semantics.

---

## Multi-agent brainstorm synthesis

### Coordinator decision

- **Recommended PR goal:** unify `TargetsIn` contract usage with one SoT
  and thin legacy compatibility.
- **Out of scope:** new endpoints, product behavior changes, broad cleanup.

### Architecture decisions (must)

- Canonical SoT: `app.schemas.nutrition_targets.TargetsIn`.
- Legacy should not host independent validation logic for `TargetsIn`;
  legacy path must adapt/delegate.
- Avoid API inflation (no parallel public schema standards).

### Contract decisions (must/should)

- **Must:** preserve backward compatibility of accepted legacy payload
  shapes via alias/mapping at one boundary only.
- **Must:** preserve deterministic error class semantics (`422` families)
  across canonical and legacy paths.
- **Should:** keep canonical serialization names; legacy aliases should be
  input-compat only.

### Logic invariants (must hold)

- Field-set equivalence by meaning (required/optional/default semantics).
- Range/nullability/type invariance for domain-significant fields.
- No contradictory precedence when payload includes both canonical and legacy aliases.

### Security focus

- Do not weaken validation constraints while unifying.
- Prefer fail-closed on invalid/coercion edge cases.

---

## Proposed implementation scope (for next code PR)

1. Freeze SoT on `app.schemas.nutrition_targets.TargetsIn`.
1. Eliminate/retire duplicate drift-prone `TargetsIn` usage pattern
   (without changing endpoint contracts).
1. Keep legacy endpoint behavior via thin adapter/delegation to canonical
   validation.
1. Add/adjust parity tests and OpenAPI checks only for this contract
   surface.

---

## Test and gate plan (before merge)

- `pre-commit run --all-files`
- `pytest -q tests/test_targets_in_parity.py`
- Targeted legacy/canonical contract tests for equivalent accept/reject matrix
- `make openapi`
- `make openapi-check`
- `make verify`

---

## Risks and mitigations

- **Contract break risk:** hidden field/default drift.
  - Mitigation: parity matrix tests + explicit delta checklist.
- **Legacy regression risk:** path-specific validation mismatch.
  - Mitigation: paired tests on canonical and legacy request paths.
- **Schema inflation risk:** duplicated models in OpenAPI.
  - Mitigation: OpenAPI determinism and artifact sync checks.

---

## Go / No-Go before code edits

- [x] Audit-first completed
- [x] Evidence commands collected with raw output excerpts and exit codes
- [x] Canonical SoT candidate identified
- [x] Narrow PR scope defined (no scope creep)
- [ ] Code edit plan approved for PR-745
