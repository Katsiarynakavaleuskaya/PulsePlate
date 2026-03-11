# PR 1122 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: ac870e54
Evidence: `tests/test_websocket_security_api.py:607`, `tests/test_websocket_security_api.py:608`, `tests/test_websocket_security_api.py:620` keep `_assert_no_duplicate_ws_route` bound to the runtime-resolved `app.main` module, so the patched `main_mod.app` and the asserted guard function stay synchronized in purge/reload-sensitive flows.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1122#discussion_r2920875349 -> ac870e54
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1122#discussion_r2920896727 -> ac870e54

## Merge Readiness
- [x] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
