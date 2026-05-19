<!-- markdownlint-disable MD013 MD034 -->
# PR #1770 - Fixed in Commit Mapping

**PR:** fix(deps): raise idna security floor
**Branch:** `codex/security-idna-3-15-dependabot-alerts`

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed
- [ ] Post-open `qa-engineer-agent -> bug-hunter` pass completed
- [ ] CodeRabbit, Sourcery, Cubic, and review-thread no-actionable status verified

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b1a74e849593e3c7289fc029ac69ae807bf37833
Evidence: `tests/test_install_locked_python_requirements.py:339` verifies all seven alert surfaces pin `idna==3.15`, no repo-managed requirement profile returns to `idna==3.11`, and no active emergency fallback exists for `idna`.

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`
Evidence: `docs/security/CVE-2026-45363-jwt-fastlane.md:28` records the 2026-05-19 resolver recheck. `ios/Gemfile.lock:103` keeps Fastlane on `jwt >= 2.1.0, < 3`, so Dependabot alert #142 is not force-fixed in this PR.

Disposition: NOT-A-BUG
Evidence: `pip index versions idna --index-url "$PULSEPLATE_PYTHON_INDEX_URL"` confirmed `idna (3.15)` is exposed by the approved private index. The Dependabot updater failure was a broad resolver failure, not proof that the exact patched `idna` wheel is unavailable.

Disposition: FIXED
Commit: b1a74e849593e3c7289fc029ac69ae807bf37833
Evidence: exact `idna==3.15` pins plus regression coverage in `tests/test_install_locked_python_requirements.py:339`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/145 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/146 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/147 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/148 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/149 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/150 -> b1a74e849593e3c7289fc029ac69ae807bf37833
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/151 -> b1a74e849593e3c7289fc029ac69ae807bf37833

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`
Evidence: `docs/security/CVE-2026-45363-jwt-fastlane.md:28` and `ios/Gemfile.lock:103` record the Fastlane `jwt < 3` blocker.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/security/dependabot/142

Disposition: FIXED
Commit: fc4ca0ed4
Evidence: `docs/review/PR_1770_PREMORTEM.md:62` now uses the clearer wording suggested by Sourcery. `tests/test_install_locked_python_requirements.py:17` defines shared idna floor constants and the test uses one repo requirements scan instead of rereading the same files through separate loops.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1770#pullrequestreview-4322175139 -> fc4ca0ed4
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1770#discussion_r3268835017 -> fc4ca0ed4

## Validation

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --task-class security --pr-phase pre_open`
- PASS: `python3 scripts/orchestration/task_bootstrap.py --task-class security --pr-phase post_open_review`
- PASS: `python -m pytest -q tests/test_install_locked_python_requirements.py tests/test_python_supply_chain_controls.py tests/guards/test_security_devtooling_regression_guards.py`
- PASS: `make validate-changed`
- PASS: `pre-commit run --all-files`
- PASS: pre-push hooks including backend tests, full-repo Bandit, and Docker build test
- PASS: `pip index versions idna --index-url "$PULSEPLATE_PYTHON_INDEX_URL"` confirmed `idna (3.15)`
- PASS: `cd ios && bundle lock --update fastlane jwt googleauth signet --print` confirmed Fastlane still resolves `jwt (2.10.2)` and requires `jwt >= 2.1.0, < 3`

## Validation Caveats

Full local `make verify` is deferred under the operator-approved machine-heavy
exception. Per-profile dry-run resolution confirmed `idna-3.15` for
`requirements.txt`, `requirements-dev.txt`, `requirements-ci-lite.txt`,
`requirements-docker-runtime.txt`, and `requirements-lock.txt`. Local macOS
dry-runs for `requirements-rag-vector.txt` and `requirements-rag-vector-cpu.txt`
are blocked by existing non-idna profile constraints (`cuda-bindings==13.2.0`
and `torch==2.11.0+cpu` distribution exposure respectively), so current-head CI
parity remains the heavy signal for those profiles.
