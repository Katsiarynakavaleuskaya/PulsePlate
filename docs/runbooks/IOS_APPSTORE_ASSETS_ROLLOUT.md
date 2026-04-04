# iOS App Store Assets Rollout

This runbook defines the protected release-ops flow for App Store metadata,
screenshots, and App Privacy uploads.

## Scope

This lane governs only:

- localized App Store metadata uploads
- screenshot uploads to App Store Connect draft state
- App Privacy questionnaire uploads
- protected evidence collection after merge

This lane does not govern:

- semantic validator expansion
- screenshot scenario redesign
- token semantic changes
- visual redesign driven by Figma/Canva
- Apple Server API migration
- backend or web deploy truth

## Source Of Truth

Protected rollout must stay aligned with the current repo-owned contract:

- Workflow: `.github/workflows/ios-appstore-assets.yml`
- Fastlane lanes: `ios/fastlane/Fastfile`
- Screenshot validator suite: `tests/test_ios_appstore_asset_validators.py`
- Workflow contract suite: `tests/test_ios_appstore_assets_workflow_contract.py`
- Screenshot scenarios: `ios/PulsePlateUITests/AppStoreScreenshotTests.swift`
- Design-token SoT:
  - `docs/design/TOKENS_SOT.md`
  - `frontend/src/styles/tokens.ts`
  - `ios/PulsePlate/DesignSystem/DesignTokens.swift`

## Secret Ownership And Placement

Protected secrets must live in GitHub protected environments, not in repo files
and not in PR branches.

### Environment: `appstore-assets`

Required secrets:

- `ASC_KEY_ID`
- `ASC_ISSUER_ID`
- `ASC_KEY_P8_BASE64`
- `APP_STORE_BUNDLE_IDENTIFIER`

Workflow / Fastlane env mapping:

| GitHub protected secret | Workflow / Fastlane env var |
| --- | --- |
| `ASC_KEY_ID` | `APP_STORE_CONNECT_API_KEY_ID` |
| `ASC_ISSUER_ID` | `APP_STORE_CONNECT_API_ISSUER_ID` |
| `ASC_KEY_P8_BASE64` | `APP_STORE_CONNECT_API_KEY` |
| `APP_STORE_BUNDLE_IDENTIFIER` | `APP_STORE_BUNDLE_IDENTIFIER` |

The GitHub secret names above are mapped by the workflow into the env vars used
by Fastlane preflight checks and upload logs.

Purpose:

- unlock `upload_to_asc=true` manual dispatch
- provide App Store Connect API authentication

### Environment: `appstore-privacy`

Required secrets:

- `FASTLANE_USER`
- `FASTLANE_SESSION`
- `FASTLANE_TEAM_ID`
- `FASTLANE_TEAM_NAME`
- `APP_STORE_BUNDLE_IDENTIFIER`

Purpose:

- unlock `upload_app_privacy=true` manual dispatch
- provide Apple ID session authentication for App Privacy upload

### Ownership Rule

- release-ops owner manages protected environment configuration
- implementation PR must not claim rollout completion without protected-run evidence
- missing secrets are a fail-closed operator condition, not a reason to weaken guards

## Validation-Only Path

Use validation-only flow before any protected upload:

1. Run implementation PR checks locally:
   - `python3 scripts/orchestration/check_preflight.py`
   - `python3 scripts/orchestration/check_agent_consistency.py`
   - `pytest -q tests/test_ios_appstore_assets_workflow_contract.py`
   - `pytest -q tests/test_ios_appstore_asset_validators.py`
   - `pre-commit run --all-files`
   - `make verify`
2. Confirm the workflow/Fastlane contract is merged to `main`.
3. Use PR validation and normal CI to ensure screenshot capture and validator
   surfaces stay green without touching protected upload paths.

### Semantic validator outcomes

The separate semantic-validator lane stays repo-local and does not require Apple
enrollment or protected upload access.

Blocking semantic failures:

- App Store-facing copy uses medical / diagnosis / treatment / cure framing
- App Store-facing copy makes guaranteed or promissory outcome claims
- App Store-facing copy hardcodes pricing / trial / eligibility / billing claims
  that must remain StoreKit / App Store truth
- Reviewer notes or HealthKit copy contradict the current read-only /
  `DATA_NOT_COLLECTED` posture

Advisory findings:

- machine-readable lines in the form `ADVISORY: <file> :: <reason>`
- future privacy-review hints or suspicious-but-non-contradictory wording
- advisory findings do not by themselves close or reopen the Apple-dependent
  rollout evidence lane

## Protected Upload Procedure

Protected uploads are allowed only from:

- `refs/heads/main`
- `refs/heads/release/*`
- `refs/tags/release-*`

### Upload metadata and screenshots

1. Merge the implementation PR to `main`.
2. Open GitHub Actions for `ios-appstore-assets`.
3. Start `workflow_dispatch` with:
   - `upload_to_asc=true`
   - `upload_app_privacy=false`
4. Verify the run reaches:
   - screenshot artifact download
   - protected ref guard pass
   - protected secret preflight pass
   - successful `bundle exec fastlane ios upload_metadata_and_screenshots`
5. Record the run URL / run ID for evidence.

### Upload App Privacy

1. Open GitHub Actions for `ios-appstore-assets`.
2. Start `workflow_dispatch` with:
   - `upload_to_asc=false`
   - `upload_app_privacy=true`
3. Verify the run reaches:
   - metadata package validation
   - protected ref guard pass
   - protected secret preflight pass
   - successful `bundle exec fastlane ios upload_app_privacy`
4. Record the run URL / run ID for evidence.

## Reviewer Notes Update Procedure

Before the protected metadata/screenshots upload:

1. Review `ios/fastlane/metadata/review_information/notes.txt`.
2. Confirm reviewer notes still match:
   - current HealthKit behavior
   - wellness-only positioning
   - read-only integration claims
3. If notes changed in the implementation lane, re-run:
   - `pytest -q tests/test_ios_appstore_asset_validators.py`
4. Do not treat reviewer-notes edits as a semantic-validator expansion lane.

## Rollback Procedure

If a protected upload fails or pushes incorrect draft state:

1. Stop and do not mark ledger items closed.
2. Preserve evidence:
   - workflow run URL / run ID
   - relevant logs
   - screenshot artifact name if applicable
3. Revert only the draft-facing App Store Connect changes that were part of the
   failed run.
4. Fix the contract or metadata issue in a new PR.
5. Re-run protected dispatch only after the fix merges to an allowed ref.

## Design-System Guardrails

This rollout lane may reference the current design-system SoT, but it must not
change runtime composition.

Allowed:

- docs/parity/guard touches around App Store surfaces
- SoT references for tokens and design ownership

Not allowed:

- screenshot composition changes
- token semantic changes that alter visuals
- iOS/web component layout changes
- Figma/Canva-driven visual refresh by default

## Evidence And Closeout Rule

Implementation PR does not itself close rollout.

Rollout is considered closed only when all of the following are true:

1. implementation PR is merged
2. protected `upload_to_asc=true` dispatch succeeds on `main` or allowed release ref
3. protected `upload_app_privacy=true` dispatch succeeds on `main` or allowed release ref
4. evidence links are collected in repo docs or review artifact
5. a docs-only follow-up PR updates ledger and closeout references

Without protected draft-upload evidence, this lane remains activation-prep only.
