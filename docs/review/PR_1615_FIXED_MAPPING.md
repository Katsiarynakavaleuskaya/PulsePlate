# PR #1615 Fixed Mapping

## Scope

CI hygiene and coverage PR: Bandit/nosec policy alignment, targeted test and small
production-path fixes, VS Code extension allowlist sync (`sst-dev.opencode`),
and detect-secrets baseline refresh.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

- Bot findings (Sourcery, CodeRabbit) mapped under **Fixed in Commit Mapping**
  with disposition and evidence. Re-check required CI and operator merge wrapper
  before merge.

## Fixed in Commit Mapping

Disposition: NOT-A-BUG

Evidence: `core/integrated_bayesian_analyzer.py:186` uses explicit `list(...)` for stable `List[str]`; refactoring `analyze_technical_aspects_common` return typing is deferred.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1615#pullrequestreview-4212503005

Disposition: NOT-A-BUG

Evidence: `tests/test_food_db_new_realistic_coverage.py:154` keeps intentional broad except/pass in the coverage harness with Bandit-nosec and remove-by metadata per repo policy.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1615#discussion_r3174426934

Disposition: NOT-A-BUG

Evidence: CodeRabbit `pullrequestreview-4212527857` is a batch summary only (Actionable comments posted); inline URLs carry thread-level disposition.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1615#pullrequestreview-4212527857

Disposition: FIXED

Evidence: `core/menu_engine_new.py:171` narrows kcal assignment guard to TypeError/AttributeError instead of bare Exception.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1615#discussion_r3174426915 -> 96b79808f7f5cbb99196085d310c7f6912295e46

Disposition: FIXED

Evidence: `tests/test_app_db_fallback_97.py:215` restores SessionLocal, _RAW_ENGINE, engine, fallback flag, and env after `_configure_session_bindings` per AGENTS DB test hygiene.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1615#discussion_r3174426926 -> 96b79808f7f5cbb99196085d310c7f6912295e46

## Validation

- Canonical artifact validated via `python3 -c` importing
  `scripts.orchestration.review_mapping_artifact.validate_mapping_artifact_text`
  after edit (local).

## Merge Readiness

- Required current-head CI must be green before merge.
- `check_merge_ready.py --require-auth` remains operator-gated before merge.

## Out of Scope

- Coverage threshold changes, workflow weakening, or unrelated product features.
