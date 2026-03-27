# PR 1261 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: 1c1e696e
Evidence: `tests/test_python_supply_chain_controls.py:162-193`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3000456021 -> 1c1e696e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3000473556 -> 1c1e696e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3000476879 -> 1c1e696e
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#pullrequestreview-4020537149 -> 1c1e696e

Disposition: FIXED
Commit: 14347b44
Evidence: `.github/actions/python-setup/action.yml:43-67`, `tests/test_python_supply_chain_controls.py:47-68`
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3000466719 -> 14347b44

Disposition: DEFERRED
Backlog: `docs/roadmap/BACKLOG_LEDGER.md#ledger-p1-ci-install-profile-split-after-disk-unblock`
Reason: PR 1261 intentionally unblocks the disk regression with the minimal direct-proxy consolidation and defers the heavier CI install-profile / dependency-surface split to the tracked follow-up ledger item.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3000585619
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#pullrequestreview-4020685400

Disposition: NOT-A-BUG
Evidence: `docs/review/PR_1261_FIXED_MAPPING.md:8-31`
Reason: These aggregate bot summaries only restate actionable findings already dispositioned by the mapped inline thread URLs above, so they do not require separate code changes or backlog items.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#issuecomment-4141912212
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#pullrequestreview-4020555158
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#pullrequestreview-4020559328

Disposition: NOT-A-BUG
Evidence: `requirements-ci-lite.txt:1`, `scripts/ci/check_pygments_exception_guard.py:26-32`
Reason: The reported missing-file path is not reachable on this branch because `requirements-ci-lite.txt` is added in the same PR, so tracking it in the Pygments guard does not introduce a crash path.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#discussion_r3001884612
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1261#pullrequestreview-4022193858

## Merge Readiness
- [ ] All required checks pass
- [ ] No unresolved review threads
- [ ] No actionable bot comments remain unmapped in `Fixed in Commit Mapping`
- [ ] `pre-commit run --all-files`
- [ ] `make verify`
