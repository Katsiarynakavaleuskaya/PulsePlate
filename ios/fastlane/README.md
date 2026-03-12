fastlane documentation
----

# Installation

Make sure you have the latest version of the Xcode command line tools installed:

```sh
xcode-select --install
```

For _fastlane_ installation instructions, see [Installing _fastlane_](https://docs.fastlane.tools/#installing-fastlane)

# Available Actions

## iOS

### ios snapshot_all

```sh
[bundle exec] fastlane ios snapshot_all
```

Capture deterministic localized App Store screenshots

### ios validate_assets

```sh
[bundle exec] fastlane ios validate_assets
```

Validate screenshot dimensions, color profile, metadata, and HealthKit copy alignment

### ios upload_metadata_and_screenshots

```sh
[bundle exec] fastlane ios upload_metadata_and_screenshots
```

Upload localized metadata and screenshots to App Store Connect draft

### ios upload_app_privacy

```sh
[bundle exec] fastlane ios upload_app_privacy
```

Upload App Privacy questionnaire answers using Apple ID session auth

### ios release_assets

```sh
[bundle exec] fastlane ios release_assets
```

Run screenshot capture, validation, and metadata/screenshots upload

----

This README.md is auto-generated and will be re-generated every time [_fastlane_](https://fastlane.tools) is run.

More information about _fastlane_ can be found on [fastlane.tools](https://fastlane.tools).

The documentation of _fastlane_ can be found on [docs.fastlane.tools](https://docs.fastlane.tools).
