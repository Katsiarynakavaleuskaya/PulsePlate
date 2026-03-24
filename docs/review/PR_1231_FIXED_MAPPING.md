## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 81b79450
Evidence: `llm.py`, `.env.example`, `tests/test_llm_comprehensive.py`, `tests/test_llm_extras.py`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981662350
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981696506
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981723514
Disposition: FIXED
Commit: 64244290
Evidence: `scripts/validate-ci-environment.sh` (supported provider messages aligned with runtime)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981723508
Disposition: FIXED
Commit: 64244290
Evidence: `tests/test_llm_extras.py` (`_PerplexityProvider` keyword-only init + strict instance/field assertions)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981733299
Disposition: FIXED
Commit: 64244290
Evidence: `tests/test_llm.py` (remove ImportError-swallow fallback; import `get_provider` directly)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981733314
Disposition: FIXED
Commit: 64244290
Evidence: `tests/test_llm.py` (switch env mutation to `monkeypatch` for deterministic isolation)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981733319
Disposition: FIXED
Commit: 307adf04
Evidence: `tests/test_llm_extras.py` (`test_get_provider_ollama_typeerror_posargs_fallback` now asserts constructor path via type and env-bound fields)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981825324
Disposition: FIXED
Commit: 307adf04
Evidence: `tests/test_llm.py` (add `pytest.MonkeyPatch` annotations and `-> None` return types for modified test functions)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981825340
Disposition: NOT-A-BUG
Evidence: `tests/test_llm_comprehensive.py` (`TestPerplexityLiteProvider.test_grok_lite_provider_through_exception`) intentionally validates provider-unavailable fallback path by setting `PerplexityProvider=None`; this is distinct from API-key guard coverage, which is already covered in `tests/test_llm_extras.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981723500
Disposition: FIXED
Commit: 06fcd766
Evidence: `docker-compose.yaml` (`pulseplate` + `pulseplate-dev` now export `LLM_PROVIDER`, `PERPLEXITY_API_KEY`, `PERPLEXITY_ENDPOINT`, `PERPLEXITY_MODEL`)
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981733280
Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1231_FIXED_MAPPING.md` entries above map all actionable inline comments; review-summary comments from bots are informational wrappers over already mapped items.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#pullrequestreview-3999279826
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#pullrequestreview-3999355816
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#pullrequestreview-3999367140
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#pullrequestreview-3999432091
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#pullrequestreview-3999471188

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (resolve on GitHub after push)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
