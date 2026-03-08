# PR 1046 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#pullrequestreview-3911967929 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/minimization.py:133; core/compliance/transparency.py:101; app/routers/feedback.py:63; docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md:53
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#pullrequestreview-3911971493 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/privacy.py:110; app/routers/legal.py:1; tests/test_app_endpoints_1383_1401.py:133; docs/roadmap/BACKLOG_LEDGER.md:79
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902358121 -> 1d983225
  Disposition: FIXED
  Evidence: app/security/agent_control_plane.py:280; core/compliance/minimization.py:176
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902358124 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/minimization.py:133; tests/test_feedback_api.py:258
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902358127 -> 1d983225
  Disposition: FIXED
  Evidence: docs/compliance/AI_TRANSPARENCY_AND_PROFILING_NOTICE.md:53
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902358131 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/transparency.py:101; tests/test_compliance_control_plane.py:112
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902358132 -> 1d983225
  Disposition: FIXED
  Evidence: app/routers/feedback.py:63; tests/test_feedback_api.py:246
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361384 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/privacy.py:110; tests/test_compliance_control_plane.py:30
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361390 -> 1d983225
  Disposition: FIXED
  Evidence: core/compliance/transparency.py:101; tests/test_compliance_control_plane.py:112
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361393
  Disposition: NOT-A-BUG
  Evidence: tests/guards/test_wellness_language_blockers_guard.py:33
  Reason: The guard blocks narrow cure/diagnose phrasing, not the legal/policy noun phrases used in this doc; the file passes the current blocker guard without an in-file marker.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361398
  Disposition: NOT-A-BUG
  Evidence: tests/guards/test_wellness_language_blockers_guard.py:33
  Reason: The RFC text uses policy/regulatory framing that is outside the current blocker patterns; an allow-marker is not required for the guard contract now.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361402
  Disposition: NOT-A-BUG
  Evidence: tests/guards/test_wellness_language_blockers_guard.py:33
  Reason: The legal privacy document does not contain the narrow blocked cure/diagnose claims; the guard contract already permits this wording without an explicit marker.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361404 -> 1d983225
  Disposition: FIXED
  Evidence: docs/review/PR_1046_FIXED_MAPPING.md:3
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361406 -> 1d983225
  Disposition: FIXED
  Evidence: docs/roadmap/BACKLOG_LEDGER.md:79
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361410 -> 1d983225
  Disposition: FIXED
  Evidence: app/routers/legal.py:1; legacy_app.py:1714
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361412 -> 1d983225
  Disposition: FIXED
  Evidence: tests/test_app_endpoints_1383_1401.py:133
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361599 -> 1d983225
  Disposition: FIXED
  Evidence: app/routers/feedback.py:56; tests/test_feedback_api.py:246
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361604 -> 1d983225
  Disposition: FIXED
  Evidence: app/security/agent_control_plane.py:280; core/compliance/minimization.py:176

## Merge Readiness
- [x] Scope tied to PR objective
- [x] Docs/runtime changes applied
- [x] Verification completed
- [ ] Required GitHub checks PASS with no pending required jobs
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] No unresolved review threads or actionable bot comments remain
- [ ] Review wait-window completed
