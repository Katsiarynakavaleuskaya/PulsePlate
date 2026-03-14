# PR 1164 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Initial PR body aligned to project canon
- [ ] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

### Fixed in Commit Mapping
Disposition: FIXED
Commit: be6d29a5
Evidence: `app/routers/api_key.py:19`, `app/routers/api_key.py:21`, `tests/test_business_router.py:142`, `tests/test_business_router_coverage.py:79`, `tests/test_business_router_coverage.py:87`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934851690 -> be6d29a5
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934854342 -> be6d29a5

Disposition: FIXED
Commit: be6d29a5
Evidence: `tests/test_business_router.py:93`, `tests/test_business_router.py:97`, `tests/test_business_router_coverage.py:87`, `tests/test_business_router_coverage.py:201`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934856658 -> be6d29a5

Disposition: NOT-A-BUG
Reason: This PR centralizes app-level API key validation in `app/routers/api_key.py` and reuses that helper from the business router. The remaining duplication concern in other legacy routers predates this lane and was not introduced by the current diff.
Evidence: `app/routers/api_key.py:16`, `app/routers/business.py:10`, `app/routers/business.py:93`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934854343

Disposition: NOT-A-BUG
Reason: These review-level bot comments are aggregate summaries of inline findings that are already dispositioned above and do not add separate unfixed obligations.
Evidence: `docs/review/PR_1164_FIXED_MAPPING.md:8`, `docs/review/PR_1164_FIXED_MAPPING.md:13`, `docs/review/PR_1164_FIXED_MAPPING.md:18`, `docs/review/PR_1164_FIXED_MAPPING.md:23`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#pullrequestreview-3948322337
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#pullrequestreview-3948326367
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#pullrequestreview-3948328323

Disposition: FIXED
Commit: 7bbc8a6b
Evidence: `app/routers/api_key.py:16`, `app/routers/api_key.py:19`, `tests/test_business_router.py:153`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934901526 -> 7bbc8a6b

Disposition: FIXED
Commit: <pending-docs-commit>
Evidence: `docs/review/PR_1164_FIXED_MAPPING.md:33`, `docs/review/PR_1164_FIXED_MAPPING.md:35`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#discussion_r2934901527 -> <pending-docs-commit>

Disposition: NOT-A-BUG
Reason: This review-level CodeRabbit summary only aggregates the two inline findings above and does not introduce a separate actionable beyond those mapped threads.
Evidence: `docs/review/PR_1164_FIXED_MAPPING.md:25`, `docs/review/PR_1164_FIXED_MAPPING.md:31`, `docs/review/PR_1164_FIXED_MAPPING.md:35`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1164#pullrequestreview-3948385258

## Merge Readiness
- [ ] Local gates passed on current head
- [ ] All required checks green
- [ ] No unresolved review threads remain
- [ ] CodeRabbit PASS / no-actionables
- [ ] Sourcery PASS / no-actionables
- [ ] Cubic PASS / no-actionables
- [ ] Wait-window after latest bot/review activity observed

Local gate baseline before current discussion-thread pass:
- `pre-commit run --all-files`
- `make lint`
- `make typecheck`
- `make test-fast`
- `.venv/bin/coverage erase && .venv/bin/coverage run -m pytest -q && .venv/bin/coverage xml -o coverage_verify.xml && .venv/bin/diff-cover coverage_verify.xml --compare-branch=origin/main --fail-under=97`
