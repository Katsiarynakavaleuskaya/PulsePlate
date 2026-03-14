# PR 1170 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 531d25dd7f1fa6fa309c953e06fbb8274892dd18
Evidence: `scripts/orchestration/logic_philosophy_replay_eval.py:260` and `scripts/orchestration/logic_philosophy_replay_eval.py:271` now send replay failures to `stderr`, `tests/test_logic_philosophy_replay_eval.py:153` locks the stderr-only error contract, and `docs/analytics/EXPERIMENT_REGISTRY.md:16` now matches the canonical metric wording with `unsupported claim rate`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#pullrequestreview-3948903506 -> 531d25dd7f1fa6fa309c953e06fbb8274892dd18
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935349289 -> 531d25dd7f1fa6fa309c953e06fbb8274892dd18
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935349294 -> 531d25dd7f1fa6fa309c953e06fbb8274892dd18

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
