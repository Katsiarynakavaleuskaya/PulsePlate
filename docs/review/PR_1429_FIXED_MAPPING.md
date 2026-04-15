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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085436142
Disposition: FIXED
Commit: 81bf0b975
Evidence: `docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:169` qualifies that policy/guard checks stay deterministic while the optional `--preflight-only` path performs network reads against `PULSEPLATE_PYTHON_INDEX_URL` (and may use `scripts/ci/emergency_python_wheels.json`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085436146
Disposition: FIXED
Commit: 81bf0b975
Evidence: `scripts/ci/install_locked_python_requirements.py:722-724` rejects non-object JSON roots before `payload.get("min_versions")`, so malformed schema files raise the script’s stable `RuntimeError` shape.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085436150
Disposition: FIXED
Commit: 81bf0b975
Evidence: `scripts/ci/install_locked_python_requirements.py:879-904` (`run_command`) folds captured pip stdout/stderr into `RuntimeError` text so `_resolver_miss_error` can match “No matching distribution …” output on real resolver misses.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085477600
Disposition: FIXED
Commit: 81bf0b975
Evidence: same as `discussion_r3085436150`: `scripts/ci/install_locked_python_requirements.py:879-904` preserves pip stderr/stdout on non-zero exits for floor-preflight resolver-miss matching.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085477615
Disposition: FIXED
Commit: 79c21ea02
Evidence: `scripts/ci/install_locked_python_requirements.py:1277-1284` enforces `args.require_virtualenv` + `is_virtualenv_python(...)` before `args.upgrade_pip` / `upgrade_pip(...)`, so pip is not upgraded outside the guarded interpreter refusal path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085477622
Disposition: FIXED
Commit: 81bf0b975
Evidence: same as `discussion_r3085436146`: `scripts/ci/install_locked_python_requirements.py:722-724`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085477628
Disposition: FIXED
Commit: 79c21ea02
Evidence: same as `discussion_r3085436155`: `tests/test_install_locked_python_requirements.py:18-24` (`_resolver_miss_runtimeerror_like_run_command`), `:1720`, `:1806`, and `:1046-1062` align stubbed failures with the production `run_command` error contract.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#discussion_r3085702790
Disposition: NOT-A-BUG
Evidence: `scripts/ci/install_locked_python_requirements.py` `run_command` intentionally captures subprocess text so failures include pip stderr for resolver-miss and floor preflight; streaming install logs is a separate UX trade-off from this PR’s diagnostic contract (same rationale as `discussion_r3085630237`).




- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112374782
Disposition: NOT-A-BUG
Evidence: `tests/fixtures/dependency_security_schema.json` remains the canonical on-disk schema path exercised by `tests/test_dependency_security_guard.py`; `build_floor_preflight_command`/`run_dependency_floor_preflight` pairing is an internal helper seam for this PR and does not change intake correctness.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112412648
Disposition: FIXED
Commit: 81bf0b975
Evidence: CodeRabbit umbrella “Actionable comments posted: 4” maps to the same fixes as inline threads `discussion_r3085436142`, `discussion_r3085436146`, `discussion_r3085436150`, and `discussion_r3085436155` (`docs/security/DEPENDENCY_SECURITY_GUARD_WORKFLOW.md:169`; `scripts/ci/install_locked_python_requirements.py:722-724` and `:879-904`; tests cited under `discussion_r3085436155`).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112460492
Disposition: FIXED
Commit: 81bf0b975
Evidence: Cubic umbrella maps to inline threads `discussion_r3085477600`, `discussion_r3085477602`, `discussion_r3085477615`, `discussion_r3085477622`, and `discussion_r3085477628` (see disposition evidence on those URLs).

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112490721
Disposition: FIXED
Commit: 79c21ea02
Evidence: CodeRabbit duplicate-review summary tracks the resolver-miss test contract updates captured under `discussion_r3085436155` and `discussion_r3085477628`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112611397
Disposition: NOT-A-BUG
Evidence: Follow-up refactors (explicit schema path injection, explicit `--dest` parameterization, short-circuit emergency downloads) are optional hardening; this PR’s behavior is covered by tests and does not change the dependency intake contract.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112637471
Disposition: FIXED
Commit: bddb80887
Evidence: mapping evidence tightened to strict `file:line` anchors as described under `discussion_r3085646506`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1429#pullrequestreview-4112701663
Disposition: NOT-A-BUG
Evidence: same rationale as `discussion_r3085702790`: captured subprocess text is required for resolver-miss diagnostics; streaming logs is a separate UX follow-up.

## Merge Readiness

- [ ] Current-head CI is green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
<!-- markdownlint-enable MD034 -->
