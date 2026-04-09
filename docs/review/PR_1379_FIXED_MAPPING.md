# PR #1379 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned here before they are resolved on GitHub.

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4081266106 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056866537 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056866544 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888554 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888560 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888564 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888572 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888581 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888585 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888592 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056893790 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056893792 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4081311870 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910860 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910868 -> e85ca81d59cb2336913e83f48513f9627c03652b
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056910886 -> e85ca81d59cb2336913e83f48513f9627c03652b
Disposition: FIXED
Commit: e85ca81d59cb2336913e83f48513f9627c03652b
Evidence: `llm.py` (insight-only fallback chain, timeout floor, isolated fallback builders, provider type hint, Ollama fallback warning/docstring contract); `core/insight/llm_provider_loader.py` (insight path uses `get_insight_provider()`); `app/services/insight_runtime.py` (fallback winner propagated into tracing/provider identity); `legacy_app.py` (`/ready` fail-soft runtime enrichment); `tests/_client.py`, `tests/conftest.py`, `tests/test_llm_extras.py`, `tests/test_app_insight_runtime.py`, `tests/test_api.py`, `tests/test_health_db.py`, `tests/test_insight_error_hygiene.py`, `tests/test_insight_rag_response_fields.py`, `tests/test_philosophy_validation_integration.py`, `tests/test_rag_vector_feature_flag_guard.py`. Latest recovery head `4546ab11f` preserved this contract after merge-through with `origin/main`; local gates are green via `pre-commit run --all-files` and `make verify` on `4546ab11f`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3056888533 -> 62738b566
Disposition: FIXED
Commit: 62738b566
Evidence: `docs/review/PR_1379_FIXED_MAPPING.md` merge-readiness and discussion-pass checkboxes were reset to in-progress state in commit `62738b566`, so the artifact no longer claims readiness before current-head CI and GitHub thread resolution complete.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3057599929 -> 4546ab11f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3057599934 -> 4546ab11f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3057611916 -> 4546ab11f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4082052885 -> 4546ab11f
Disposition: FIXED
Commit: 4546ab11f
Evidence: merge-through recovery aligned `#1379` with the current approved security/dependency baseline already present on `origin/main`; obsolete branch-local seam docs were removed and the active evidence now lives in `docs/security/CRYPTOGRAPHY_46_0_7_PRIVATE_INDEX_ADVISORY.md:1`, `docs/roadmap/BACKLOG_LEDGER.md:338`, `scripts/ci/emergency_python_wheels.json:1`, `.github/actions/python-setup/action.yml:55`, and `Dockerfile:248`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4083032445 -> 4546ab11f
Disposition: FIXED
Commit: 4546ab11f
Evidence: CodeRabbit nitpicks were fixed on the recovery head: `app/services/insight_runtime.py` now emits `gen_ai.provider.name` on every call, `llm.py` logs the Ollama constructor fallback warning and documents the dynamic fallback attribute contract, and the closure-based rate-limiter patching was extracted into `tests/_client.py` and reused from `tests/test_insight_rag_response_fields.py`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4083076599 -> 4546ab11f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3058530222 -> 4546ab11f
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3058530227 -> 4546ab11f
Disposition: FIXED
Commit: 4546ab11f
Evidence: cubic found two test-hygiene issues on the updated head, both fixed in `4546ab11f`: `tests/test_api.py` now uses `monkeypatch.setattr(llm, "get_insight_provider", ...)` instead of `@patch`, and `tests/conftest.py` now honors lazy `app.__getattr__` exports by falling back to `getattr(module, attr_name, None)` after `vars(module).get(...)`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4085380632 -> 1a9f2299c
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#discussion_r3060628115 -> 1a9f2299c
Disposition: FIXED
Commit: 1a9f2299c
Evidence: latest CodeRabbit round is closed on `1a9f2299c`: `tests/test_api.py` removes the remaining `unittest.mock.patch` import and rewrites `test_compute_wht_ratio_round_exception` to use `monkeypatch.setattr(core.bmi.engine, "round", ...)`; `tests/test_insight_rag_response_fields.py` removes redundant manual `_disable_vip_monthly_quota(...)` / `_ensure_rate_limiting_disabled(...)` calls because the module autouse fixture already applies both seams for every test.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4081288984
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1379#pullrequestreview-4082066018
Disposition: NOT-A-BUG
Evidence: thread-level actionable comments from these aggregate bot reviews are mapped separately above; the remaining summary-level rollups do not introduce additional unresolved defects on current head beyond the already-dispositioned inline items.
Reason: aggregate review summaries are advisory once their concrete inline comments are mapped, and the current branch head preserves the approved A1 runtime contract without widening `#1379` beyond insight fallback/readiness scope.

## Current-Head Follow-up

Disposition: FIXED
Commit: 775c863f4
Evidence: `tests/test_llm_extras.py` now covers the current-head `diff-coverage` tail reported by GitHub job `70690704857` for `llm.py` (`_parse_ollama_timeout` invalid-value fallback, double-failure Ollama ctor path, Perplexity lite fallback branches, and direct `get_provider` / `get_insight_provider` dispatch branches). Focused local `diff-cover` against `origin/main` passes at `97%` with `legacy_app.py` and `llm.py` both at `100%` diff coverage.

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green on latest pushed head
- [ ] `make verify` green on latest pushed head
