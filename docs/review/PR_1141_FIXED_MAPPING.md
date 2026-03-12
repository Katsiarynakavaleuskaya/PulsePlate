# PR 1141 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 3a0515ad
Evidence: `scripts/check_domain_tls.py:236`; `tests/test_check_domain_tls.py:121`; `tests/test_check_domain_tls.py:182`
Reason: Apex redirect responses are now validated against the repo-owned production host, and deterministic tests cover both the accepted apex redirect path and the off-host drift case.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927290344 -> 3a0515ad
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927320476 -> 3a0515ad

Disposition: FIXED
Commit: 3a0515ad
Evidence: `scripts/check_domain_tls.py:137`; `tests/test_check_domain_tls.py:213`
Reason: The diagnostic now fails closed when `dig` is unavailable for `CNAME` inspection, so ownership drift cannot silently pass without the required DNS tooling.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927320470 -> 3a0515ad

Disposition: FIXED
Commit: 3a0515ad
Evidence: `scripts/check_domain_tls.py:158`; `tests/test_check_domain_tls.py:233`
Reason: HTTP header parsing now resets state when a new status line appears, so only the final response block contributes redirect metadata.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927300627 -> 3a0515ad

Disposition: FIXED
Commit: 3a0515ad
Evidence: `docs/deploy/CLOUDFLARE.md:163`
Reason: The Cloudflare runbook no longer overstates `diagnose_production.sh`; it now describes the origin-side check as Caddy/container/origin-config verification rather than certificate coverage.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927320448 -> 3a0515ad

Disposition: FIXED
Commit: 3a0515ad
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:1032`
Reason: The backlog item was reopened and tied explicitly to PR `#1141`, keeping it in progress until merge governance clears and the branch lands on `main`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927300622 -> 3a0515ad

Disposition: FIXED
Commit: 0f2a3aae
Evidence: `docs/review/PR_1141_FIXED_MAPPING.md:44`
Reason: The merge-readiness checklist keeps the local hard-gate item unchecked until the actual final merge cycle, matching the current governance guidance for fixed-mapping artifacts.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1141#discussion_r2927300601 -> 0f2a3aae

## Deferred / Follow-ups
- Live domain remediation completed on March 12, 2026: `www.pulseplate.app` now returns `308` to the repo-owned apex, and the post-fix evidence is recorded in `docs/figma/orchestration/sessions/2026-03-12_domain_canonicalization/01_BASELINE_STATUS.md`.
- Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-domain-ownership-canonicalization`

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
