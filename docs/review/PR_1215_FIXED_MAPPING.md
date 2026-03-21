# PR 1215 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: NOT-A-BUG
Evidence: The Sourcery wrapper `#pullrequestreview-3986206239` only aggregates inline issues that are all fixed on the current head: execution-mode handling is now bound before the permission gate in `app/routers/fitchef_structured.py:53`, fenced JSON extraction no longer strips arbitrary backticks in `core/insight/fitchef_companion.py:543`, and 429 response wiring is canonicalized through `RATE_LIMIT_429_RESPONSES` in `app/routers/fitchef_structured.py:77`.
Reason: No standalone defect remains beyond the concrete inline review threads mapped below.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#pullrequestreview-3986206239

Disposition: FIXED
Commit: 78f8ab97
Evidence: `app/services/fitchef_runtime.py:78`, `app/services/fitchef_runtime.py:602`, `app/services/fitchef_runtime.py:640`, `app/services/fitchef_runtime.py:711`, `app/services/fitchef_runtime.py:824`, `app/services/fitchef_runtime.py:912`, `tests/test_fitchef_structured_api.py:298`, `tests/test_fitchef_structured_api.py:594`, `tests/test_fitchef_structured_api.py:726`, `tests/test_cbt_insight_api.py:814`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969777424 -> 78f8ab97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969777425 -> 78f8ab97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969778020 -> 78f8ab97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969778022 -> 78f8ab97

Disposition: FIXED
Commit: 78f8ab97
Evidence: `tests/test_fitchef_structured_api.py:60`, `tests/test_fitchef_structured_api.py:337`, `tests/test_rate_limit_llm_and_exports_api.py:216`, `app/routers/fitchef_structured.py:37`, `frontend/src/api/openapi.json:7308`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969777530 -> 78f8ab97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969778024 -> 78f8ab97
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#discussion_r2969778031 -> 78f8ab97

Disposition: NOT-A-BUG
Evidence: The cubic wrapper `#pullrequestreview-3986210339` only aggregates the local `TestClient(app)` isolation issue that is fixed on the current head in `tests/test_fitchef_structured_api.py:60`.
Reason: No standalone defect remains once the inline thread is dispositioned.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#pullrequestreview-3986210339

Disposition: NOT-A-BUG
Evidence: The CodeRabbit wrapper `#pullrequestreview-3986210725` only aggregates inline issues now fixed on the current head: fail-closed provider/quota ordering in `app/services/fitchef_runtime.py:640`, missing transparency fallback removal in `app/services/fitchef_runtime.py:602`, OpenAPI/assertion/test fixture cleanup in `tests/test_fitchef_structured_api.py:337` and `tests/test_rate_limit_llm_and_exports_api.py:216`, plus generated contract tags in `frontend/src/api/openapi.json:7308`.
Reason: No standalone defect remains once the mapped inline threads are fixed.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1215#pullrequestreview-3986210725

## Merge Readiness
- [ ] All required checks are green on latest commit (no pending/rerun required)
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Wait-window completed after latest bot/review activity (do not merge on first green tick)
