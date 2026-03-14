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

Disposition: FIXED
Commit: af9b9482d562a9955eb6d16fc260aeb95b4c383d
Evidence: `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md:9-11` and `docs/orchestration/contracts/LOGIC_PHILOSOPHY_REPLAY_EVAL_CONTRACT.md:31-34` now anchor contract truth claims with explicit `file:line` evidence; `scripts/orchestration/logic_philosophy_replay_contract.py:44-50` and `scripts/orchestration/logic_philosophy_replay_contract.py:82-88` fail closed on non-string snippets and non-integer network budgets; `scripts/orchestration/logic_philosophy_replay_eval.py:35-59`, `scripts/orchestration/logic_philosophy_replay_eval.py:85-105`, and `scripts/orchestration/logic_philosophy_replay_eval.py:177-205` reject empty or negated snippet matches, expose missing required facts, count correctness failures in known-good controls, and enforce the usefulness-floor promotion guardrail; `tests/test_logic_philosophy_replay_eval.py:52-69` and `tests/test_logic_philosophy_replay_eval.py:103-188` lock the strict contract and evaluator regressions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935351139 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935351289 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935351291 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935354922 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935354923 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935354924 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935354925 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1170#discussion_r2935359571 -> af9b9482d562a9955eb6d16fc260aeb95b4c383d

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
