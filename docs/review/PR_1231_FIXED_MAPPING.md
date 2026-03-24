## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
Disposition: FIXED
Commit: 81b79450
Evidence: `llm.py`, `.env.example`, `tests/test_llm_comprehensive.py`, `tests/test_llm_extras.py`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981662350
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981696506
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
Disposition: NOT-A-BUG
Evidence: `tests/test_llm_comprehensive.py` (`TestPerplexityLiteProvider.test_grok_lite_provider_through_exception`) intentionally validates provider-unavailable fallback path by setting `PerplexityProvider=None`; this is distinct from API-key guard coverage, which is already covered in `tests/test_llm_extras.py`.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1231#discussion_r2981723500

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads (resolve on GitHub after push)
- [x] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] Pre-commit green
