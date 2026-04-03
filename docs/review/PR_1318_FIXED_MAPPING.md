# PR 1318 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b5984f92
Evidence: identified by cubic in `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#pullrequestreview-4055966995`. `ios/fastlane/Fastfile:89` now enforces `fastlane/metadata` as a directory via `require_existing_directory!`, `ios/fastlane/Fastfile:95` now enforces `app_privacy_details.json` as a file via `require_existing_file!`, and `tests/test_ios_appstore_assets_workflow_contract.py:148` plus `tests/test_ios_appstore_assets_workflow_contract.py:162` lock the helper contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#pullrequestreview-4055966995 -> b5984f92

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
Notes: Implementation-only App Store assets activation-prep PR. This PR does not
claim rollout closeout; protected post-merge evidence on `main` and a separate
docs-only follow-up PR are still required.
