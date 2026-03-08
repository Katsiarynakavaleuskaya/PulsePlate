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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#pullrequestreview-3912009316 -> de3c9a6a
  Disposition: FIXED
  Evidence: app/routers/cbt_insight.py:349; core/server_salt.py:14; tests/test_cbt_insight_api.py:929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#pullrequestreview-3912010619 -> de3c9a6a
  Disposition: FIXED
  Evidence: app/routers/legal.py:94; app/main.py:80; tests/test_app_endpoints_1383_1401.py:74; tests/test_compliance_control_plane.py:22
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#pullrequestreview-3912061363 -> 649a2fb6
  Disposition: FIXED
  Evidence: core/server_salt.py:11; legacy_app.py:2140; tests/test_llm_monthly_quota_config_validation.py:23; tests/test_insight_error_hygiene.py:185
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
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361410 -> de3c9a6a
  Disposition: FIXED
  Evidence: app/routers/legal.py:94; app/main.py:80
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361412 -> 1d983225
  Disposition: FIXED
  Evidence: tests/test_app_endpoints_1383_1401.py:133
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361599 -> 1d983225
  Disposition: FIXED
  Evidence: app/routers/feedback.py:56; tests/test_feedback_api.py:246
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902361604 -> 1d983225
  Disposition: FIXED
  Evidence: app/security/agent_control_plane.py:280; core/compliance/minimization.py:176
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902400352 -> de3c9a6a
  Disposition: FIXED
  Evidence: app/routers/cbt_insight.py:349; tests/test_cbt_insight_api.py:929
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902400354 -> de3c9a6a
  Disposition: FIXED
  Evidence: core/server_salt.py:14; core/compliance/minimization.py:134; app/security/server_salt.py:1
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902402282 -> de3c9a6a
  Disposition: FIXED
  Evidence: tests/test_compliance_control_plane.py:31; tests/test_compliance_control_plane.py:50; tests/test_compliance_control_plane.py:119
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902461471 -> 649a2fb6
  Disposition: FIXED
  Evidence: core/server_salt.py:11; tests/test_llm_monthly_quota_config_validation.py:31; tests/conftest.py:145
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1046#discussion_r2902461473 -> 649a2fb6
  Disposition: FIXED
  Evidence: legacy_app.py:2140; legacy_app.py:2303; legacy_app.py:2324; tests/test_insight_error_hygiene.py:185

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
