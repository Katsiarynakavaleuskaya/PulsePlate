# PR TBD Fixed Mapping - JWT / Fastlane Suppression Unblock Monitor

## Scope

- Dependabot alert `#142`: RubyGems `jwt` in `ios/Gemfile.lock`,
  `CVE-2026-45363` / `GHSA-c32j-vqhx-rx3x`, fixed version `3.2.0`.
- GitHub Code Scanning alert `#594`: same Trivy finding carried by the Bundler
  release-tooling graph.
- This PR is not a forced `jwt` fix. It is an unblock/revalidation PR with a
  monitor that fails when the suppression becomes removable.

## Discussion Thread Pass

- [ ] No unresolved actionable review threads remain after PR open.
- [ ] CodeRabbit/Sourcery/Cubic no-actionable status verified after PR open.

## Fixed In Commit Mapping

### Dependabot Alert #142 - Ruby `jwt` CVE-2026-45363

Disposition: DEFERRED.

Backlog:
`docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-remove-trivy-suppression-jwt-cve-2026-45363`

Evidence: fresh 2026-05-19 resolver output still selects `fastlane 2.234.0`
with `jwt (>= 2.1.0, < 3)` and `jwt 2.10.2`; GitHub reports the alert remains
open for `ios/Gemfile.lock` with patched version `3.2.0`.

### Premortem Finding - Date-Only Suppression Reminder Can False-Green

Disposition: FIXED.

Commit: da8e81b51.

Evidence: `scripts/ci/check_trivy_ignore_policy_expiry.py` now checks every
`Review-by` marker; `tests/test_trivy_ignore_policy_expiry.py` covers stale
review dates.

### Premortem Finding - Missing Resolver Unblock Detection

Disposition: FIXED.

Commit: da8e81b51.

Evidence: `scripts/ci/check_jwt_fastlane_unblock.py` parses Bundler output and
fails when `jwt >= 3.2.0` is reachable or Fastlane no longer constrains
`jwt < 3`; `tests/test_jwt_fastlane_unblock_guard.py` covers blocked and
unblocked graphs.

### Premortem Finding - Unsafe Forced Lockfile Override

Disposition: NOT-A-BUG.

Evidence: this PR does not change `ios/Gemfile` or `ios/Gemfile.lock`; the
resolver remains blocked by Fastlane's upstream `jwt < 3` contract.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path scripts/ci/check_jwt_fastlane_unblock.py --path scripts/ci/check_trivy_ignore_policy_expiry.py --path scripts/ci/check_current_head_pr_checks.py --path tests/test_jwt_fastlane_unblock_guard.py --path tests/test_trivy_ignore_policy_expiry.py --path tests/test_current_head_pr_checks.py --path docs/security/CVE-2026-45363-jwt-fastlane.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/review/PR_TBD_JWT_FASTLANE_PREMORTEM.md --path docs/review/PR_TBD_JWT_FASTLANE_FIXED_MAPPING.md --path trivy/ignore-policy.rego`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/ci/check_jwt_fastlane_unblock.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py`
- PASS: `.venv/bin/python -m pytest -q tests/test_current_head_pr_checks.py`
- PASS: `.venv/bin/python -m pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py`
- PASS: `.venv/bin/python -m ruff check scripts/ci/check_jwt_fastlane_unblock.py scripts/ci/check_trivy_ignore_policy_expiry.py scripts/ci/check_current_head_pr_checks.py tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py tests/test_current_head_pr_checks.py`
- PASS: `.venv/bin/python -m black --check scripts/ci/check_jwt_fastlane_unblock.py scripts/ci/check_trivy_ignore_policy_expiry.py scripts/ci/check_current_head_pr_checks.py tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py tests/test_current_head_pr_checks.py`
- PASS: `.venv/bin/python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-45363-jwt-fastlane.md docs/roadmap/BACKLOG_LEDGER.md docs/review/PR_TBD_JWT_FASTLANE_PREMORTEM.md docs/review/PR_TBD_JWT_FASTLANE_FIXED_MAPPING.md`
- PASS: `VENV_PYTHON=/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/.venv/bin/python pre-commit run --all-files`
- PENDING: `make validate-changed`

Full local `make verify` is deferred under the operator-approved machine-heavy
exception. This PR relies on focused local gates plus current-head CI parity
before any readiness claim.

## Merge Readiness

- [ ] PR body Phase 2 gates pass after PR open.
- [ ] Review-thread disposition guard passes with auth after PR open.
- [ ] Strict merge-readiness wrapper passes with auth after current-head CI.
- [ ] Current-head required CI is terminal/pass.
