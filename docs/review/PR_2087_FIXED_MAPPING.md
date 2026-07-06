# PR 2087 - Fixed in Commit Mapping

PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/2087

Branch: `codex/fix-main-knowledge-promotion-timeout-test`

## Summary

This PR fixes the post-merge `main` CI failure in the knowledge-promotion
store-error regression test. The test now isolates the intended store-error
branch from the timeout branch, while production fail-soft behavior remains
unchanged.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Implementation Evidence

Disposition: FIXED
Commit: 6d9d0022f5c0252cd59fe58691ecde9b074580cf
Evidence: `tests/test_remaining_modules.py`
Reason: The store-error test now raises `KNOWLEDGE_PROMOTION_TIMEOUT_SECONDS`
for that test only, so it exercises the intended `RuntimeError("boom")` branch
instead of racing the timeout branch under the Python 3.12 CI shard.

## Main CI Failure Evidence

- `main` CI run: https://github.com/Katsiarynakavaleuskaya/PulsePlate/actions/runs/28804293563
- Failed job: `test-main (3.12, 90)` / job `85415810365`.
- Failure:
  `tests/test_remaining_modules.py::TestInsightApplicationServiceFastLane::test_maybe_promote_knowledge_candidates_logs_and_swallows_store_errors`
  expected `Knowledge promotion failed` but observed
  `Knowledge promotion timed out; response path continues without persistence`.

## Role-Agent Notes

- Lane packet: `artifacts/orchestration/task_packets/f63b2263dd01.json`
- Role order requested:
  `agent-coordinator -> qa-engineer-agent -> bug-hunter -> security-auditor`.
- Timed-out coordinator attempts were closed instead of left running:
  `019f38d3-6468-7bd0-b349-187d10fcfc88`,
  `019f38da-1e29-7781-92e3-0385c92fd74c`.

## Experiment Runner Evidence

Not applicable: runner was attempted but the local macOS sandbox rejected oracle
execution because `unshare` is unavailable, so no accepted runner result shaped
this commit.

## Validation Evidence

- `python3 scripts/orchestration/check_preflight.py --path tests/test_remaining_modules.py --path app/services/insight_application_service.py` - PASS.
- `python3 scripts/orchestration/check_agent_consistency.py` - PASS.
- `.venv/bin/python -m pytest -q tests/test_remaining_modules.py::TestInsightApplicationServiceFastLane::test_maybe_promote_knowledge_candidates_logs_and_swallows_store_errors` - PASS.
- `.venv/bin/python -m pytest -q tests/test_remaining_modules.py -k 'maybe_promote_knowledge_candidates'` - PASS, `4 passed`.
- `make validate-changed` - PASS.
- `pre-commit run --all-files` - PASS.
- Push hook - PASS, including backend pre-push tests, full-repo Bandit,
  pip-audit, and Docker build test skip/no files.

## Merge Readiness

Not claimed here. Requires current-head GitHub CI, strict merge-readiness
wrapper, and final bot/review disposition pass.
