# PR 1093 - Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914961536 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: app/telemetry/genai.py:118; app/telemetry/genai.py:205; tests/test_genai_tracing.py:168
Reason: fingerprint and event helpers now no-op when tracing is enabled without `PULSE_OBS_HMAC_KEY`, so request paths degrade safely instead of crashing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981102 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: .env.example:46
Reason: `.env.example` now documents the full tracing enablement contract, including the `PULSE_OBS_HMAC_KEY` precondition.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981105 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: app/services/insight_runtime.py:98; core/insight/philosophical_runtime.py:332; legacy_app.py:2306
Reason: tracing moved to an app-layer adapter; `core/insight/philosophical_runtime.py` no longer imports app telemetry helpers or accepts `trace_*` parameters.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981110 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: docs/compliance/PROVIDER_INVENTORY.md:12
Reason: provider inventory wording now matches the privacy/legal contract and includes bounded usage metadata.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981118 -> e3620198
Disposition: FIXED
Commit: e3620198
Evidence: docs/review/PR_1093_FIXED_MAPPING.md:7; docs/review/PR_1093_FIXED_MAPPING.md:98; docs/review/PR_1093_FIXED_MAPPING.md:107
Reason: the blanket `No actionable review comments` line was removed and replaced with concrete dispositions plus an explicit merge-readiness checklist.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981122 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: app/services/insight_runtime.py:142; legacy_app.py:2306
Reason: `legacy_app.py` no longer opens `chain_span(...)`; the insight chain span now lives in an app-layer helper and legacy remains a thin delegator.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981125 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: legacy_app.py:2388
Reason: the legacy `/insight` path now tags tracing with `user_tier=\"VIP\"`, matching the route guard.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981488 -> e52acb85
Disposition: FIXED
Commit: e52acb85
Evidence: legacy_app.py:2388
Reason: cubic identified this duplicate VIP-tier misclassification; the traced tier now matches `require_vip_tier`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#pullrequestreview-3925961437
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914961536; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981102; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981105; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981110; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981122; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981125
Reason: this CodeRabbit review entry is a summary shell for the actionable child threads dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#pullrequestreview-3925961804
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2914981488
Reason: cubic identified this issue in the summary shell; the exact actionable child thread is dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174836 -> fcdde198
Disposition: FIXED
Commit: fcdde198
Evidence: tests/test_genai_tracing.py:238; tests/test_genai_tracing.py:253
Reason: the middleware error-path test now raises `RuntimeError`, so it exercises tracing exception finalization instead of FastAPI's handled `HTTPException` response path.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174839 -> fcdde198
Disposition: FIXED
Commit: fcdde198
Evidence: core/insight/philosophical_runtime.py:103
Reason: the injected retriever hook now uses `RAGOrchestrationResult` instead of `Any`, preserving core-layer static typing.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174845 -> fcdde198
Disposition: FIXED
Commit: fcdde198
Evidence: docs/legal/Privacy.md:208
Reason: the Spanish privacy section now includes the external-provider retention/disclosure sentence already present in the RU and EN sections.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174850 -> 6f2e447a
Disposition: FIXED
Commit: 6f2e447a
Evidence: docs/review/PR_1093_FIXED_MAPPING.md:28; docs/review/PR_1093_FIXED_MAPPING.md:30
Reason: the earlier mapping entry for `discussion_r2914981118` now cites the actual checklist anchors instead of stale line references.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915185255 -> fcdde198
Disposition: FIXED
Commit: fcdde198
Evidence: app/telemetry/genai.py:295; tests/test_genai_tracing.py:259
Reason: `request_span()` now binds and restores `pulseplate.request.id` context so nested spans inherit the same request correlation id.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915185258 -> 6f2e447a
Disposition: FIXED
Commit: 6f2e447a
Evidence: docs/review/PR_1093_FIXED_MAPPING.md:98; docs/review/PR_1093_FIXED_MAPPING.md:101
Reason: the merge-readiness checklist stays unchecked until the actual final merge cycle, matching repository governance.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#pullrequestreview-3926167880
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174836; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174839; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174845; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915174850
Reason: this cubic review entry is a summary shell; each actionable child thread is dispositioned individually above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#pullrequestreview-3926179096
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915185255; https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915185258
Reason: this CodeRabbit review entry is a summary shell for the child comments dispositioned above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915859928 -> 31ef7c86
Disposition: FIXED
Commit: 31ef7c86
Evidence: app/telemetry/genai.py:195; app/telemetry/genai.py:204; app/telemetry/genai.py:213; app/telemetry/genai.py:248; app/telemetry/genai.py:269; tests/test_genai_tracing.py:217
Reason: post-start span mutations now use best-effort wrappers for `set_attribute` and `add_event`, and the regression test proves a raising backend no longer breaks execution.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#pullrequestreview-3926888311
Disposition: NOT-A-BUG
Evidence: https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1093#discussion_r2915859928
Reason: this CodeRabbit review entry is a summary shell for the actionable child thread dispositioned immediately above.

## Merge Readiness
- [ ] Scope tied to PR objective
- [ ] Docs/runtime changes applied
- [ ] Verification completed
- [ ] Required GitHub checks PASS with no pending required jobs
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] No unresolved review threads or actionable bot comments remain
- [ ] Review wait-window completed

Current state note: fresh bot comments from 2026-03-11 are dispositioned in this follow-up. Final readiness still waits for a clean post-push GitHub sweep, zero unresolved threads, and the mandatory final wait-window.
