# PR 1161 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 89ba21b1
Evidence: app/http_error_details.py:1, tests/test_pro_restaurant_partner_api.py:10, tests/test_subscription_activation_api.py:14
Reason: Sanitized client-facing error details are now centralized in a shared canonical module, and the touched regression tests assert against imported contract constants instead of duplicated string literals.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#pullrequestreview-3947251638 -> 89ba21b1

## Merge Readiness
- [x] Local hard gate passed (`make verify` equivalent via canonical split gates: lint + typecheck + test-fast + diff-cov)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
