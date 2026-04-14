# PR 1416 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: [tests/test_payments_activation_paywall_events.py](../../tests/test_payments_activation_paywall_events.py#L68), [frontend/src/lib/analytics.ts](../../frontend/src/lib/analytics.ts#L31)
Reason: Sourcery follow-ups for deterministic activation lineage assertions and memoized hidden-ingestion import were fixed in earlier review passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074758628 -> bba685ea0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074758638 -> 055c113b5

Disposition: FIXED
Commit: see mapping entries below
Evidence: [app/schemas/paywall_analytics.py](../../app/schemas/paywall_analytics.py#L36), [app/routers/paywall_analytics.py](../../app/routers/paywall_analytics.py#L36), [app/main.py](../../app/main.py#L205), [app/services/paywall_exposure_ledger.py](../../app/services/paywall_exposure_ledger.py#L143), [tests/test_paywall_exposure_ledger_api.py](../../tests/test_paywall_exposure_ledger_api.py#L124), [tests/test_paywall_exposure_ledger_service.py](../../tests/test_paywall_exposure_ledger_service.py#L106), [tests/test_main_paywall_bootstrap.py](../../tests/test_main_paywall_bootstrap.py#L44)
Reason: Hardened the hidden paywall ledger path by splitting client/server event enums, requiring trusted first-party provenance or authenticated context, enforcing correct route ownership during bootstrap, removing raw payment identifiers from analytics metadata, making the Alembic revision deterministic, and adding targeted coverage for the new branches.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074768785 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074805532 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074805537 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806360 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806365 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806369 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806372 -> db3446f6e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806387 -> db3446f6e

Disposition: FIXED
Commit: 6d1e7d2e1
Evidence: [docs/review/PR_1416_FIXED_MAPPING.md](./PR_1416_FIXED_MAPPING.md#L1)
Reason: Merge-readiness checkboxes were reset to unchecked and the artifact now uses thread-specific mapping evidence instead of the earlier ambiguous review-level references.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806376 -> 6d1e7d2e1

Disposition: FIXED
Commit: adbfbe91c
Evidence: [frontend/src/lib/analytics.ts](../../frontend/src/lib/analytics.ts#L37)
Reason: The paywall analytics client import cache now resets after a transient dynamic-import failure, so the next exposure post can recover instead of reusing a poisoned rejected promise.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074827076 -> adbfbe91c

Disposition: FIXED
Commit: ee85df1b0
Evidence: [docs/review/PR_1416_FIXED_MAPPING.md](./PR_1416_FIXED_MAPPING.md#L8)
Reason: Canonical evidence links in the PR 1416 artifact were normalized to repository-relative markdown targets, removing local absolute filesystem paths from the review record.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074827084 -> ee85df1b0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074827088 -> ee85df1b0

Disposition: FIXED
Commit: 0769efdf6
Evidence: [tests/test_main_paywall_bootstrap.py](../../tests/test_main_paywall_bootstrap.py#L44)
Reason: The bootstrap helper test now restores `app_main.app` after exercising temporary `FastAPI` instances, preventing module-singleton contamination across later tests.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3075310789 -> 0769efdf6

Disposition: FIXED
Commit: 9cdc3fda0
Evidence: [app/routers/paywall_analytics.py](../../app/routers/paywall_analytics.py#L49), [tests/test_paywall_exposure_ledger_api.py](../../tests/test_paywall_exposure_ledger_api.py#L136), [tests/test_main_paywall_bootstrap.py](../../tests/test_main_paywall_bootstrap.py#L9)
Reason: Late CodeRabbit follow-ups were closed with a post-comment hardening pass: the optional auth resolver now swallows only expected `HTTPException` auth rejections, unexpected resolver failures propagate to keep bugs visible, and the bootstrap tests restore the module singleton automatically between cases.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3075318765 -> 9cdc3fda0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3075318772 -> 9cdc3fda0

Disposition: FIXED
Commit: d17162bcc
Evidence: [tests/test_main_paywall_bootstrap.py](../../tests/test_main_paywall_bootstrap.py#L1), [tests/test_paywall_exposure_ledger_api.py](../../tests/test_paywall_exposure_ledger_api.py#L336)
Reason: The remaining open CodeRabbit follow-ups are now closed: the autouse yield fixture is typed as `Generator[None, None, None]`, the primary cookie-auth exchange path uses `pro_headers`, and a separate VIP compatibility test preserves the earlier coverage without overloading the main PRO happy path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3075520368 -> d17162bcc
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3075520378 -> d17162bcc

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1416_FIXED_MAPPING.md:8`, `docs/review/PR_1416_FIXED_MAPPING.md:16`, `docs/review/PR_1416_FIXED_MAPPING.md:29`, `docs/review/PR_1416_FIXED_MAPPING.md:70`
Reason: These review-level bot comments are aggregate summaries of inline findings that are already dispositioned individually in this artifact. They do not add separate unfixed obligations beyond the mapped `discussion_r...` entries above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4100747870
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4100802453
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4100803334
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4100826139
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4101369074
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4101378274
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4101602245

Disposition: FIXED
Commit: 3fca652fe
Evidence: [docs/roadmap/BACKLOG_LEDGER.md](../../docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-pillow-private-index-sync)
Reason: The Pillow mirror-lag cleanup item now targets a follow-up PR instead of this same PR, so the ledger no longer points the temporary fallback removal back at the change set that introduced it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3076006585 -> 3fca652fe

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1416_FIXED_MAPPING.md:82`, `docs/review/PR_1416_FIXED_MAPPING.md:92`
Reason: The latest Cubic review body is an aggregate wrapper for the single inline backlog-target finding that is already mapped immediately above and does not create a second independent obligation.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4102141160

Disposition: FIXED
Commit: 826ce2b3a
Evidence: [frontend/src/lib/analytics.ts](../../frontend/src/lib/analytics.ts#L8), [frontend/src/api/client.ts](../../frontend/src/api/client.ts#L181), [frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx](../../frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx#L95)
Reason: The remaining Sourcery inline follow-ups are now closed: the client ingestion contract is typed to client-authored paywall events only, legacy paywall analytics calls use a stricter event union, and the Pro paywall tests now cover the successful purchase path with stable exposure-id sequencing.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3076280427 -> 826ce2b3a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3076280434 -> 826ce2b3a

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1416_FIXED_MAPPING.md:91`, `frontend/src/lib/analytics.ts:8`, `frontend/src/api/client.ts:181`, `frontend/src/pages/Pro/__tests__/ProPaywallPage.test.tsx:95`
Reason: The latest Sourcery review body is an aggregate wrapper for the two inline comments mapped immediately above. Its extra note about centralizing `auth_source` / `tier_snapshot` typing is high-level follow-up advice rather than a separate correctness defect required to merge this PR.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#pullrequestreview-4102440298

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green

Notes: `db3446f6e` passed targeted pytest, changed-file pre-commit, and accelerated changed-line diff-cover (`98%`). Full `make verify` / CI current-head status must be re-checked on the final merge cycle before any merge claim.
