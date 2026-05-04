# PR 1660 Fixed Mapping

## Summary

Evaluation item metadata registry PR — adds psychometric-readiness metadata
layer for RAG and judgment eval fixtures.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596200 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: scripts/evals/eval_item_registry.py:103-121 — removed str()/bool()/list() coercion, added explicit isinstance checks for all string fields and variant_family_coverage items

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596228 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: tests/evals/test_eval_item_metadata_registry.py:194,221 — added cross-lane canonical_id collision assertions before dict merge

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1660#discussion_r3182596232 -> ca9aaee3c
Disposition: FIXED
Commit: ca9aaee3c
Evidence: tests/evals/test_eval_item_metadata_registry.py:333-349 — added _is_forbidden_module() helper that catches submodule imports (e.g. requests.sessions)

## Premortem / Bug-hunter Hardening (self-review)

Commit 2143209dc addressed findings from internal premortem + bug-hunter pass:
- BUG-1: non-dict raw input now rejected with clear ValueError (eval_item_registry.py:85)
- BUG-3: extract_canonical_ids_from_outcome_fixture now wraps json.loads with try/except (eval_item_registry.py:209)
- RISK-1: empty variant_family_coverage now rejected (eval_item_registry.py:113)
- GAP-1: 13 negative validation tests added (test_eval_item_metadata_registry.py:407-480)
- GAP-2: index_registry_by_canonical_id duplicate detection tested (test_eval_item_metadata_registry.py:487)
- GAP-3: validate_registry_coverage error paths tested (test_eval_item_metadata_registry.py:495-505)

## Merge Readiness Evidence

Pending current-head CI completion after hardening commit.
