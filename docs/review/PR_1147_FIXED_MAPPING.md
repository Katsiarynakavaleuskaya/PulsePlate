# PR 1147 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3939415411
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:13
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:17
Reason: The GitHub Advanced Security review shell is satisfied by the explicit workflow-permissions thread mappings recorded below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3942777950
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:29
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:33
Reason: The Codex review shell is satisfied by the individually mapped App Privacy validation and locale-handling thread dispositions below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3942816854
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:37
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:93
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:101
Reason: The first cubic aggregate review is satisfied by the FIXED and DEFERRED mappings recorded below; no separate unmapped action remains at the review-shell level.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943626630
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:69
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:109
Reason: The first CodeRabbit review shell is satisfied by the explicit FIXED thread mappings and the deferred backlog follow-up recorded below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943770421
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:117
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The later CodeRabbit review shell is satisfied by the shared-key fix in `fda35188`, the existing screenshot/localization fixes, and the deferred shared-scenario follow-up recorded below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943866079
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:117
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The later cubic aggregate review is satisfied by the shared-key fix, the localized copy fix, and the explicit deferred cleanup anchor captured below.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2927088169 -> 5086c136
Disposition: FIXED
Commit: 5086c136
Evidence: .github/workflows/ios-appstore-assets.yml:24
Evidence: .github/workflows/ios-appstore-assets.yml:25

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2927088177 -> 5086c136
Disposition: FIXED
Commit: 5086c136
Evidence: .github/workflows/ios-appstore-assets.yml:24
Evidence: .github/workflows/ios-appstore-assets.yml:25

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2927088182 -> 5086c136
Disposition: FIXED
Commit: 5086c136
Evidence: .github/workflows/ios-appstore-assets.yml:24
Evidence: .github/workflows/ios-appstore-assets.yml:25

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930102763 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: .github/workflows/ios-appstore-assets.yml:159
Evidence: .github/workflows/ios-appstore-assets.yml:161
Evidence: ios/fastlane/Fastfile:101
Evidence: ios/fastlane/Fastfile:105

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930102771 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:121
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:132
Evidence: ios/PulsePlateUITests/AppStoreScreenshotTests.swift:85
Evidence: ios/PulsePlateUITests/AppStoreScreenshotTests.swift:100
Reason: Screenshot locale now comes from Fastlane/Xcode language injection and `Locale.preferredLanguages`; the UITest no longer overrides locale with a second source of truth.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140358 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/Appfile:1
Evidence: ios/fastlane/Appfile:4
Evidence: ios/fastlane/Fastfile:37
Evidence: ios/fastlane/Fastfile:42

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140363 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/app_privacy_details.json:1
Evidence: ios/fastlane/app_privacy_details.json:6
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:71
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:79

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140368 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:52
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:55
Reason: Screenshot preview PRO state is now computed in-memory only; there is no longer any write path that seeds Keychain state during screenshot bootstrap.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140370 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: .github/workflows/ios-appstore-assets.yml:159
Evidence: .github/workflows/ios-appstore-assets.yml:161
Evidence: ios/fastlane/Fastfile:101
Evidence: ios/fastlane/Fastfile:105

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140378 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlateUITests/SnapshotHelper.swift:237
Evidence: ios/PulsePlateUITests/SnapshotHelper.swift:245

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140384 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: .github/workflows/ios-appstore-assets.yml:126
Evidence: .github/workflows/ios-appstore-assets.yml:139

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140386 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: .github/workflows/ios-appstore-assets.yml:141
Evidence: .github/workflows/ios-appstore-assets.yml:170
Evidence: ios/fastlane/Fastfile:126
Evidence: ios/fastlane/Fastfile:136

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140389 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: tests/test_ios_appstore_asset_validators.py:170
Evidence: tests/test_ios_appstore_asset_validators.py:188

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140391 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/verify/validate_metadata.rb:20
Evidence: ios/fastlane/verify/validate_metadata.rb:21
Evidence: ios/fastlane/verify/validate_metadata.rb:66
Evidence: ios/fastlane/verify/validate_metadata.rb:68

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140396 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:62
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:79
Reason: Screenshot bootstrap and rendering both default to `.home` when screenshot mode is enabled without an explicit scenario argument.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140400 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:13
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:17

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140404 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/es.lproj/Localizable.strings:148
Evidence: ios/PulsePlate/es.lproj/Localizable.strings:153

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140408 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/verify/validate_color_gamut.rb:7
Evidence: ios/fastlane/verify/validate_color_gamut.rb:61
Evidence: ios/fastlane/verify/validate_color_gamut.rb:62

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140411
Disposition: DEFERRED
Backlog: docs/roadmap/BACKLOG_LEDGER.md#ledger-p2-pr1147-ios-appstore-asset-followups
Reason: Pinning/documenting an explicit `ios_version` strategy is valid cleanup, but it is intentionally deferred out of PR #1147 to avoid reopening the stabilized snapshot matrix during merge-readiness.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140413 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/Views/PlateView.swift:111
Evidence: ios/PulsePlate/Views/PlateView.swift:147
Evidence: ios/PulsePlate/Views/PlateView.swift:148

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140423 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/fastlane/metadata/ru-RU/release_notes.txt:1
Evidence: ios/fastlane/metadata/en-US/release_notes.txt:1
Evidence: ios/fastlane/metadata/es-ES/release_notes.txt:1

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930140425 -> e44c851b
Disposition: FIXED
Commit: e44c851b
Evidence: ios/PulsePlate/ru.lproj/Localizable.strings:161

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930853827 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: `git ls-files --stage ios/fastlane/verify/validate_dimensions.rb` -> `100755`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930853846 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: `git ls-files --stage ios/fastlane/verify/validate_metadata.rb` -> `100755`

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930853869 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/en.lproj/InfoPlist.strings:2
Evidence: ios/PulsePlate/es.lproj/InfoPlist.strings:2
Evidence: ios/PulsePlate/ru.lproj/InfoPlist.strings:2
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:43
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:53

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930968063 -> fda35188
Disposition: FIXED
Commit: fda35188
Evidence: ios/PulsePlate/Services/ProfileProvider.swift:3
Evidence: ios/PulsePlate/Services/ProfileProvider.swift:4
Evidence: ios/PulsePlate/Models/LocalizationManager.swift:9
Evidence: ios/PulsePlate/Models/LocalizationManager.swift:17
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:66

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930968073 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:52
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:55
Reason: The side-effectful screenshot PRO-key seeding path was removed; there is no longer a failing setter path to swallow.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2930968075 -> ccdb089d
Disposition: FIXED
Commit: ccdb089d
Evidence: ios/PulsePlate/Views/PlateView.swift:111
Evidence: ios/PulsePlate/Views/PlateView.swift:147
Evidence: ios/PulsePlate/Views/PlateView.swift:148

## Merge Readiness
- [x] Local hard gate passed (`pre-commit run --all-files`; `pytest -q tests/test_ios_appstore_asset_validators.py`; `make ios-test IOS_ONLY_TESTING="PulsePlateUITests/AppStoreScreenshotTests"`; `make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
