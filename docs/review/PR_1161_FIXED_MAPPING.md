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

Disposition: FIXED
Commit: eb540717
Evidence: tests/test_app_missing_lines_extra.py:166, tests/test_bmi_pro_router.py:206, tests/test_enhanced_plate_api.py:305, tests/test_foods_router_additional.py:176
Reason: The error-path tests now assert JSON Content-Type before parsing response bodies, and the foods router regression uses the shared module-level constant instead of a duplicated literal.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#discussion_r2934055735 -> eb540717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#discussion_r2934055738 -> eb540717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#discussion_r2934055742 -> eb540717
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#discussion_r2934055746 -> eb540717

Disposition: FIXED
Commit: e3dc7abb
Evidence: tests/test_pro_restaurant_partner_api.py:169, tests/test_pro_restaurant_partner_api.py:202, tests/test_pro_restaurant_partner_api.py:484, tests/test_pro_restaurant_partner_api.py:681, tests/test_pro_restaurant_partner_api.py:714
Reason: The previously direct router-call regressions for the partner order and handoff-share error paths now exercise the live HTTP endpoints via `TestClient`, asserting JSON content type and the sanitized response envelope exactly as requested by the review.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#discussion_r2934055750 -> e3dc7abb

Disposition: FIXED
Commit: a67c1a7b
Evidence: tests/test_subscription_activation_api.py:710, tests/test_subscription_activation_api.py:727
Reason: The review-level CodeRabbit follow-up is now fully addressed by post-comment code commits: the partner-order sanitization cases were moved onto live `TestClient` coverage, the BMI route uses `status.HTTP_400_BAD_REQUEST`, and the missing-transport activation regression now also asserts that the sanitized detail omits leaking auth/header internals.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#pullrequestreview-3947270364 -> a67c1a7b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1161#pullrequestreview-3947357781 -> a67c1a7b

## Merge Readiness
- [x] Local hard gate passed (`make verify` equivalent via canonical split gates: lint + typecheck + test-fast + diff-cov)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
