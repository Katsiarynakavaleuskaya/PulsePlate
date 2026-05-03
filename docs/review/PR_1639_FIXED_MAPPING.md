# PR 1639 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1639#pullrequestreview-4216072842
Disposition: NOT-A-BUG
Evidence: Current repo dependency-fallback and mirror-catch-up policy is represented in `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-cryptography-private-index-sync`; this PR keeps `pre-commit` at the mirrored installable floor used in this lane (`4.5.1`) to preserve deterministic CI behavior until the private index mirror supports the intended bump.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1639#discussion_r3177842097
Disposition: NOT-A-BUG
Evidence: See same lane-level constraint rationale as above for `pre-commit` pin selection in this branch: `requirements-dev.txt` and `requirements-ci-lite.in` are intentionally aligned to the installable wheelhouse version to keep `make verify`-relevant dependency installs stable under current CI mirror state.
