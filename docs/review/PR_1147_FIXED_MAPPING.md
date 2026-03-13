# PR 1147 — Fixed in Commit Mapping

## Discussion Thread Pass
- [x] Discussion-thread pass completed
- [x] Fixed in commit mapping completed

## Fixed in Commit Mapping
- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3939415411
Disposition: NOT-A-BUG
Evidence: .github/workflows/ios-appstore-assets.yml:24
Evidence: .github/workflows/ios-appstore-assets.yml:25
Reason: This review shell contains only the three workflow-permissions findings mapped below; no additional review-level action remains beyond the explicit `contents: read` fix.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3942777950
Disposition: NOT-A-BUG
Evidence: .github/workflows/ios-appstore-assets.yml:159
Evidence: ios/PulsePlateUITests/AppStoreScreenshotTests.swift:85
Reason: This review shell contains only the privacy-upload validator split and screenshot-locale consistency findings mapped below; no additional review-level action remains.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3942816854
Disposition: NOT-A-BUG
Evidence: ios/fastlane/Appfile:1
Evidence: ios/fastlane/Fastfile:126
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The first cubic aggregate review is satisfied by the explicit FIXED mappings below plus the deferred `ios_version` cleanup captured in the backlog anchor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943626630
Disposition: NOT-A-BUG
Evidence: ios/fastlane/verify/validate_dimensions.rb:1
Evidence: ios/PulsePlate/en.lproj/InfoPlist.strings:2
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The first CodeRabbit review shell is satisfied by the FIXED script-mode/HealthKit/localization mappings below plus the deferred shared-scenario cleanup anchor.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943770421
Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Services/ProfileProvider.swift:3
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The later CodeRabbit review shell is satisfied by the shared-key fix, the existing screenshot/localization fixes, and the deferred shared-scenario follow-up recorded in the backlog.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943866079
Disposition: NOT-A-BUG
Evidence: ios/fastlane/verify/validate_color_gamut.rb:9
Evidence: ios/fastlane/verify/validate_metadata.rb:80
Evidence: tests/test_ios_appstore_asset_validators.py:177
Reason: The later cubic aggregate review is satisfied by the validator hardening and coverage additions mapped below; no separate review-shell action remains.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3943895317
Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Models/HealthKitManager.swift:69
Evidence: core/compliance/privacy.py:132
Evidence: ios/fastlane/verify/validate_metadata.rb:8
Reason: This review shell is satisfied by the fixed validator/localization mappings below plus two explicit NOT-A-BUG dispositions: HealthKit data remains read-only/request-scoped, and the validator intentionally requires a full source-controlled metadata pack.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3944019711
Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:41
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:344
Reason: This review shell contains only the fail-fast scenario parsing fix and the merge-readiness checkbox/doc-proof fixes mapped below; no additional review-level action remains.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#pullrequestreview-3944034323
Disposition: NOT-A-BUG
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:10
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:49
Evidence: docs/roadmap/BACKLOG_LEDGER.md:1497
Reason: The final cubic review shell is satisfied by the artifact-proof corrections and the existing deferred cleanup anchor; no separate action remains beyond the doc fix mapped below.

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

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931050194 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:77
Evidence: tests/test_ios_appstore_asset_validators.py:197

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931050204 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/fastlane/verify/validate_metadata.rb:80
Evidence: tests/test_ios_appstore_asset_validators.py:223

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931050209 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/fastlane/verify/validate_color_gamut.rb:9
Evidence: ios/fastlane/verify/validate_color_gamut.rb:44
Evidence: ios/fastlane/verify/validate_color_gamut.rb:73

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931050216 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/PulsePlate/Views/PlateView.swift:111

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931050222 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: tests/test_ios_appstore_asset_validators.py:177
Evidence: tests/test_ios_appstore_asset_validators.py:197

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075456
Disposition: NOT-A-BUG
Evidence: ios/PulsePlate/Models/HealthKitManager.swift:69
Evidence: core/compliance/privacy.py:132
Evidence: ios/fastlane/app_privacy_details.json:1
Reason: HealthKit access is read-only on device, and backend wellness-profile requests are documented as request-scoped unless a separate persistence feature is introduced; the App Privacy payload intentionally stays `DATA_NOT_COLLECTED` for this release.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075466 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/fastlane/verify/validate_color_gamut.rb:9
Evidence: ios/fastlane/verify/validate_color_gamut.rb:26
Evidence: tests/test_ios_appstore_asset_validators.py:177

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075478 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/fastlane/verify/validate_healthkit_copy.rb:22
Evidence: tests/test_ios_appstore_asset_validators.py:197

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075493
Disposition: NOT-A-BUG
Evidence: ios/fastlane/verify/validate_metadata.rb:8
Evidence: ios/fastlane/metadata/en-US/marketing_url.txt:1
Evidence: ios/fastlane/metadata/en-US/release_notes.txt:1
Reason: Apple may treat these fields as optional in some submission contexts, but this repo intentionally requires a full localized metadata pack so launch-ready App Store copy remains source-controlled and CI-validated across locales.

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075494 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:153
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:167

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931075502 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:220
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:225

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931182975 -> TBD
Disposition: FIXED
Commit: TBD
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:344

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931182982 -> 5f7232e7
Disposition: FIXED
Commit: 5f7232e7
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:44
Evidence: ios/PulsePlate/AppStore/AppStoreScreenshotContext.swift:47

- https://github.com/Katsiarynakavaleuskaya/PulsePlate/pull/1147#discussion_r2931195563 -> TBD
Disposition: FIXED
Commit: TBD
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:10
Evidence: docs/review/PR_1147_FIXED_MAPPING.md:49

## Merge Readiness
- [ ] Local hard gate passed (`pre-commit run --all-files`; `pytest -q tests/test_ios_appstore_asset_validators.py`; `make ios-test IOS_ONLY_TESTING="PulsePlateUITests/AppStoreScreenshotTests"`; `make verify`)
- [ ] Required checks PASS with no pending required jobs
- [ ] No unresolved review threads
- [ ] No actionable bot comments
- [ ] Final post-bot wait cycle completed
