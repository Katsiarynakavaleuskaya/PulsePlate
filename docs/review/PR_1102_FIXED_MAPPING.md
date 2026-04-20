# PR 1102 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: `fcbe3cfb` renames the audit artifact from `PR_TBD` to `PR_1102` in `docs/audit/PR_1102_CV_EXPERIMENTATION_LANE_AUDIT_2026-03-11.md:1` and updates the active PR5 ledger entry to point at `#1102` and the new audit path in `docs/roadmap/BACKLOG_LEDGER.md:5384`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916582520 -> fcbe3cfb
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916582525 -> fcbe3cfb

Disposition: FIXED
Commit: see mapping entries below
Evidence: `b9be3da5` normalizes CV hint detection through `normalize_text()` in `scripts/orchestration/experiment_contract.py:268`, removes the unused `_is_cv_experiment` wrapper in `scripts/orchestration/experiment_bootstrap.py:236`, and adds separator-normalization regression coverage in `tests/test_experiment_bootstrap.py:110`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916582526 -> b9be3da5

Disposition: FIXED
Commit: see mapping entries below
Evidence: `e4026349` adds explicit rollout/rollback instruction sync for the governed CV lane in `.cursor/agents/agent-coordinator.md:351` and `.cursor/agents/cv-agent.md:21`, satisfying the requested `docs(agents): update instructions` follow-up for the new orchestration behavior.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916582524 -> e4026349

Disposition: FIXED
Commit: see mapping entries below
Evidence: cubic identified the separator-normalization bug in `is_cv_experiment()`. `b9be3da5` fixes that by normalizing CV hint input through `normalize_text()` in `scripts/orchestration/experiment_contract.py:268`, and `504ad3b1` hardens ML-domain hint matching to token boundaries in `scripts/orchestration/experiment_bootstrap.py:55`, adds a false-positive regression test in `tests/test_experiment_bootstrap.py:111`, and restores P1-before-P2 ordering in `docs/roadmap/BACKLOG_LEDGER.md:5411`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916601568 -> b9be3da5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916601574 -> 504ad3b1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#discussion_r2916601601 -> 504ad3b1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#pullrequestreview-3927626055 -> 504ad3b1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1102#pullrequestreview-3927647750 -> 504ad3b1
