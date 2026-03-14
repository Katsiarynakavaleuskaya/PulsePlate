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

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
