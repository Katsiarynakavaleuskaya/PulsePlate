# PR 1127 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: b750659a
Evidence: `b750659a` removes the subprocess-based import probe from `scripts/ci/check_local_verify_environment.py:1-97`, makes `verify-env` run inside the repo `.venv` in `Makefile:138-142`, and extends `tests/test_check_local_verify_environment.py:1-88` with deterministic coverage for the repo-venv execution contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921384592 -> b750659a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921385119 -> b750659a

Disposition: FIXED
Commit: 3fde7ffd
Evidence: `3fde7ffd` reopens the carried-over phase2 ledger item instead of pre-closing it in `docs/roadmap/BACKLOG_LEDGER.md:5918-5927`, adds the missing phony targets in `Makefile:477`, and aligns the new parity tests with typed-fixture expectations in `tests/test_check_local_verify_environment.py:1-95`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921398401 -> 3fde7ffd

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
