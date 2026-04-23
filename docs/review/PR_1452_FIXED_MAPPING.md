# PR #1452 - Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

Canonical review-governance artifact and PR-body mirror requirements:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:41-90`;
`docs/orchestration/AGENTS.md:79-82`.

Current GitHub review surface for PR `#1452` was re-checked on `23 April 2026`:

- actionable Sourcery review:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#pullrequestreview-4131518820`
- actionable Sourcery inline comments:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#discussion_r3102744914`,
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#discussion_r3102744917`
- non-actionable bot comments / reviews:
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#issuecomment-4270680767`
  (CodeRabbit rate-limit/system comment),
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#issuecomment-4270681804`
  (Sourcery review guide),
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#pullrequestreview-4131575203`
  (cubic "No issues found"),
  `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#issuecomment-4270723398`
  (Codecov coverage report)

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#discussion_r3102744914 -> 939c6b196
Disposition: FIXED
Commit: 939c6b196
Evidence: `tests/test_dependency_security_guard.py:46-53` defines VCS/editable prefixes, `tests/test_dependency_security_guard.py:167-173` rejects URL/VCS/editable requirement entries on guarded surfaces, and `tests/test_dependency_security_guard.py:313-335` parameterizes direct URL, VCS, `-e`, and `--editable` regression cases. Local proof before mapping: `python3 -m pytest -q tests/test_dependency_security_guard.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#discussion_r3102744917 -> 939c6b196
Disposition: FIXED
Commit: 939c6b196
Evidence: `tests/test_dependency_security_guard.py:169-171` includes `path.name` in the fail-fast diagnostic, and `tests/test_dependency_security_guard.py:331-334` asserts `requirements.txt` is present in the raised error message. Local proof before mapping: `python3 -m pytest -q tests/test_dependency_security_guard.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1452#pullrequestreview-4131518820 -> 881240c82
Disposition: FIXED
Commit: 881240c82
Evidence: `tests/test_dependency_security_guard.py:331-334` now catches `pytest.fail.Exception` instead of broad `BaseException`, while the VCS/editable and filename inline obligations remain covered at `tests/test_dependency_security_guard.py:313-335`. The framework-decoupling suggestion is intentionally not adopted because this file is a pytest-native repository guard and existing helper contract uses `pytest.fail(...)` consistently for guard diagnostics. Local proof before mapping: `python3 -m pytest -q tests/test_dependency_security_guard.py`.

## Merge Readiness

Merge-readiness contract:
`AGENTS.md:42-52`; `docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:93-112`;
`docs/orchestration/PR_ORCHESTRATION_CONTRACT_MATRIX.md:153-216`.

- [ ] Current-head CI is green for PR branch head
  Evidence: pending fresh push/check cycle after this mapping artifact.
- [ ] Required checks complete (no pending jobs)
  Evidence: pending `gh pr checks 1452` and strict wrapper on current head.
- [ ] All review threads resolved on GitHub after disposition updates
  Evidence: actionable current-head threads are dispositioned above and require
  explicit GitHub resolution only after the updated branch head is pushed.
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
  Evidence: actionable Sourcery review and both inline Sourcery comments are
  mapped above; non-actionable bot/system comments are listed in the discussion
  pass.
- [ ] Pre-commit green on latest pushed head
  Evidence: pending `pre-commit run --all-files` before push.
- [ ] `make verify` green on latest pushed head
  Evidence: pending `make verify` before merge-ready claim.

## Deferred / Follow-ups

- None.
