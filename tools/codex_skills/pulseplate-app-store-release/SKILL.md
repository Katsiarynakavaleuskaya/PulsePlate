---
name: pulseplate-app-store-release
description: Handle PulsePlate App Store release work covering Fastlane metadata, screenshot packs, review evidence, and protected rollout notes without bypassing coordinator-first policy.
---

# PulsePlate App Store Release

## When to use

- Preparing or updating App Store metadata under `ios/fastlane/metadata/`.
- Working on screenshot packs, App Store Connect upload flow, or App Privacy assets.
- Reviewing release evidence, rollback notes, or protected upload readiness for iOS release ops.

## Inputs required

- Release surface in scope (`metadata`, `screenshots`, `app_privacy`, `review_notes`, or `evidence`).
- Candidate file paths or workflow paths being changed.
- Expected release outcome (`draft-ready`, `validation-only`, or `protected-upload follow-up`).

## Procedure (commands)

1. Load release-policy context:

   ```bash
   rg -n -C 2 "App Store|Fastlane|release" ios/AGENTS.md
   rg -n -C 2 "Validation-only|Protected upload|App Privacy|review information|rollback" docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md
   ```

2. Verify Fastlane and validator surfaces before editing:

   ```bash
   rg -n "upload_metadata|upload_screenshots|upload_app_privacy|review_information" ios/fastlane
   pytest -q tests/test_ios_appstore_assets_workflow_contract.py
   pytest -q tests/test_ios_appstore_asset_validators.py
   ```

3. Keep rollout claims fail-closed:

   ```bash
   python3 scripts/orchestration/check_preflight.py
   python3 scripts/orchestration/check_agent_consistency.py
   pre-commit run --all-files
   make verify
   ```

## Output format

- `Release surface`: exact App Store surface touched.
- `Evidence`: validator/tests/workflow proof and protected-run dependencies.
- `Risk notes`: reviewer impact, secret/environment dependency, rollback note.
- `Follow-up`: whether protected upload remains operator-only after merge.

## Guardrails

- Do not bypass coordinator-first routing or convert this skill into release authority.
- Do not claim App Store rollout completion without protected-run evidence.
- Do not mix backend billing truth or entitlement logic into iOS/App Store asset work.
- Keep protected secrets and upload credentials outside repo branches and worktrees.

## SoT links

- `AGENTS.md`
- `ios/AGENTS.md`
- `docs/runbooks/IOS_APPSTORE_ASSETS_ROLLOUT.md`
- `ios/fastlane/Fastfile`
- `tests/test_ios_appstore_assets_workflow_contract.py`
- `tests/test_ios_appstore_asset_validators.py`
