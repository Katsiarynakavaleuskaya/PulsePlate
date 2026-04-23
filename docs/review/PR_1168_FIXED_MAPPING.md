# PR 1168 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 89283dd44f43f5f377ee60299b16bbe3ac9b2673
Evidence: `tests/test_app_lifespan_additional.py:165` adds the positive production startup case with explicit `ALLOW_DEV_API_KEY=false` and `ALLOW_ANONYMOUS_API_KEYS=false`, while `tests/test_app_lifespan_additional.py:184` proves `app.lifespan(...)` now succeeds when `PRO_LLM_INSIGHT_REQUESTS_PER_MONTH` is a valid integer instead of only checking the fail path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948673639 -> 89283dd44f43f5f377ee60299b16bbe3ac9b2673
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935133225 -> 89283dd44f43f5f377ee60299b16bbe3ac9b2673

Disposition: FIXED
Commit: a1e09f2831ce9b2a4d2198d11e1555a02ac9349a
Evidence: `tests/test_payment_source_contract_api.py:46` now patches `app.get_api_key` without `raising=False`, so the transport-auth regression test will fail loudly if the expected symbol disappears instead of silently creating it.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948679729 -> a1e09f2831ce9b2a4d2198d11e1555a02ac9349a
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935137722 -> a1e09f2831ce9b2a4d2198d11e1555a02ac9349a

Disposition: FIXED
Commit: 2a81288bb00eb6f3ae8a2a121499b133e91851ce
Evidence: `app/routers/billing.py:261` restores `require_pro_tier` on `manual-intent` so the same principal can still reach the reconcile/status endpoints, `tests/test_payment_source_contract_api.py:38` drops the invalid non-PRO transport-key acceptance case, and `frontend/src/lib/auth.tsx:115` plus `frontend/src/lib/usePremium.ts:20` now broadcast/listen for a same-document premium-session change event backed by `frontend/src/lib/premiumEvents.ts:1`, with `frontend/src/lib/__tests__/usePremium.test.ts:73` proving the hook revalidates after session transitions.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948687473 -> 2a81288bb00eb6f3ae8a2a121499b133e91851ce
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935143201 -> 2a81288bb00eb6f3ae8a2a121499b133e91851ce
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935143203 -> 2a81288bb00eb6f3ae8a2a121499b133e91851ce

Disposition: NOT-A-BUG
Evidence: `app/routers/billing.py:259` keeps `/ru-by/manual-intent` on `require_pro_tier`, while `app/routers/billing.py:305` and `app/routers/billing.py:361` keep reconcile and status on the same principal guard, so restoring `_require_billing_transport_key` at intent creation would recreate orphaned intents instead of opening a safe purchase path.
Reason: The later Cubic review asks to undo the earlier reconcile-alignment fix, but the current route contract is intentionally fail-closed and consistent across intent creation, reconciliation, and status lookup.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948706164
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935157992

Disposition: FIXED
Commit: 1b4cecbf54f2023292e4d85eb7a5b60bc843a718
Evidence: `tests/test_payment_source_contract_api.py:13` and `tests/test_payment_source_contract_api.py:27` now cover both `_require_billing_transport_key` fallback outcomes, proving the helper accepts a valid PRO fallback and returns 401 when tier auth is absent; local `make verify` now reports `app/routers/billing.py (100%)` diff coverage again.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935158366 -> 1b4cecbf54f2023292e4d85eb7a5b60bc843a718

Disposition: NOT-A-BUG
Evidence: `frontend/src/lib/usePremium.ts:21` already listens for `PREMIUM_CHANGE_EVENT`, and `frontend/src/lib/__tests__/usePremium.test.ts:83` proves same-document session changes trigger a second server revalidation for the hook.
Reason: This CodeRabbit thread arrived after the premium-refresh fix was already present in the branch, so the current code already satisfies the requested behavior without another production change.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935158367

Disposition: FIXED
Commit: 1b4cecbf54f2023292e4d85eb7a5b60bc843a718
Evidence: `frontend/src/pages/NutritionSetup/SetupForm.tsx:14` now preserves parsed numeric values instead of truncating them, and `frontend/src/pages/NutritionSetup/__tests__/SetupForm.test.tsx:44` proves fractional age input is rejected instead of silently coercing `30,9` to `30`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935158368 -> 1b4cecbf54f2023292e4d85eb7a5b60bc843a718

Disposition: NOT-A-BUG
Evidence: `tests/test_payment_source_contract_api.py:13` now starts with direct helper coverage tests, and the file no longer contains `test_manual_intent_accepts_transport_validated_non_pro_key`, so there is no remaining direct `_APP_MODULE = None` mutation in the current test surface.
Reason: The cleanup concern referenced a test that has already been removed from the branch, so no further mutation rollback is needed in the current code.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935158369

Disposition: NOT-A-BUG
Evidence: The actionable inline comments from this CodeRabbit review are dispositioned individually in this artifact (`discussion_r2935158366`, `discussion_r2935158367`, `discussion_r2935158368`, `discussion_r2935158369`), and the remaining review summary suggestions are non-blocking refactors outside this readiness-blocker lane.
Reason: The review-level summary does not introduce an additional unresolved contract gap beyond the inline findings already addressed or dispositioned above.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948706805

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
