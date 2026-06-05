# FitChef ES App Store Production Pack

**Status:** ES localization production-pack contract
**Date:** 2026-06-05
**Owner:** @katsiaryna_kavaleuskaya

## Summary

This contract opens the governed Spanish localization lane for the FitChef App
Store production pack after the EN pack and RU localization pack landed.

The pack is additive and non-runtime. It does not change live FitChef routes,
Fastlane metadata/upload surfaces, App Store Connect draft state, screenshot
binaries, preview binaries, or protected release evidence.

The ES pack mirrors the governed EN/RU seven-shot sequence and stores localized
metadata, screenshot manifests, preview storyboard/script, upload checklist,
and approved source inventories under `/appstore/fitchef/es-ES/...`.

## Scope

This contract defines and/or populates:

- `/appstore/fitchef/es-ES/iphone-6.9/screenshots/`
- `/appstore/fitchef/es-ES/iphone-6.9/preview/`
- `/appstore/fitchef/es-ES/metadata/`
- `/appstore/fitchef/localization_qa/cross_locale_review_prep.md`
- deterministic tests for EN/RU/ES App Store pack integrity
- backlog/governance sync after merged PR #1879 and PR #1883

This contract explicitly does not add:

- runtime, backend, OpenAPI, DB, semantic cache, or GraphRAG changes
- frontend or iOS implementation changes
- Fastlane or App Store Connect upload automation
- final screenshot PNG/JPG exports
- final preview video binaries
- protected App Store submission evidence

## Localization policy

The ES pack derives from the approved EN and RU App Store production packs and
keeps the same product surfaces, shot order, safe-area baseline, source refs,
and canonical mascot asset keys.

ES copy must stay App Store-safe and wellness-safe:

- no professional-role framing
- no guaranteed outcomes
- no pricing, trial, discount, or subscription claims
- no fake UI, unsupported feature states, or submission-ready claims
- food recipe wording is allowed only in food-planning context
- medicine or prescription framing remains blocked
- FitChef remains a friendly support cue over real PulsePlate product surfaces

## Acceptance checklist

- `es-ES` App Store pack folder contract is populated
- metadata starter pack exists and stays within App Store practical limits
- screenshot manifest defines the same seven governed shots as EN/RU
- preview storyboard/script exists and stays under 30 seconds
- icon/mascot source inventory references only canonical assets
- cross-locale QA prep flags EN/RU/ES rendered-review risks without upload authority
- deterministic tests validate EN/RU/ES pack structure, references, safety, and no-binary scope
- backlog marks PR #1879 and PR #1883 landed and activates the ES localization lane
- no runtime/API/release-upload behavior changes are introduced

## Evidence anchors

- `docs/contracts/FITCHEF_INITIATIVE_FOUNDATION.md#localization-policy`
- `docs/contracts/FITCHEF_APP_STORE_VISUAL_CONTRACT.md#localization-policy`
- `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_EN.md:1`
- `docs/contracts/FITCHEF_APP_STORE_PRODUCTION_PACK_RU.md:1`
- `appstore/fitchef/es-ES/metadata/app_store_metadata.json:1`
- `appstore/fitchef/es-ES/metadata/icon_source_inventory.json:1`
- `appstore/fitchef/es-ES/iphone-6.9/screenshots/shot_manifest.json:1`
- `appstore/fitchef/es-ES/iphone-6.9/preview/storyboard.json:1`
- `appstore/fitchef/localization_qa/cross_locale_review_prep.md:1`
- `tests/test_fitchef_app_store_pack.py:1`
