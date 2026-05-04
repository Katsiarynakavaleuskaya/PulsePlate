# PR 1659 Fixed Mapping

## Summary

Canonical-fail invariance fixture coverage for judgment and RAG validity datasets.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1659#discussion_r3181951781 -> 9e790f466
Disposition: FIXED
Commit: 9e790f466
Evidence: tests/evals/test_judgment_validity_variant_families.py:171, tests/evals/test_judgment_validity_variant_families.py:193

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1659#discussion_r3181954445 -> 9e790f466
Disposition: FIXED
Commit: 9e790f466
Evidence: tests/evals/test_rag_release_gate_validity_variant_families.py:171, tests/evals/test_rag_release_gate_validity_variant_families.py:193

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1659#discussion_r3182058367 -> 6c8bb0c42
Disposition: FIXED
Commit: 6c8bb0c42
Evidence: tests/evals/test_rag_release_gate_validity_variant_families.py:166, tests/evals/test_judgment_validity_variant_families.py:164

## Merge Readiness Evidence

All CI checks pass on current head. Bot review threads addressed.
