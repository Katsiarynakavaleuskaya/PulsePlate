# PR 1416 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: see mapping entries below
Evidence: [tests/test_payments_activation_paywall_events.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/tests/test_payments_activation_paywall_events.py:63), [frontend/src/lib/analytics.ts](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/frontend/src/lib/analytics.ts:24)
Reason: Sourcery follow-ups for deterministic activation lineage assertions and memoized hidden-ingestion import were fixed in earlier review passes.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074758628 -> bba685ea0
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074758638 -> 055c113b5

Disposition: FIXED
Commit: see mapping entries below
Evidence: [app/schemas/paywall_analytics.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/app/schemas/paywall_analytics.py:39), [app/routers/paywall_analytics.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/app/routers/paywall_analytics.py:35), [app/main.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/app/main.py:205), [app/services/paywall_exposure_ledger.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/app/services/paywall_exposure_ledger.py:143), [tests/test_paywall_exposure_ledger_api.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/tests/test_paywall_exposure_ledger_api.py:74), [tests/test_paywall_exposure_ledger_service.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/tests/test_paywall_exposure_ledger_service.py:93), [tests/test_main_paywall_bootstrap.py](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/tests/test_main_paywall_bootstrap.py:43)
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
Evidence: [docs/review/PR_1416_FIXED_MAPPING.md](/Users/katsiaryna_kavaleuskaya/Developer/BMI-App_2025_clean/worktrees/feat-paywall-exposure-ledger/docs/review/PR_1416_FIXED_MAPPING.md:1)
Reason: Merge-readiness checkboxes were reset to unchecked and the artifact now uses thread-specific mapping evidence instead of the earlier ambiguous review-level references.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1416#discussion_r3074806376

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (re-check on current head before merge)
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
- [ ] `make verify` green

Notes: `db3446f6e` passed targeted pytest, changed-file pre-commit, and accelerated changed-line diff-cover (`98%`). Full `make verify` / CI current-head status must be re-checked on the final merge cycle before any merge claim.
