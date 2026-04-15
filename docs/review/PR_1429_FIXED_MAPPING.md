<!-- markdownlint-disable MD034 -->
# PR #1429 — Fixed in Commit Mapping (canonical)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads are dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085416208
Disposition: FIXED
Commit: 81bf0b975
Evidence: `scripts/ci/install_locked_python_requirements.py:873` (`run_command` captures subprocess stdout/stderr and folds them into `RuntimeError` text so `_resolver_miss_error` can match pip “No matching distribution …” output).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085416213
Disposition: FIXED
Commit: 81bf0b975
Evidence: `scripts/ci/install_locked_python_requirements.py:1273` enforces `--require-virtualenv` before `scripts/ci/install_locked_python_requirements.py:1278` (`--upgrade-pip`), so pip is not upgraded outside an interpreter refusal path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085436155
Disposition: FIXED
Commit: 79c21ea02
Evidence: `tests/test_install_locked_python_requirements.py:18-24` defines `_resolver_miss_runtimeerror_like_run_command`; `tests/test_install_locked_python_requirements.py:1720` and `tests/test_install_locked_python_requirements.py:1806` raise it in emergency preflight resolver-miss tests; `tests/test_install_locked_python_requirements.py:1046-1062` extends `test_run_command_wraps_subprocess_failures` to assert stderr text is included in the `RuntimeError` message.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085477602
Disposition: FIXED
Commit: 79c21ea02
Evidence: `.github/actions/python-setup/action.yml:60`, `:78`, `:166`, and `:176` replace `set -euxo pipefail` with `set -euo pipefail` so bash xtrace cannot echo expanded `PULSEPLATE_PYTHON_INDEX_URL` values into logs.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085646506
Disposition: FIXED
Commit: bddb80887
Evidence: `docs/review/PR_1429_FIXED_MAPPING.md` evidence lines for `discussion_r3085436155` and `discussion_r3085477602` now use strict `file:line` anchors (`tests/test_install_locked_python_requirements.py:18-24`, `:1720`, `:1806`, `:1046-1062`; `.github/actions/python-setup/action.yml:60`, `:78`, `:166`, `:176`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085622859
Disposition: NOT-A-BUG
Evidence: `scripts/ci/install_locked_python_requirements.py` (`run_command`): including captured stderr in `RuntimeError` is required for resolver-miss detection and CI triage; index URLs come from CI env (not user paste). Heuristic redaction/truncation of subprocess output is product-hardening scope—track separately if we want bounded error blobs policy-wide.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085622872
Disposition: NOT-A-BUG
Evidence: `tests/test_install_locked_python_requirements.py` already exercises `--preflight-only` through `main` with proxy/emergency flags; adding sentinel monkeypatches for every forwarded argument is optional coverage expansion, not a correctness gap for this PR.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085630237
Disposition: NOT-A-BUG
Evidence: `run_command` captures output only where subprocess diagnostics are required (pip failure analysis / preflight). Long installs in CI are bounded by workflow `timeout-minutes` and step logs; switching wheelhouse paths back to inherited stdio would lose stderr needed for this PR’s resolver-miss contract.

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
