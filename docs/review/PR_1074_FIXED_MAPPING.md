# PR 1074 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: Sourcery review `#pullrequestreview-3921812301`
Reason: The Sourcery comment is a weekly diff-character rate-limit notice, not implementation feedback or an actionable defect.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#pullrequestreview-3921812301

Disposition: FIXED
Commit: c19e05ad
Evidence: `docker-compose.yaml:57`, `docs/contracts/API_CANONICAL_MAP.md:20`, `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#pullrequestreview-3921836587 -> c19e05ad
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911237504 -> c19e05ad
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911237507 -> c19e05ad
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911237519 -> c19e05ad

Disposition: FIXED
Commit: 4a0a0041
Evidence: `app/routers/billing.py:116`, `app/services/payments_activation.py:226`, `app/services/payments_activation.py:296`, `docs/contracts/API_CANONICAL_MAP.md:15`, `docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md:27`, `docs/roadmap/BACKLOG_LEDGER.md:80`, `tests/conftest.py:602`, `tests/test_apple_receipt_verify_service_helpers.py:130`, `tests/test_ios_receipt_verification_api.py:13`, `tests/test_pro_payments_api.py:330`, `tests/test_payment_reconciliation_api.py:53`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#pullrequestreview-3921893497 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285640 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285642 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285650 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285655 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285659 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285682 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285687 -> 4a0a0041
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285690 -> 4a0a0041

Disposition: FIXED
Commit: 661cfe9c
Evidence: `docs/review/PR_1074_FIXED_MAPPING.md:3`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#discussion_r2911285670 -> 661cfe9c

Disposition: FIXED
Commit: 65e0290a
Evidence: `app/routers/billing.py:168`, `docs/contracts/API_CANONICAL_MAP.md:16`, `docs/roadmap/BACKLOG_LEDGER.md:64`, `docs/roadmap/BACKLOG_LEDGER.md:156`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#pullrequestreview-3922339679 -> 65e0290a

Disposition: FIXED
Commit: 29df8752
Evidence: `docs/roadmap/BACKLOG_LEDGER.md:321`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1074#pullrequestreview-3922347821 -> 29df8752

## Merge Readiness
- [ ] All required checks are green on latest commit (no pending/rerun required)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Wait-window completed after latest bot/review activity (do not merge on first green tick)
