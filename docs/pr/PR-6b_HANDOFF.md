# PR-6b HANDOFF — iOS -only-testing Centralize (Sourcery Follow-up)

**Topic:** Centralize `-only-testing` xcodebuild list (ledger-p2-ios-agents-only-testing-centralize)
**Date:** 2026-03-16
**Status:** Ready for implementation

---

## Backlog

- [P2: iOS agents-only-testing centralize](../roadmap/BACKLOG_LEDGER.md#ledger-p2-ios-agents-only-testing-centralize)

---

## Scope

- Single source of truth for iOS unit test `-only-testing` list
- Future test-set changes require one edit (`scripts/ios_test_targets.sh`), not three (Makefile, ci.yml, ios/AGENTS.md)

---

## Non-goals

- Changing which tests run (same 14 tests as before)
- iOS test logic or coverage changes

---

## Files

- **New:** `scripts/ios_test_targets.sh` — canonical comma-separated list
- **Edit:** `Makefile` — use `$(shell ./scripts/ios_test_targets.sh)` for default ONLY_ITEMS
- **Edit:** `.github/workflows/ci.yml` — call script, pass output to Python xcodebuild step
- **Edit:** `ios/AGENTS.md` — remove 3 duplicated blocks; add canonical reference
- **Edit:** `docs/roadmap/BACKLOG_LEDGER.md` — update ledger-p2 when merged

---

## DoD

- [x] `scripts/ios_test_targets.sh` outputs 14-test comma-separated list
- [x] Makefile `ios-test` uses script when `IOS_ONLY_TESTING` unset
- [x] ci.yml ios-tests job uses script output
- [x] ios/AGENTS.md references script; no duplicated inline lists
- [ ] `make ios-test` passes
- [ ] `pre-commit run --all-files` passes
- [ ] `make verify` passes

---

## Merge gates (required)

- [ ] `python3 scripts/orchestration/check_preflight.py` — PASS
- [ ] `pre-commit run --all-files` — PASS
- [ ] `make verify` — PASS
