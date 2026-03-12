# PR 1133 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 9482ab7c
Evidence: `deploy/Caddyfile.production:1`; `deploy/Caddyfile.production:31`; `docs/roadmap/BACKLOG_LEDGER.md:952`
Reason: The follow-up commit added method-preserving `www` redirects for production and fallback staging, and anchored/reordered the deferred ledger item called out by CodeRabbit.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#pullrequestreview-3934988798 -> 9482ab7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923236764 -> 9482ab7c

Disposition: FIXED
Commit: 9482ab7c
Evidence: `deploy/Caddyfile.production:1`; `deploy/Caddyfile.production:4`
Reason: The production `www` canonical redirect now uses HTTP 308 so API methods and request bodies are preserved across the apex redirect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923238024 -> 9482ab7c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923268368 -> 9482ab7c

Disposition: FIXED
Commit: 9482ab7c
Evidence: `docs/figma/orchestration/sessions/2026-03-12_domain_canonicalization/01_BASELINE_STATUS.md:26`
Reason: The baseline evidence keeps the operational finding but redacts the raw Figma Make file key from the repository.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923268382 -> 9482ab7c

Disposition: FIXED
Commit: 9482ab7c
Evidence: `docs/figma/FIGMA_MAKE_SYNC_AUDIT_HPP.md:36`
Reason: The stale evidence citation was corrected to the actual baseline section line.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923268391 -> 9482ab7c

Disposition: FIXED
Commit: 9482ab7c
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:952`; `docs/roadmap/BACKLOG_LEDGER.md:953`
Reason: The ledger item now has a stable HTML anchor and sits in deterministic P1 ordering ahead of the nearby design entries.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#discussion_r2923268401 -> 9482ab7c

Disposition: NOT-A-BUG
Evidence: The actionable inline findings from this wrapper review are already dispositioned in this artifact as `#discussion_r2923268368`, `#discussion_r2923268382`, `#discussion_r2923268391`, and `#discussion_r2923268401`.
Reason: The `pullrequestreview-3935024266` URL is a summary shell for those inline cubic findings and does not introduce an additional standalone defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1133#pullrequestreview-3935024266

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
