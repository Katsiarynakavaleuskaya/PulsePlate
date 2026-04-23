# PR 1341 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#discussion_r3036923597 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#discussion_r3036934286 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059518980 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059520790 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059522438 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059530080 -> ca32df25b215ea0bef3516ab6bdda3c5d851a38d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059532661 -> 63d06e6798328d59b62ecebb8e17bc05d3c574a8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#discussion_r3036937730 -> f459b55606d9824c09302ab400bb0c45a06192cc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059546957 -> d5006459a6ae10a9a677ca5960a58c2f8ee719f0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#pullrequestreview-4059590694 -> 31172c229f040f1927e44981043de7e70f2f69c2
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1341#discussion_r3037017072 -> 31172c229f040f1927e44981043de7e70f2f69c2

Disposition: FIXED

Commit: ca32df25b215ea0bef3516ab6bdda3c5d851a38d; 63d06e6798328d59b62ecebb8e17bc05d3c574a8; d5006459a6ae10a9a677ca5960a58c2f8ee719f0; 7a28f81753260016ebf61c09aec020de65453234; f459b55606d9824c09302ab400bb0c45a06192cc; 31172c229f040f1927e44981043de7e70f2f69c2

Evidence: scripts/build_food_db.py:329 (explicit `INSERT INTO foods` column list); requirements.in / requirements.txt (`numpy==2.4.0` for CI PULSEPLATE mirror + `--only-binary`; transformers `>=5.5.0` retained); requirements-lock.txt regenerated (`transformers==5.5.0`); tests/test_food_schema_provenance.py (`core.schemas.FoodItem` resolver fields for diff-coverage; duplicate `test_core_schemas_fooditem_resolver_provenance_fields_round_trip` removed: `31172c229f040f1927e44981043de7e70f2f69c2`).
