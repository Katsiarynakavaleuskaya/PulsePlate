# PR 1169 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 7b6ef2da5e5149bb63793f203a0a6512c952a356
Evidence: `scripts/orchestration/check_merge_ready.py:56` defines a stable `BLOCKING_MERGE_READY_GATES` order, while `scripts/orchestration/check_merge_ready.py:266` now derives `blocking=yes/no` from `policy.blocking` instead of hardcoding the label; `tests/test_orchestration_merge_ready.py:225` locks the contract with a regression test that proves a non-blocking policy prints `blocking=no`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#pullrequestreview-3948850887 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#discussion_r2935290995 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356

Disposition: FIXED
Commit: 7b6ef2da5e5149bb63793f203a0a6512c952a356
Evidence: `scripts/orchestration/check_merge_ready.py:56` defines the canonical blocking gate order, and `scripts/orchestration/check_merge_ready.py:266` now prints `blocking=yes/no` from `policy.blocking`; this satisfies the duplicate cubic finding about hardcoded bundle output, with the regression expectation anchored in `tests/test_orchestration_merge_ready.py:225`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#pullrequestreview-3948852341 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#discussion_r2935292982 -> 7b6ef2da5e5149bb63793f203a0a6512c952a356

Disposition: NOT-A-BUG
Evidence: `scripts/orchestration/check_merge_ready.py:310` constructs `gate_results` only from the four canonical hard gates, and `scripts/orchestration/check_merge_ready.py:325` therefore intentionally treats every non-zero return in that fixed bundle as blocking. The advisory fallback policy is currently output metadata for unknown names, not an executed lane inside this wrapper contract.
Reason: CodeRabbit identified a hypothetical future mismatch if non-blocking gates are ever added to `gate_results`, but the current wrapper executes only the fixed blocking bundle, so the present merge verdict logic remains consistent with the implemented contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#pullrequestreview-3948859273

Disposition: FIXED
Commit: cc39111f5d6d98b0f879ae2319139d68412b00b4
Evidence: `docs/review/PR_1169_FIXED_MAPPING.md:8` now points to `scripts/orchestration/check_merge_ready.py:266`, the actual line where `blocking_value` is derived, so the artifact proof matches the code that implements the fix.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#pullrequestreview-3948859818 -> cc39111f5d6d98b0f879ae2319139d68412b00b4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1169#discussion_r2935302846 -> cc39111f5d6d98b0f879ae2319139d68412b00b4

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
