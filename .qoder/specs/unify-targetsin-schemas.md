# Plan: Close TargetsIn Schema Unification Ledger Item

## Summary

**Task already completed in PR-633.** This PR updates the backlog ledger to mark the item as done.

## Evidence (from codebase exploration)

| Location | Content |
|----------|---------|
| `app/schemas/nutrition_targets.py:37-58` | Canonical TargetsIn definition (import-safe, no ORM) |
| `legacy_app.py:127` | `TargetsIn = CanonicalTargetsIn` (thin alias) |
| `legacy_app.py:126` | Comment: "PR-633: thin alias to canonical import-safe schema (no local validation)" |
| `tests/test_targets_in_parity.py:28-32` | `assert legacy_app.TargetsIn is CanonicalTargetsIn` (guard test) |

## DoD Verification

| DoD Item | Status |
|----------|--------|
| One canonical schema (single source of truth) | ✅ `app/schemas/nutrition_targets.py` |
| Thin wrapper/alias where needed | ✅ `legacy_app.TargetsIn = CanonicalTargetsIn` |
| Parity tests that prevent schema drift | ✅ `test_legacy_targets_in_is_canonical_alias()` |
| No contract break for legacy endpoints | ✅ Tests exist in `test_targets_in_parity.py` |

## Implementation

### Files to modify

1. `docs/roadmap/BACKLOG_LEDGER.md`
   - Mark checkbox: `- [x] P1: Unify TargetsIn schemas`
   - Update status: `✅ Completed (PR-633)`
   - Add resolution note referencing evidence

### Verification

```bash
# Docs-only change — no code verification needed
pre-commit run --all-files
make lint  # optional sanity check
```

## Scope

- **Type:** docs-only (ledger update)
- **Risk:** None (no code changes)
- **PR title:** `docs(ledger): close TargetsIn schema unification — completed in PR-633`
