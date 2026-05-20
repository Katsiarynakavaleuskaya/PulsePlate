# PR 1772 Fixed Mapping - JWT / Fastlane Suppression Unblock Monitor

## Scope

- Dependabot alert `#142`: RubyGems `jwt` in `ios/Gemfile.lock`,
  `CVE-2026-45363` / `GHSA-c32j-vqhx-rx3x`, fixed version `3.2.0`.
- GitHub Code Scanning alert `#594`: same Trivy finding carried by the Bundler
  release-tooling graph.
- This PR is not a forced `jwt` fix. It is an unblock/revalidation PR with a
  monitor that fails when the suppression becomes removable.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: see mapping entries below
Evidence: bot findings were fixed in code/docs and revalidated with focused local gates plus current-head CI on head `27114aa15`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269647532
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269647558
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323216766
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269661762
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269661769
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670933
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670942
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670948
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269688860
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269764142
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269764152
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323359508
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777107
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777109
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777110
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323399365
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269797639
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269797642

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269647532 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269647558 -> b4d3b6dc8
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323216766 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269661762 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269661769 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670933 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670942 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269670948 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269688860 -> 0146902ae
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269764142 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269764152 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323359508 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777107 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777109 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269777110 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#pullrequestreview-4323399365 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269797639 -> e337af86a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1772#discussion_r3269797642 -> e337af86a

## Premortem And Alert Dispositions

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

### Bug-Hunter Finding - Constraint Parser Can False-Green Unblock State

Disposition: FIXED.

Commit: 0146902ae.

Evidence: `scripts/ci/check_jwt_fastlane_unblock.py` now parses comparison
operators instead of substring-matching `<3`; `tests/test_jwt_fastlane_unblock_guard.py`
covers `< 3.2` and `3.2.0.rc1` edge cases.

### Bug-Hunter Finding - Invalid `Review-by` Dates Crash Parser

Disposition: FIXED.

Commit: 0146902ae.

Evidence: `scripts/ci/check_trivy_ignore_policy_expiry.py` now converts invalid
`Suppression expires` and `Review-by` dates into deterministic policy failures;
`tests/test_trivy_ignore_policy_expiry.py` covers both cases.

### Bug-Hunter Finding - Current-Head Fallback Misses `test-main` Matrix Names

Disposition: FIXED.

Commit: 0146902ae.

Evidence: `scripts/ci/check_current_head_pr_checks.py` now allowlists
`test-main (3.11, 60)`, `test-main (3.12, 90)`, and `test-main (3.13, 90)`;
`tests/test_current_head_pr_checks.py` derives those names from workflow matrix
`timeout-minutes`.

### Bug-Hunter Finding - Checkout Credentials Persist In Read-Only Guard Job

Disposition: FIXED.

Commit: 0146902ae.

Evidence: `.github/workflows/ci.yml` sets `persist-credentials: false` on the
new `Ruby jwt/Fastlane unblock guard` checkout step.

### Bug-Hunter Finding - Security Note Line Anchor Is Stale

Disposition: FIXED.

Commit: 0146902ae.

Evidence: `docs/security/CVE-2026-45363-jwt-fastlane.md` now points to the
current `trivy/ignore-policy.rego:443` rule line.

### Bug-Hunter Finding - Validation Evidence Uses Host-Specific Python Path

Disposition: FIXED.

Commit: 0146902ae.

Evidence: this artifact and the PR body now use portable `python` commands
after `. .venv/bin/activate` rather than absolute host-local interpreter paths.

## Split Justification

This PR intentionally stays together as one security-governance lane because
the `jwt` alert cannot be safely fixed in `ios/Gemfile.lock` until Fastlane
permits a patched `jwt` resolver path. The code guard, suppression expiry
guard, regression tests, security note, backlog anchor, and review mapping are
one auditable control set for Dependabot alert `#142` / `CVE-2026-45363`.
Splitting them would leave either the suppression without an unblock monitor or
the monitor without the canonical suppression/backlog evidence. No runtime API,
OpenAPI, frontend, or iOS app behavior changes are included.

## Local Validation

- PASS: `python3 scripts/orchestration/check_preflight.py --path .github/workflows/ci.yml --path scripts/ci/check_jwt_fastlane_unblock.py --path scripts/ci/check_trivy_ignore_policy_expiry.py --path scripts/ci/check_current_head_pr_checks.py --path tests/test_jwt_fastlane_unblock_guard.py --path tests/test_trivy_ignore_policy_expiry.py --path tests/test_current_head_pr_checks.py --path docs/security/CVE-2026-45363-jwt-fastlane.md --path docs/roadmap/BACKLOG_LEDGER.md --path docs/review/PR_1772_PREMORTEM.md --path docs/review/PR_1772_FIXED_MAPPING.md --path trivy/ignore-policy.rego`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `python3 scripts/ci/check_jwt_fastlane_unblock.py`
- PASS: `python -m pytest -q tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py`
- PASS: `python -m pytest -q tests/test_current_head_pr_checks.py`
- PASS: `python -m pytest -q tests/guards/test_subprocess_uses_absolute_binaries.py tests/guards/test_nosec_policy_guard.py`
- PASS: `python -m ruff check scripts/ci/check_jwt_fastlane_unblock.py scripts/ci/check_trivy_ignore_policy_expiry.py scripts/ci/check_current_head_pr_checks.py tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py tests/test_current_head_pr_checks.py`
- PASS: `python -m black --check scripts/ci/check_jwt_fastlane_unblock.py scripts/ci/check_trivy_ignore_policy_expiry.py scripts/ci/check_current_head_pr_checks.py tests/test_jwt_fastlane_unblock_guard.py tests/test_trivy_ignore_policy_expiry.py tests/test_current_head_pr_checks.py`
- PASS: `python scripts/ci/check_docs_phase1_gates.py --files docs/security/CVE-2026-45363-jwt-fastlane.md docs/roadmap/BACKLOG_LEDGER.md docs/review/PR_1772_PREMORTEM.md docs/review/PR_1772_FIXED_MAPPING.md`
- PASS: `. .venv/bin/activate && pre-commit run --all-files`
- PASS: `. .venv/bin/activate && make validate-changed`

Full local `make verify` is deferred under the operator-approved machine-heavy
exception. This PR relies on focused local gates plus current-head CI parity
before any readiness claim.

## Merge Readiness

- [ ] PR body Phase 2 gates pass after PR open.
- [ ] Review-thread disposition guard passes with auth after PR open.
- [ ] Strict merge-readiness wrapper passes with auth after current-head CI.
- [ ] Current-head required CI is terminal/pass.
