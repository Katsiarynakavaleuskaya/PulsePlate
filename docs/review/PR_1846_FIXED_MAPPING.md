# PR 1846 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- No actionable review comments

## Review Dispositions

### Implemented Fixes

- Disposition: FIXED
- Commit: `5b9aa041c`
- Evidence: `trivy/ignore-policy.rego`, `.trivyignore`, `docs/security/*`, `docs/roadmap/BACKLOG_LEDGER.md`, `scripts/ci/check_trivy_ignore_policy_expiry.py`, `tests/test_trivy_ignore_policy_expiry.py`, `scripts/ci/check_docs_phase1_gates.py`
- Reason: Expired Trivy suppression review window fixed by removing obsolete/fixed suppressions and retaining only residual exact-match suppressions through 2026-06-27.

- Disposition: FIXED
- Commit: `045c6d3c8`
- Evidence: `docs/security/CVE-2026-0915-glibc.md`, `docs/security/CVE-2026-33845-gnutls.md`, `docs/security/CVE-2026-33846-gnutls.md`, `docs/security/CVE-2025-14831-gnutls.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `scripts/ci/check_docs_phase1_gates.py`
- Reason: Post-open QA/security doc consistency findings fixed; removed suppressions now use historical wording and retained suppressions remain tracked.

## Lane Start Provenance

- Packet: `artifacts/orchestration/task_packets/d3b39ff0308a.json`

## Experiment Runner Evidence

- Not applicable: targeted security suppression-governance PR; deterministic security gates and role-agent security review are governing evidence.

## Deferred / Follow-ups

- None.

## Merge Readiness

- [ ] Current-head CI completed successfully
- [ ] Post-open role passes completed
- [ ] Bot review disposition completed
- [ ] Strict merge wrapper passed
- [ ] Wait-window completed
