# PR 1127 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: b750659a
Evidence: `b750659a` removes the subprocess-based import probe from `scripts/ci/check_local_verify_environment.py:1-97`, makes `verify-env` run inside the repo `.venv` in `Makefile:138-142`, and extends `tests/test_check_local_verify_environment.py:1-88` with deterministic coverage for the repo-venv execution contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3932979456 -> b750659a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921384592 -> b750659a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921385119 -> b750659a

Disposition: FIXED
Commit: 3fde7ffd
Evidence: `3fde7ffd` reopens the carried-over phase2 ledger item instead of pre-closing it in `docs/roadmap/BACKLOG_LEDGER.md:5918-5927`, adds the missing phony targets in `Makefile:477`, and aligns the new parity tests with typed-fixture expectations in `tests/test_check_local_verify_environment.py:1-95`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3932986920 -> 3fde7ffd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3932991615 -> 3fde7ffd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921393322 -> 3fde7ffd
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921398401 -> 3fde7ffd

Disposition: FIXED
Commit: 8977d3e6
Evidence: `8977d3e6` makes `make venv` create `.venv` before pip usage and routes `verify-env` through `$(VENV_PYTHON)` in `Makefile:54-87` and `Makefile:140-143`, hardens repo-venv detection with `sys.prefix` plus console-entrypoint checks in `scripts/ci/check_local_verify_environment.py:1-131`, and extends deterministic coverage for the fresh-clone bootstrap contract in `tests/test_check_local_verify_environment.py:1-168`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3933005101 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3933009220 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921397875 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921413066 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921417519 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921417522 -> 8977d3e6
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#discussion_r2921417524 -> 8977d3e6

Disposition: FIXED
Commit: edb07c47
Evidence: `edb07c47` reuses `VENV_BIN_DIR` for `VENV_PYTHON` in `scripts/ci/check_local_verify_environment.py:16-19` and restores the merge-readiness checklist to an unchecked pre-final-review state in `docs/review/PR_1127_FIXED_MAPPING.md:37-41`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1127#pullrequestreview-3933861078 -> edb07c47

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
