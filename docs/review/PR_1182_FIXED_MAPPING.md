# PR 1182 — B1 Payments RU/BY + iOS Baseline — Fixed in Commit Mapping

**PR:** 1182
**Branch:** feat/p0-payments-ruby-ios-baseline-runtime-w1

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#issuecomment-4072707735 -> 92165e82
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#pullrequestreview-3958635283 -> 92165e82
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#pullrequestreview-3958646178 -> 92165e82
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#discussion_r2944833945 -> 92165e82
Commit: 92165e82
Evidence: app/services/payments_activation.py; tests/test_payment_webhook_signature_api.py; docs/contracts/PAYMENTS_RU_BY_IOS_BASELINE.md
Reason: webhook signature contract hardened (no strip, hex case-insensitive, fail-closed malformed).

Disposition: NOT-A-BUG
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#issuecomment-4072707284
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#discussion_r2944837422
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1182#pullrequestreview-3958649530
Evidence: docs/review/PR_1182_FIXED_MAPPING.md
Reason: merge-readiness checkboxes already unchecked on current HEAD; no actionable code change requested.

## Merge Readiness

- [x] `make verify` green
- [x] `pre-commit run --all-files` green
- [x] No actionable bot comments
