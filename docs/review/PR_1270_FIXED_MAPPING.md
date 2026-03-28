# PR 1270 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: NOT-A-BUG
Evidence: `scripts/ci/check_pygments_exception_guard.py:27` (`TRACKED_REQUIREMENTS` is the code-level source of truth); `docs/security/GHSA-5239-wwwm-4pmq-pygments.md:8`; `docs/roadmap/BACKLOG_LEDGER.md:7856`
Reason: The tracked Pygments surfaces are already centralized in code for enforcement. The matching docs/backlog entries intentionally mirror that list as explicit governance artifacts for auditability and operator readability; replacing this narrow seam with pattern-based auto-discovery is a broader design change, not a defect in the current security remediation PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1270#pullrequestreview-4025908838

Disposition: FIXED
Commit: 503e3c03cf9ea58887b84609bd64f62600310389
Evidence: `tests/test_check_pygments_exception_guard.py` (`test_evaluate_guard_state_flags_requirements_test_only_regression`)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1270#pullrequestreview-4025910961 -> 503e3c03cf9ea58887b84609bd64f62600310389

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [x] Pre-commit green
- [x] `make verify` green
- [x] Mandatory post-open bug-hunter pass completed
Notes: Draft PR `#1270` is the security-first remediation lane requested after merged PR `#1269`. The code change is intentionally narrow: carry the safe npm lockfile remediation already proposed for GitHub alerts `#76`, `#82`, and `#83`, then refresh the Pygments seam documentation/backlog for still-open GitHub alerts `#80` and `#81`, which remain upstream-blocked because `GHSA-5239-wwwm-4pmq` still exposes no patched release. The post-open bug-hunter pass found a real contract drift between the documented Pygments alert surfaces and `scripts/ci/check_pygments_exception_guard.py`; that finding was fixed in commit `6b023e26` by tracking `requirements-test.txt`, updating the guard tests, and correcting the security note wording. The branch stays isolated from the Postgres foundation slice and from unrelated feature or infra work.
