<!-- markdownlint-disable MD034 -->
# PR 1442 — Fixed in Commit Mapping

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot review threads and review-level summaries for this PR are dispositioned here
before any GitHub thread is resolved.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1442#discussion_r3102729968 -> d99fc7f442651944e0455fe624d22a527426376f
Disposition: FIXED
Commit: d99fc7f442651944e0455fe624d22a527426376f
Evidence: `app/routers/pro_payments.py:71-85` now strips the transport key once, validates issued `PRO/VIP` transport keys without consulting DB entitlement truth, and reuses the normalized key for `derive_subject_id_from_api_key(...)`; `tests/test_subscription_activation_api.py:543-552` and `tests/test_subscription_activation_api.py:1179-1198` cover invalid-key rejection with deterministic 403 responses.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1442#pullrequestreview-4131498817 -> d99fc7f442651944e0455fe624d22a527426376f
Disposition: FIXED
Commit: d99fc7f442651944e0455fe624d22a527426376f
Evidence: The Sourcery review-level summary is satisfied by the same trim-once transport-auth fix documented above in `app/routers/pro_payments.py:71-85`, plus the focused regression coverage in `tests/test_subscription_activation_api.py:543-552` and `tests/test_subscription_activation_api.py:1179-1198`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1442#pullrequestreview-4131507837 -> d99fc7f442651944e0455fe624d22a527426376f
Disposition: FIXED
Commit: d99fc7f442651944e0455fe624d22a527426376f
Evidence: `app/routers/pro_payments.py:55-64` now centralizes the forbidden activation envelope via `_activation_forbidden_response(...)`, and both handler branches call that helper at `app/routers/pro_payments.py:145` and `app/routers/pro_payments.py:198`, eliminating the drift risk raised by CodeRabbit.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1442#pullrequestreview-4131529120
Disposition: NOT-A-BUG
Reason: cubic found no issues in the reviewed files, so this review summary does not request any follow-up code or documentation change.
Evidence: The review body explicitly states "No issues found across 4 files" and therefore contributes no unresolved actionable item for this PR.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head
<!-- markdownlint-enable MD034 -->
