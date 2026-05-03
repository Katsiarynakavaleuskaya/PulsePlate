# PR #1636 — Fixed in Commit Mapping (SoT)

## Summary

Makes `scripts/release/release_manifest.py` usable via direct file invocation
(`python3 scripts/release/release_manifest.py --help`) by adding a guarded
`__package__` bootstrap. Adds subprocess tests for both direct and module
invocation modes.

## Discussion Thread Pass

- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#discussion_r3177344216
  Disposition: NOT-A-BUG
  Evidence: AGENTS.md:1781 — "scripts/ may use sys.path.insert for standalone CLI only".
  30+ existing scripts/ files use the same pattern. Import hygiene guards only scan tests/, not scripts/.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215625075
  Disposition: NOT-A-BUG
  Evidence: Sourcery rate-limited; no analysis produced. No actionable items.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215626240
  Disposition: NOT-A-BUG
  Evidence: CodeRabbit review summary; single inline comment addressed above.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1636#pullrequestreview-4215626612
  Disposition: NOT-A-BUG
  Evidence: Cubic found no issues ("No issues found across 1 file").

## Merge Readiness

- [x] All bot reviews mapped with disposition
- [x] CodeRabbit inline thread resolved as NOT-A-BUG with policy evidence
- [x] `make validate-min` passed locally
- [x] `pre-commit run --all-files` passed locally
- [x] Import hygiene guards pass (15/15)
- [x] Release manifest tests pass (20/20)
- [x] Direct invocation verified: `python3 scripts/release/release_manifest.py --help` exits 0
- [x] Module invocation verified: `python3 -m scripts.release.release_manifest --help` exits 0
