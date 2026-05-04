# PR 1660 Pre-mortem — Evaluation Item Metadata Registry

## Summary

This pre-mortem assumes the item metadata registry PR failed after merge and
records the main risks.

## Failure Mode 1 — Fake psychometrics

**Risk:** Registry labels are mistaken for calibrated IRT/difficulty estimates.

**Mitigation:** Docs state registry is psychometric-readiness only and does not
implement IRT or scoring. Every notes field says "Difficulty band is heuristic
label, not calibrated IRT estimate."

## Failure Mode 2 — Missing item coverage

**Risk:** Some fixture canonical_ids are not represented in the registry.

**Mitigation:** Tests compare fixture canonical_ids with registry canonical_ids
exactly (tests 5, 6, 7). Any new fixture item added without a registry row
will fail CI.

## Failure Mode 3 — Orphan registry rows

**Risk:** Registry contains canonical_ids not present in any fixture.

**Mitigation:** `validate_registry_coverage()` rejects orphan canonical_ids.
Test 7 enforces this.

## Failure Mode 4 — Decision contradiction

**Risk:** Registry expected_decision diverges from fixture canonical decision.

**Mitigation:** Test 8 compares registry expected_decision to canonical fixture
row decision for all 10 items (8 pass + 2 fail).

## Failure Mode 5 — Runtime scope creep

**Risk:** PR touches runtime/API/RAG thresholds/judgment decisions.

**Mitigation:** Allowed-files check shows only `scripts/evals/`, `data/evals/`,
`tests/evals/`, and `docs/` paths are touched. No `app/`, `core/`, `frontend/`,
`ios/`, or billing paths.

## Required Evidence Before Merge

- `pytest -q tests/evals/test_eval_item_metadata_registry.py`
- `pytest -q tests/evals/`
- `pytest -q tests/test_judgment_eval.py`
- `pytest -q tests/test_rag_release_gates_runner.py`
- `make verify` or raw failure output documented
