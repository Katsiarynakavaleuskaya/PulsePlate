# PR 1381 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#pullrequestreview-4085529481 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060753041 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060753142 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#pullrequestreview-4085556378 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060775789 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060775806 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060775809 -> 96cd93f20
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1381#discussion_r3060775815 -> 96cd93f20
Disposition: FIXED
Commit: 96cd93f20
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:205` and `docs/roadmap/BACKLOG_LEDGER.md:208` now use the concrete PR reference and consistent `release-truth` wording; `frontend/src/mocks/__tests__/purchase.test.ts:1-50` now checks runtime MSW matcher behavior across handler predicates instead of relying on `info.path` and adds explicit TypeScript annotations; `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:59` adds the explicit async return type; `docs/review/PR_1381_FIXED_MAPPING.md:13-18` keeps merge-readiness checkboxes unchecked until the final merge cycle.

## Merge Readiness

- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green
- [ ] Mandatory post-open `qa-engineer-agent -> bug-hunter` pass completed
- Scope: frontend closeout for `ledger-p0-web-entitlement-truth`, limited to canonical web entitlement truth, fail-closed paywall behavior, and stale mock/release-path cleanup.
