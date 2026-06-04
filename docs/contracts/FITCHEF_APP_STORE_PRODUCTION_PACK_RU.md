# FitChef RU App Store Production Pack

**Status:** RU localization production-pack contract
**Date:** 2026-06-04
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract opens the governed Russian localization lane for the FitChef
App Store production pack after the EN pack and Signal vs Noise GTM lane landed.

The pack is additive and non-runtime. It does not change live FitChef routes,
Fastlane metadata/upload surfaces, App Store Connect draft state, screenshot
binaries, preview binaries, or ES localization.

The RU pack mirrors the governed EN seven-shot sequence and stores localized
metadata, screenshot manifests, preview storyboard/script, upload checklist,
and approved source inventories under `/appstore/fitchef/ru-RU/...`.

## Scope

This contract defines and/or populates:

- `/appstore/fitchef/ru-RU/iphone-6.9/screenshots/`
- `/appstore/fitchef/ru-RU/iphone-6.9/preview/`
- `/appstore/fitchef/ru-RU/metadata/`
- deterministic tests for EN/RU App Store pack integrity
- backlog/governance sync after merged PR #1873

This contract explicitly does not add:

- runtime, backend, OpenAPI, DB, semantic cache, or GraphRAG changes
- frontend or iOS implementation changes
- Fastlane or App Store Connect upload automation
- final screenshot PNG/JPG exports
- final preview video binaries
- ES App Store localization assets

## Localization policy

The RU pack derives from the approved EN App Store production pack and keeps the
same product surfaces, shot order, safe-area baseline, source refs, and
canonical mascot asset keys.

RU copy must stay App Store-safe and wellness-safe:

- no professional-role framing
- no guaranteed outcomes
- no pricing, trial, discount, or subscription claims
- no fake UI, unsupported feature states, or submission-ready claims
- FitChef remains a friendly support cue over real PulsePlate product surfaces

## Acceptance checklist

- `ru-RU` App Store pack folder contract is populated
- metadata starter pack exists and stays within App Store practical limits
- screenshot manifest defines the same seven governed shots as EN
- preview storyboard/script exists and stays under 30 seconds
- icon/mascot source inventory references only canonical assets
- deterministic tests validate EN/RU pack structure, references, safety, and no-binary scope
- backlog marks PR #1873 landed and activates the RU localization lane
- no runtime/API/release-upload behavior changes are introduced

## Evidence anchors

- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md#localization-policy`
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md#localization-policy`
- `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md:1`
- `appstore/fitchef/ru-RU/metadata/app_store_metadata.json:1`
- `appstore/fitchef/ru-RU/metadata/icon_source_inventory.json:1`
- `appstore/fitchef/ru-RU/iphone-6.9/screenshots/shot_manifest.json:1`
- `appstore/fitchef/ru-RU/iphone-6.9/preview/storyboard.json:1`
- `tests/test_fitchef_app_store_pack.py:1`
