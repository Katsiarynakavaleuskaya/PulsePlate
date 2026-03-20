# PR 1195 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: Aggregate bot review records are roll-up comments only; their actionable items are dispositioned individually below in this artifact.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#pullrequestreview-3981300665
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#pullrequestreview-3981313064
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#pullrequestreview-3981327585

Disposition: FIXED
Commit: 6d0b35cd
Evidence: `core/rag/philosophy_pipeline.py:106-160` preserves Unicode and mixed health tokens such as `A1C` and `LDL-C`, and `tests/test_philosophy_pipeline.py:297-301` asserts alphanumeric medical token extraction.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#issuecomment-4097730775 -> 6d0b35cd

Disposition: FIXED
Commit: 7db0cd50
Evidence: `core/rag/philosophy_pipeline.py:415-445` now extracts anchors per numeric range using range-local context, `core/rag/philosophy_pipeline.py:475-491` compares contradictions with those range-local anchors, and `tests/test_philosophy_pipeline.py:322-330,420-442` cover multi-topic chunk suppression and `B12` contradiction detection.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965562418 -> 7db0cd50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965573190 -> 7db0cd50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965573907 -> 7db0cd50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965573913 -> 7db0cd50
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965587728 -> 7db0cd50

Disposition: NOT-A-BUG
Evidence: `core/rag/philosophy_pipeline.py:108-160` intentionally keeps audience/cadence terms non-binding, and `tests/test_philosophy_pipeline.py:397-432` proves cohort-only overlap would reintroduce false contradictions across different metrics.
Reason: C2 ambiguity policy prefers suppressing contradiction when only demographic or cadence language overlaps.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965587721

Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md:2866
Reason: Long-form to acronym normalization (for example `body mass index` -> `BMI`) needs an explicit synonym/alias layer and is outside narrow C2 follow-through.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1195#discussion_r2965573196

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
