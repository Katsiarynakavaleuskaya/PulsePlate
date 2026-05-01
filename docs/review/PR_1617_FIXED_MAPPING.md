# PR 1617 Fixed in Commit Mapping

## PR

- PR: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617
- Branch: `security/code-scanning-588-libcap2-cve-2026-4878`
- Scope: Triage libcap2 CVE-2026-4878 Trivy alert 588

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Status: CodeRabbit reviewed, Sourcery reviewed, Cubic reviewed. All actionable findings addressed.
- Review threads resolved by this artifact: 4 (see mapping below).
- Actionable review comments: all mapped.

## Fixed in Commit Mapping

Disposition: FIXED
Evidence: `docs/security/CVE-2026-4878-libcap2.md:78` — pluralized "check" to "checks"
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617#discussion_r3174936709 -> 783a89378

Disposition: FIXED
Evidence: `trivy/ignore-policy.rego:299` — added Docker Hub image ref branch `startswith(input.Image, "katsiarynakavaleuskaya/pulseplate")` to match alert #588 evidence image
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617#discussion_r3174939522 -> 783a89378

Disposition: FIXED
Evidence: `docs/security/CVE-2026-4878-libcap2.md:32` — updated doc to accurately describe image/distro fallback scope and residual risk
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617#discussion_r3174946600 -> 783a89378

Disposition: NOT-A-BUG
Evidence: `trivy/ignore-policy.rego:139` — `not input.Image` and `not input.Distro` fallbacks are the canonical repo pattern (used by libgcrypt20 CVE-2026-41989 at lines 145-157). Removing them would break suppression when Trivy does not populate these fields. The doc is now updated to describe this fallback scope accurately.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1617#discussion_r3174946602

## Local Validation Evidence

- PASS: `python3 scripts/orchestration/check_preflight.py`
- PASS: `python3 scripts/orchestration/check_agent_consistency.py`
- PASS: `python3 scripts/ci/check_trivy_ignore_policy_expiry.py`
- PASS: `pre-commit run --all-files`
- PASS: `pytest -q tests/test_repo_policy_guards.py`
- PASS: `make test-fast`
- PASS: `make lint`

## Merge Readiness

- [x] Local gates green (check_preflight, check_agent_consistency, pre-commit, test-fast, lint, policy guards)
- [x] Trivy expiry check green
- [x] CI current-head checks green (all required checks pass, 2026-05-01)
- [x] All bot comments addressed (CodeRabbit, Sourcery, Cubic)
- [x] Canonical review artifact created
- [x] `check_review_threads_disposition.py --require-auth` PASS
- [x] `check_pr_merge_readiness.py` PASS
- [x] Pre-push hooks passed (pip-audit, backend tests, bandit)
- [ ] Wait-window elapsed after last review activity

## Deferred / Follow-ups

- Remove Trivy suppression for libcap2 CVE-2026-4878 after upstream fix — tracked in `docs/roadmap/BACKLOG_LEDGER.md` (P1).
