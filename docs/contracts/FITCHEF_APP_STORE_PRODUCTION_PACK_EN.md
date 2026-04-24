# FitChef EN App Store Production Pack

**Status:** PR-3 EN production pack
**Date:** 2026-03-13
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract opens the first governed App Store production-pack lane for
FitChef/PulsePlate after the foundation, visual contract, and mascot taxonomy
waves.

PR-3 is additive and remains non-runtime. It does not change live
`/api/v1/insight/fitchef*` routes, add Fastlane automation, or mix `RU` / `ES`
localization work into the first `EN` pack.

The pack is capture-ready and review-ready inside the repo. It stores governed
metadata, screenshot manifests, preview storyboard/script, upload checklist,
and approved source inventories anchored to real repo surfaces and canonical
FitChef/App Icon assets.

## Scope

This PR-3 contract defines and/or populates:

- `/appstore/fitchef/en-US/iphone-6.9/screenshots/`
- `/appstore/fitchef/en-US/iphone-6.9/preview/`
- `/appstore/fitchef/en-US/metadata/`
- deterministic tests for App Store pack integrity
- backlog/governance sync after merged PR-2

This PR-3 contract explicitly does not add:

- Fastlane or export automation
- final screenshot PNG exports generated from a simulator/device pipeline
- final preview video binaries
- `RU` or `ES` App Store localization assets
- backend/frontend runtime changes

## Production-pack policy

### Source order

Approved source order for this lane:

1. `docs/contracts/*` FitChef contracts
2. token/runtime SoT already on `main`
3. canonical FitChef/App Icon assets already governed by PR-2
4. review-ready App Store metadata and capture manifests in `/appstore`

### Truthfulness and safety

- Screenshot manifests must point to real product surfaces already represented
  in repo code/docs.
- Copy must remain App Store-safe and wellness-safe.
- The pack must not invent fake UI states or unverifiable claims.
- If a screenshot or preview export does not yet exist as a reviewed repo
  output, the pack stores a capture-ready manifest instead of a fake binary.

## Pack contents

### Metadata

`/appstore/fitchef/en-US/metadata/` contains:

- `app_store_metadata.json`
- `icon_source_inventory.json`
- `source_of_truth.md`
- `upload_checklist.md`

### Screenshots

`/appstore/fitchef/en-US/iphone-6.9/screenshots/` contains:

- `README.md`
- `shot_manifest.json`

The manifest must define exactly seven `EN` launch shots aligned with the
PR-1 visual contract.

### Preview

`/appstore/fitchef/en-US/iphone-6.9/preview/` contains:

- `README.md`
- `storyboard.json`
- `preview_script.md`

The preview pack remains script/storyboard only in PR-3. Final video binary
export is intentionally outside this governed repo lane until a deterministic
capture/export path exists.

## Asset policy for PR-3

- `FitChef` remains the stable default mascot asset key.
- Only canonical PR-2 FitChef-prefixed variants may be referenced.
- Only canonical `AppIcon-*` files from the governed asset catalog may be
  referenced.
- Dirty local asset diffs outside the PR-3 worktree are not promoted blindly.
- If an asset candidate is not already canon-clean, it must be deferred instead
  of forced into the pack.

For this PR-3 lane, the approved source inventory stays on the canonical assets
already present on `main`; no extra binary promotion is required for pack
integrity.

## Acceptance checklist

- `EN` App Store pack folder contract is populated
- metadata starter pack exists and stays App Store-safe
- screenshot manifest defines seven governed shots
- preview storyboard/script exists and stays under 30 seconds
- icon/mascot source inventory references only canonical assets
- deterministic tests validate pack structure and references
- backlog reflects merged PR-2 and active PR-3
- no runtime/API behavior changes are introduced

## Evidence anchors

- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md:76`
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md:219`
- `docs/contracts/FITCHEF_MASCOT_ASSET_TAXONOMY.md:11`
- `appstore/fitchef/en-US/metadata/app_store_metadata.json:1`
- `appstore/fitchef/en-US/metadata/icon_source_inventory.json:1`
- `appstore/fitchef/en-US/iphone-6.9/screenshots/shot_manifest.json:1`
- `appstore/fitchef/en-US/iphone-6.9/preview/storyboard.json:1`
- `tests/test_fitchef_app_store_pack.py:1`
