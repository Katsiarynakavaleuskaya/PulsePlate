# PR 1305 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: de8b7a36
Evidence: trivy/ignore-policy.rego:36
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1305#discussion_r3030302201 -> de8b7a36
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1305#pullrequestreview-4053137261 -> de8b7a36

Disposition: NOT-A-BUG
Evidence: docs/security/CVE-2026-4046-glibc.md:70; docs/roadmap/BACKLOG_LEDGER.md:2511
Reason: The ledger evidence anchor exists in the updated lane, and the explicit two-package `PkgID` checks intentionally keep the suppression scoped to the exact observed `libc6` and `libc-bin` alerts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1305#pullrequestreview-4053135922

## Merge Readiness
- [ ] Local verification completed
- [ ] Current-head CI green
- [ ] No unresolved review threads
- [ ] Dependency lane merged
