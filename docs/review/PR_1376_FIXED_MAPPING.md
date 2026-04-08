# PR #1376 — Fixed in Commit Mapping (SoT)

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

Bot and human review threads must be dispositioned below when actionable comments appear; resolve conversations on GitHub only after mapping per `AGENTS.md`.

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 5ab8a3780
Evidence: app/services/food_store.py:126; core/judgment.py:144; core/judgment_eval.py:169; core/creative_research.py:407; tests/test_food_store_service.py:335

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#issuecomment-4204538823 -> 5ab8a3780
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#pullrequestreview-4073510048 -> 5ab8a3780
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049869404 -> 5ab8a3780
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049869411 -> 5ab8a3780
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049869428 -> 5ab8a3780

Disposition: FIXED
Commit: c803b348d
Evidence: app/services/food_store.py:202; tests/test_food_store_service.py:272; tests/test_food_store_service.py:342; tests/test_food_store_service.py:381

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049873465 -> c803b348d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049907717 -> c803b348d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049954462 -> c803b348d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049954467 -> c803b348d
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049954477 -> c803b348d

Disposition: NOT-A-BUG
Evidence: AGENTS.md:5; AGENTS.md:40; scripts/orchestration/review_mapping_artifact.py:152
Reason: CodeRabbit's walkthrough and generic pre-merge warnings are advisory only for this repository. The canonical merge gates are `make verify`, explicit disposition tracking for bot comments, and the PR `<N>` fixed-mapping artifact mirror.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#issuecomment-4204532851

Disposition: NOT-A-BUG
Evidence: app/services/food_store.py:202; tests/test_food_store_service.py:381
Reason: The Codex review summary only aggregates the alias-qualified missing-column finding that is fixed in `c803b348d`; the summary itself does not require a separate code change once the underlying inline thread is dispositioned.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#pullrequestreview-4073514071

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1375_FIXED_MAPPING.md:1; tests/test_simple_coverage_boost.py:56; app/routers/foods.py:68; app/services/food_store.py:202
Reason: This CodeRabbit review summary aggregates one retry-predicate fix already landed in `c803b348d`, two intentional historical-evidence notes for superseded PR `#1375`, and one fixture warning that is invalid on current head because the route parameter is `query`, not `q`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#pullrequestreview-4073549805
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049907730
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049907733
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049907738

Disposition: NOT-A-BUG
Evidence: docs/review/PR_1375_FIXED_MAPPING.md:1; app/services/food_store.py:126; tests/test_food_store_service.py:272
Reason: Cubic's review summary aggregates two findings already fixed in `c803b348d` and one intentional historical-evidence artifact for superseded PR `#1375`; the remaining PR-number comment is governance context, not a product defect on PR `#1376`.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#pullrequestreview-4073610573
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#discussion_r3049954474

Disposition: NOT-A-BUG
Evidence: AGENTS.md:8; AGENTS.md:16
Reason: The external Codecov patch-coverage advisory was generated on an earlier head. The repository's canonical gate is local `make verify`, which includes diff-cover ≥97% and now passes on the current branch head.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1376#issuecomment-4204654240

## Merge Readiness

- [ ] Current-head CI green for PR branch head
- [ ] Required checks complete (no pending jobs)
- [ ] All review threads resolved on GitHub after disposition updates

### Scope Notes

- Primary hotfix commit: `d4eb976e7` — restore legacy-schema-safe `food_store` compatibility for missing `foods.nutrition_confidence`
- Merge-gate unblock commits:
  - `cb533ed72` — remove redundant casts blocking repo `make verify`
  - `b0a4bc2a9` — preserve literal narrowing for push-hook mypy on changed files
- Mainline reconciliation commit:
  - `63340da16` — merge latest `main` into `fix/main-food-search-legacy-schema-compat` and keep the literal-safe `core/*` typing fix while accepting current `main` changes
- Sanctioned scope expansion was limited to:
  - `core/judgment.py`
  - `core/judgment_eval.py`
  - `core/creative_research.py`
- Superseded artifact note:
  - `docs/review/PR_1375_FIXED_MAPPING.md` is retained only as historical evidence for the superseded hotfix PR; `docs/review/PR_1376_FIXED_MAPPING.md` is the active canonical artifact for live review and merge governance.

### Local Verification

- `python3 scripts/orchestration/check_preflight.py`
- `python3 scripts/orchestration/check_agent_consistency.py`
- `pre-commit run --all-files`
- `make verify`
- mandatory final `bug-hunter` pass completed with no blocking findings

## Deferred / Follow-ups

- `docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-food-store-legacy-schema-cache-follow-through`
