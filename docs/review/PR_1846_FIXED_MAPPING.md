# PR 1846 Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#discussion_r3317184753 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; local `scripts/ci/check_docs_phase1_gates.py` passed for changed security docs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#discussion_r3317231922 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; local `scripts/ci/check_docs_phase1_gates.py` passed for changed security docs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#discussion_r3317231930 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; local `scripts/ci/check_docs_phase1_gates.py` passed for changed security docs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#discussion_r3317231935 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; local `scripts/ci/check_docs_phase1_gates.py` passed for changed security docs.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#discussion_r3317656226 -> 92a2b5c13
Disposition: FIXED
Commit: 92a2b5c13
Evidence: `docs/review/PR_1846_FIXED_MAPPING.md`; fixed mapping was expanded after the review comment timestamp.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#pullrequestreview-4380245206 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`; Sourcery actionable doc comments were fixed or made stale by removing test-only/active-suppression wording.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#pullrequestreview-4380298335 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; CodeRabbit comments were fixed in docs and mapping.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#issuecomment-4563326856 -> 8084d2717
Disposition: FIXED
Commit: 8084d2717
Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`, `docs/roadmap/BACKLOG_LEDGER.md`; CodeRabbit summary actionables were fixed in docs and mapping.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#pullrequestreview-4380804411 -> 92a2b5c13
Disposition: FIXED
Commit: 92a2b5c13
Evidence: `docs/review/PR_1846_FIXED_MAPPING.md`; latest CodeRabbit review-thread mapping was added after the comment timestamp.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1846#issuecomment-4564093996 -> 92a2b5c13
Disposition: FIXED
Commit: 92a2b5c13
Evidence: `docs/review/PR_1846_FIXED_MAPPING.md`; latest CodeRabbit summary mapping was added after the comment timestamp.

## Review Dispositions

### Implemented Fixes

- Disposition: FIXED
- Commit: 5b9aa041c
- Evidence: `trivy/ignore-policy.rego`, `.trivyignore`, `docs/security/*`, `docs/roadmap/BACKLOG_LEDGER.md`, `scripts/ci/check_trivy_ignore_policy_expiry.py`, `tests/test_trivy_ignore_policy_expiry.py`, `scripts/ci/check_docs_phase1_gates.py`
- Reason: Expired Trivy suppression review window fixed by removing obsolete/fixed suppressions and retaining only residual exact-match suppressions through 2026-06-27.

- Disposition: FIXED
- Commit: 045c6d3c8
- Evidence: `docs/security/CVE-2026-0915-glibc.md`, `docs/security/CVE-2026-33845-gnutls.md`, `docs/security/CVE-2026-33846-gnutls.md`, `docs/security/CVE-2025-14831-gnutls.md`, `docs/roadmap/BACKLOG_LEDGER.md`, `scripts/ci/check_docs_phase1_gates.py`
- Reason: Post-open QA/security doc consistency findings fixed; removed suppressions now use historical wording and retained suppressions remain tracked.

- Disposition: FIXED
- Commit: 8084d2717
- Evidence: `docs/security/CVE-2025-14831-gnutls.md`, `docs/security/CVE-2026-29111-systemd.md`, `docs/security/CVE-2026-4878-libcap2.md`
- Reason: CodeRabbit/Sourcery review comments addressed with historical suppression wording, immutable mapping evidence, and typo fix.

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
