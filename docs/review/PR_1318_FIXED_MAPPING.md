# PR 1318 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping

Disposition: FIXED
Commit: b5984f92
Evidence: identified by cubic in `https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#pullrequestreview-4055966995`. `ios/fastlane/Fastfile:89` now enforces `fastlane/metadata` as a directory via `require_existing_directory!`, `ios/fastlane/Fastfile:95` now enforces `app_privacy_details.json` as a file via `require_existing_file!`, and `tests/test_ios_appstore_assets_workflow_contract.py:148` plus `tests/test_ios_appstore_assets_workflow_contract.py:162` lock the helper contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#pullrequestreview-4055966995 -> b5984f92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#discussion_r3033101077 -> b5984f92
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#discussion_r3033101084 -> b5984f92

Disposition: FIXED
Commit: 356a2083
Evidence: identified by CodeRabbit. `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md:83` now includes `python3 scripts/orchestration/check_preflight.py` and `python3 scripts/orchestration/check_agent_consistency.py` in the validation-only checklist, while `ios/fastlane/Fastfile:176` now requires `FASTLANE_TEAM_ID` and `FASTLANE_TEAM_NAME` before App Privacy upload and `tests/test_ios_appstore_assets_workflow_contract.py:153` locks the expanded fail-closed env contract.
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#pullrequestreview-4055985256 -> 356a2083
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#discussion_r3033118348 -> 356a2083
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1318#discussion_r3033118351 -> 356a2083

## Merge Readiness
- [ ] Local hard gate passed (`make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
Notes: Implementation-only App Store assets activation-prep PR. This PR does not
claim rollout closeout; protected post-merge evidence on `main` and a separate
docs-only follow-up PR are still required.
