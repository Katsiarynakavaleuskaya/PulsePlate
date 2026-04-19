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

## Post-Merge State

- GitHub PR status: `merged=true`
- Merge commit: `52053dd8953fd48bcac98e1754ee4104d33b9ea6`
- Merged at: `2026-04-03T15:08:49Z`

## Merge Readiness
- [x] Discussion-thread mapping preserved after merge
- [x] Merge commit and merged timestamp recorded
- [ ] Protected `main` dispatch evidence collected
- [ ] Rollout closeout follow-up completed
Notes: PR 1318 merged as the implementation-only App Store assets
activation-prep change. Rollout closeout is still deferred until protected
`upload_to_asc=true` and `upload_app_privacy=true` evidence is collected on
`main`, after which a separate docs-only closeout PR should update the ledger
and evidence references.
