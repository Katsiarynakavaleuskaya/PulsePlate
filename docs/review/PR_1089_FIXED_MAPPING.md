# PR 1089 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914532840 -> a8c2aee3
Disposition: FIXED
Commit: `a8c2aee3`
Evidence: `docs/contracts/RAG_CONTRACT.md:228`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914532846 -> a8c2aee3
Disposition: FIXED
Commit: `a8c2aee3`
Evidence: `tests/test_db_rls.py:60`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925491244
Disposition: NOT-A-BUG
Evidence: `docs/contracts/RAG_CONTRACT.md:228`; `tests/test_db_rls.py:60`
Reason: This cubic summary review only aggregates the two inline findings above, and current head addresses both of them.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543522 -> f19de674
Disposition: FIXED
Commit: `f19de674`
Evidence: `app/middleware/api_tiers.py:530`; `app/middleware/api_tiers.py:545`; `tests/test_api_tiers.py:623`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543533 -> f19de674
Disposition: FIXED
Commit: `f19de674`
Evidence: `app/routers/feedback.py:157`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914524554 -> f19de674
Disposition: FIXED
Commit: `f19de674`
Evidence: `app/routers/feedback.py:157`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543537 -> f19de674
Disposition: FIXED
Commit: `f19de674`
Evidence: `core/db_rls.py:37`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543544
Disposition: NOT-A-BUG
Evidence: `docs/contracts/RAG_CONTRACT.md:228`
Reason: Current head already uses explicit `file:line` anchors in the cited evidence bullet, so this comment targets an outdated diff snapshot rather than a live contract violation.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543548
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1089_FIXED_MAPPING.md:8`
Reason: The stale placeholder text is no longer present on current head; the mapping section already contains explicit dispositions and evidence.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914543553 -> f19de674
Disposition: FIXED
Commit: `f19de674`
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:876`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925503441
Disposition: NOT-A-BUG
Evidence: `app/middleware/api_tiers.py:530`; `app/routers/feedback.py:157`; `core/db_rls.py:37`; `docs/contracts/RAG_CONTRACT.md:228`; `docs/review/PR_1089_FIXED_MAPPING.md:8`; `docs/roadmap/BACKLOG_LEDGER.md:876`; `tests/test_compliance_control_plane.py:371`
Reason: This CodeRabbit summary review aggregates the inline findings above; current head either fixes them in `f19de674` or already satisfies the contract on the cited lines.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914695916 -> 0a5f621a
Disposition: FIXED
Commit: `0a5f621a`
Evidence: `docs/review/PR_1089_FIXED_MAPPING.md:94`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914699387 -> 0a5f621a
Disposition: FIXED
Commit: `0a5f621a`
Evidence: `tests/test_compliance_control_plane.py:371`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914699392 -> 0a5f621a
Disposition: FIXED
Commit: `0a5f621a`
Evidence: `app/middleware/api_tiers.py:520`; `app/models/rag_feedback.py:1`; `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:1`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925664343
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1089_FIXED_MAPPING.md:94`
Reason: This CodeRabbit summary review aggregates the fixed merge-readiness checkbox finding mapped immediately above; current head keeps the checklist provisional until the final merge cycle.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925668197
Disposition: NOT-A-BUG
Evidence: `tests/test_compliance_control_plane.py:371`; `app/middleware/api_tiers.py:520`; `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:1`
Reason: This cubic summary review aggregates the two inline findings immediately above, both identified by cubic and fixed in `0a5f621a`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925679771
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1089_FIXED_MAPPING.md:94`; `tests/test_compliance_control_plane.py:371`; `app/middleware/api_tiers.py:520`; `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:1`
Reason: This CodeRabbit summary review aggregates the fixed checkbox, RLS principal, and DSAR test findings above; current head addresses each concrete issue in `0a5f621a`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914902331 -> 83b91507
Disposition: FIXED
Commit: `83b91507`
Evidence: `docs/contracts/RAG_CONTRACT.md:228`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914902340 -> 83b91507
Disposition: FIXED
Commit: `83b91507`
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:866`; `docs/roadmap/BACKLOG_LEDGER.md:867`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2914917602 -> 83b91507
Disposition: FIXED
Commit: `83b91507`
Evidence: `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:68`; `tests/test_db_rls.py:88`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925883672
Disposition: NOT-A-BUG
Evidence: `docs/contracts/RAG_CONTRACT.md:228`; `docs/roadmap/BACKLOG_LEDGER.md:866`
Reason: This CodeRabbit summary review aggregates the two inline findings immediately above, and both are fixed in `83b91507`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3925898576
Disposition: NOT-A-BUG
Evidence: `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:68`; `tests/test_db_rls.py:88`
Reason: This cubic summary review aggregates the rollback-FK finding immediately above, and current head fixes it in `83b91507`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2915074289 -> a9dae019
Disposition: FIXED
Commit: `a9dae019`
Evidence: `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:68`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#discussion_r2915074293 -> a9dae019
Disposition: FIXED
Commit: `a9dae019`
Evidence: `tests/test_db_rls.py:96`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1089#pullrequestreview-3926057925
Disposition: NOT-A-BUG
Evidence: `alembic/versions/202603110001_harden_rag_subject_principal_bigint.py:68`; `tests/test_db_rls.py:96`
Reason: This cubic summary review aggregates the two inline findings immediately above, and current head addresses both in `a9dae019`.

## Merge Readiness
- [x] Local `pre-commit run --all-files`
- [x] Local `make verify`
- [ ] Required remote checks PASS
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final wait-window observed before merge
