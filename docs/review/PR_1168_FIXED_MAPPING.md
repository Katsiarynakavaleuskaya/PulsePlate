# PR 1168 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: 89283dd4d55bc678a4954838de30c3404cc2697d
Evidence: `tests/test_app_lifespan_additional.py:165` adds the positive production startup case with explicit `ALLOW_DEV_API_KEY=false` and `ALLOW_ANONYMOUS_API_KEYS=false`, while `tests/test_app_lifespan_additional.py:184` proves `app.lifespan(...)` now succeeds when `PRO_LLM_INSIGHT_REQUESTS_PER_MONTH` is a valid integer instead of only checking the fail path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#pullrequestreview-3948673639 -> 89283dd4d55bc678a4954838de30c3404cc2697d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1168#discussion_r2935133225 -> 89283dd4d55bc678a4954838de30c3404cc2697d

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
