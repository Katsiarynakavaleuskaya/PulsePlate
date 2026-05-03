# PR #1636 — Fixed in Commit Mapping (SoT)

## Summary

Makes `scripts/release/release_manifest.py` usable via direct file invocation
by adding a guarded `__package__` bootstrap. Adds subprocess tests for both
direct and module invocation modes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#discussion_r3177344216
  Disposition: NOT-A-BUG
  Evidence: AGENTS.md:1781 allows path bootstrap in scripts/; 30+ existing precedents.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215625075
  Disposition: NOT-A-BUG
  Evidence: Sourcery rate-limited; no analysis produced.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215626240
  Disposition: NOT-A-BUG
  Evidence: CodeRabbit single inline comment addressed above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215626612
  Disposition: NOT-A-BUG
  Evidence: Cubic found no issues.

## Merge Readiness

- [x] All bot reviews mapped with disposition
- [x] CodeRabbit inline thread resolved as NOT-A-BUG with policy evidence
- [x] `make validate-min` passed locally
- [x] `pre-commit run --all-files` passed locally
- [x] Import hygiene guards pass (15/15)
- [x] Release manifest tests pass (20/20)
