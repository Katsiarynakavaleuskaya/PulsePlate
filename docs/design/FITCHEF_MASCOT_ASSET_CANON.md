# FitChef Mascot Asset Canon

Status: `Seed Pack v1 + Public Demo Pack v1 + Web Hero Scenario v1`
Owner: `@katsiaryna_kavaleuskaya`
Scope: `Repo brand asset canon for FitChef mascot/logo references`

## Summary

This document locks the first canonical FitChef mascot seed pack that can be
reused by iOS, web, and Figma reference workflows without treating Xcode asset
catalogs as the source of truth.

Current source-of-truth pack:

- `frontend/src/assets/brand/fitchef-portrait-neutral-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-wink-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-thinking-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-sleepy-v1.png`
- `frontend/src/assets/brand/fitchef-portrait-surprised-v1.png`
- `frontend/src/assets/brand/fitchef-onboarding-welcome-v1.png`
- `frontend/src/assets/brand/fitchef-hero-stretch-v1.webp`
- `frontend/src/assets/brand/fitchef-public-demo/v1/`

## Canonical Rules

1. Repo asset files are the current mascot source of truth for PR4.
2. `ios/PulsePlate/Assets.xcassets/` is a derived runtime mirror, not the
   authoring lane.
3. Figma remains a design/reference lane for placement and composition, not the
   master asset lane for these mascot PNGs.
4. Legacy web aliases remain valid for current consumers:
   - `frontend/src/assets/brand/fitchef-static.png`
   - `frontend/src/assets/brand/fitchef-wink.png`

## Default Runtime Mapping

### Web

- Default mascot alias: `frontend/src/assets/brand/fitchef-static.png`
- Existing wink alias: `frontend/src/assets/brand/fitchef-wink.png`
- New PR4 source pack is additive and should be used for future website hero,
  onboarding, and campaign layouts.

### iOS

- Default mascot alias: `ios/PulsePlate/Assets.xcassets/FitChef.imageset`
- Named variants:
  - `FitChefWink.imageset`
  - `FitChefThinking.imageset`
  - `FitChefSleepy.imageset`
  - `FitChefSurprised.imageset`
  - `FitChefOnboardingWelcome.imageset`

## Variant Contract

| Variant | Canonical file | Intended usage |
| --- | --- | --- |
| neutral | `frontend/src/assets/brand/fitchef-portrait-neutral-v1.png` | default UI mascot / baseline portrait |
| wink | `frontend/src/assets/brand/fitchef-portrait-wink-v1.png` | positive feedback / playful UI states |
| thinking | `frontend/src/assets/brand/fitchef-portrait-thinking-v1.png` | reflection / planning / question states |
| sleepy | `frontend/src/assets/brand/fitchef-portrait-sleepy-v1.png` | rest / night / calm guidance states |
| surprised | `frontend/src/assets/brand/fitchef-portrait-surprised-v1.png` | alert / attention / highlight states |
| onboarding-welcome | `frontend/src/assets/brand/fitchef-onboarding-welcome-v1.png` | onboarding hero / welcome card / promo scenes |

## Mutation Policy

Allowed:

- add new named variants with explicit `-vN` suffixes
- derive runtime copies for iOS/web from this pack
- update docs that map usages

Forbidden:

- overwrite a locked variant in place without version bump
- use generic names like `Image.imageset` for mascot variants
- use filenames with Finder collision suffixes like `image 1.png`
- treat Figma export/import as the mascot source of truth

## Figma Policy

Figma consumers must reference this seed pack when composing screens or
marketing layouts. Any future Figma sync remains `reference_only` until a
follow-up PR promotes a governed export/import contract.

## Public Demo Photographic Pack v1

The public demo pack promotes the complete owner-approved photographic family
for the shared Web `FitChefValueDemo`. The Human Product Owner approved these
assets for PulsePlate Web use and later governed iOS reuse. That approval is
project-use authority only; it is not deployment, release, App Store, payment,
entitlement, or paid-Web execution authority.

Design provenance:

- Authoring source: Open Design project
  `er-ios-1-fitchef-support-choice-clean`.
- Terminal Open Design source SHA-256:
  `38e8154dfa0b581c9bc214f67bd4b507117c80b1f0e727b5b43b99c2c06dc182`.
- Terminal Product Design QA report SHA-256:
  `8d940c2b83ef22ca6e6120496c3da288ab026c73fa06798eb825e68dff630d20`.
- Terminal evidence manifest SHA-256:
  `5f1903fb4fc0d492c60654f0d0264b77deda5c81cb54dfeb52072d795497f06b`.
- sRGB promotion proof SHA-256:
  `9c9d9a5627026fa643b3e463774623bc6becf23cf2872dde914103aab1de00e4`.
- WebP derivative QA manifest SHA-256:
  `83337176871bbb8adc906753a43aeec7cadc11b7b6139f9eb71be39dfaf62d37`.
- Human Product Owner decision on 2026-08-31: Web uses the reviewed WebP
  derivatives; the terminal PNG family remains Open Design and future iOS
  authority.
- QA result: `PASSED / PASS_TO_COORDINATOR`, with no remaining
  `P0`, `P1`, `P2`, or `P3` finding in that terminal design epoch.

The Open Design HTML, flattened locale canvases, contact sheet, and QA evidence
remain local review artifacts. They are not runtime assets. Runtime ownership
starts only at the repo paths below.

### Exact asset inventory

| Runtime path under `frontend/src/assets/brand/fitchef-public-demo/v1/` | Open Design PNG SHA-256 | Runtime WebP SHA-256 | Pixels | Web delivery |
| --- | --- | --- | --- | --- |
| `activity-palette/endurance.webp` | `687a5a49c8fe321990f036cb6efdd1889bd08c5ff38983cf6eda94a3546bcda2` | `09d238901bf22f79525c1b597e1e6cf9b5ce2ceb602f8fa82e9439df7bf998f0` | `410x512 RGB` | q96, 88776 B, resized-reference PSNR 40.3768 dB, sRGB ICC |
| `activity-palette/movement-everyday-fitness.webp` | `d0b9be1359c0f56c6fd6dfffe849c4f6de2c699c8acfe8fb204f2a890e2ec1d5` | `7472fb52b167bed135a76e95f40d681e9962c515d9038a8158611683f436a620` | `410x512 RGB` | q96, 94298 B, resized-reference PSNR 38.0093 dB, sRGB ICC |
| `activity-palette/strength-power.webp` | `0e04ea90a7d657c9c7ae03f793c2fb2da46ae418b682ed67e882401f0c08381c` | `4a154769734dedbbe2ad7fb250e45a371071316971bc27761aee62611c3758d0` | `410x512 RGB` | q96, 33474 B, resized-reference PSNR 44.0667 dB, sRGB ICC |
| `activity-palette/team-combat.webp` | `389fba16715bd7b1e16650feb87ab7b274a6b5baebb57a18359e8dc0337440a7` | `80627dd04d4d1ac099e826741e1a10d099ab254bc4e49b45c47b8ae6eb75be8d` | `410x512 RGB` | q96, 65154 B, resized-reference PSNR 41.6872 dB, sRGB ICC |
| `daily-plate-a-salmon-1024.webp` | `5bb635cdf4a86359d2763235dd31e7ef8f7d5b8c5776826823c5ff0a63806331` | `ae1410aeaabf59389ef244cab577ad9d7a82ef5ffc4338ac41f256a034be2149` | `1024x1024 RGB` | q96, 245002 B, PSNR 40.9164 dB, sRGB ICC |
| `food-context/food-context-ingredients-at-home.webp` | `69bdd1f50666964308e4a89494095dde5b86fd906b04c6824f02a9b7ebbe67b0` | `7759e414df893aea1261e69a84228ebc144f458eeebbee344fb2dd8041b45dfd` | `410x512 RGB` | q96, 64556 B, resized-reference PSNR 41.2113 dB, sRGB ICC |
| `food-context/food-context-meal-photo.webp` | `12501b21584f9369574630268489b40430b643a97aa22d69fe61b4a16a7846ba` | `579e19094f5b5b3e33df260d7c71199b7c665cf77f7252a61a3b2383fb3fa2a1` | `410x512 RGB` | q96, 76426 B, resized-reference PSNR 40.3378 dB, sRGB ICC |
| `food-context/food-context-restaurant-chef.webp` | `ae932ce5aeb858cb86a9ed98694cd55292495f450ced6c60118c233da86adab4` | `09dc0969eb4a9fc6e9cf469b5f3a83a075cbad298101ab26602d0ec2ed5725c0` | `410x512 RGB` | q96, 64116 B, resized-reference PSNR 40.6184 dB, sRGB ICC |
| `food-context/food-context-shopping-stores.webp` | `2bd534f149fd0804986800ae939f3b7bdbf56ea52d2946f4a87c4a2d6ba113a5` | `214a0dcbcfb11caa97a645e1b9b3b66e16da3fc659b0c71c08191c8873441239` | `410x512 RGB` | q96, 96778 B, resized-reference PSNR 36.4094 dB, sRGB ICC |
| `vip/fitchef-vip-editorial-owner-approved-logo-v2.webp` | `14223bd347c5b81f58a90da28fdf4a8243b90b9b0b156d8a6caa555144309d64` | `324d63729b745d17a0a7706a55bd74979a40a7db8820958a024e4ad73000d8f7` | `1122x1402 RGB` | q96, 368238 B, PSNR 44.5484 dB, sRGB ICC |
| `weekly-planning-a-meal-grid-1024.webp` | `d6cff5674fb8b74cbae348c88f6bf41682e0ea7a73c961d69cfadb76ec75a46a` | `678a55fd171bd40112377e160794019112dee3c1f8e6cb0d29c99f6058380d8a` | `1024x1024 RGB` | q96, 332828 B, PSNR 39.6382 dB, sRGB ICC |
| `weekly-planning-b-notebook-1024.webp` | `1943c4fd28fef04b697c243be450a3c0e74c2a8dd039b1828402394c14db0e40` | `8d8f4d53b3f55e323a346520313d5e98021aca94734117e855d1d9b4953fc73d` | `1024x1024 RGB` | q96, 376662 B, PSNR 39.1452 dB, sRGB ICC |

The eight activity and food-context images are deterministic 410x512 card-sized
derivatives; their PSNR is measured against a Lanczos 410x512 resize of the
unchanged Open Design PNG. The four planning/VIP derivatives preserve their
1024+ source dimensions. All twelve carry the frozen explicit sRGB ICC profile,
stay below the repository's 500 KiB added-file limit, and reduce the complete
Web pack from 24875178 to 1906308 bytes. The card-only subset is 583578 bytes,
down from 2763534 bytes in the first full-resolution Web promotion. The original
PNG bytes and their source hashes remain the Open Design and future iOS
authority. The existing
`fitchef-portrait-neutral-v1.png` remains the neutral H1 mascot and is not a
thirteenth public-demo derivative.

## IOS-REL-2 V5 iOS Runtime Derivative Pack

Status: `IMPLEMENTATION_REQUIRED / PENDING NATIVE V1`

The Human Product Owner selected Candidate A (`Home / BMI / Today / Progress /
Profile`) with the exact outcome `APPROVE_A` after reviewing the immutable V5
navigation epoch. The Open Design epoch digest is
`05eed1a9b01f4b92c3961690b114c08158939ff8b8bdfafde329b0cc4d8437fc`;
the separate human-decision receipt digest is
`604e3553fe9e574f870aedae9fd298048dd0d22c222b43413d1171a70bd04d03`.
Those receipts select the following bounded ten-image set without modifying the
Open Design sources or promoting the V5 HTML/WebP review package as runtime
truth.

The seven FitChef sources belong to the Open Design project
`ds-nutrition-ai-assistant-design-system`. The three photographic PNG originals
belong to the already owner-approved Public Demo Photographic Pack v1 and remain
the iOS source authority; the WebP derivatives listed above are not derivative
inputs for this pack.

The Open Design authoring model has two complementary project pages/surfaces:

- the Design System page (`ds-nutrition-ai-assistant-design-system`, including
  `kit.html` and `assets/fitchef/`) owns composition, tokens, structural visual
  language, and the FitChef family;
- the approved Web Marketing page
  (`er-ios-1-fitchef-support-choice-clean/fitchef-public-web-demo-pr2.html` and
  its `pr2-public-demo` originals) owns the photographic lifestyle language
  deliberately planned for governed iOS reuse.

Neither page substitutes for the other. iOS combines the Design System's
FitChef identity with only the explicitly selected Marketing-page photographs;
it must not fall back to the older schematic chart/icon imagery when an approved
photographic source is listed below.

| Approved source identity | Source PNG SHA-256 | iOS runtime candidate | Output SHA-256 | Pixels / bytes | Bounded use |
| --- | --- | --- | --- | --- | --- |
| `assets/fitchef/onboarding/assets_FITCHEF_ONBOARDING_WELCOME_V1.png` | `7e37a0a90772a5423f546948e94d36a876a30877ed8c80b336b2f291dd07eb98` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@3x.png` | `279081197210c7dc66c16234ce0eec6cf7f490a134176af894ab56f0cca67de5` | `384x576 RGB`, `182824 B` | compact/narrow free-ready Home hero |
| `assets/fitchef/actions/assets_FITCHEF_ACTION_PROGRESS_TRACKING_V1.png` | `38b9604a3a27f229535c948e0e5e8e22fe2ae185e0b585c965b040b330d4d65f` | `ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@3x.png` | `8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a` | `384x576 RGB`, `128577 B` | compact Progress summary; future wide Weekly row only after the navigation carrier sync |
| `assets/fitchef/actions/assets_FITCHEF_ACTION_NUTRITION_PLATE_V1.png` | `e73bcbf5fd3f2f9af60e89e93db79570e1be89fac7213bdb39b131adc881955b` | `ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@3x.png` | `da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80` | `384x576 RGB`, `124822 B` | Today plate-photo medallion, replacing the generic duplicate mascot |
| `assets/fitchef/onboarding/assets_FITCHEF_ONBOARDING_PROFILE_SETUP_V1.png` | `3ae7e0265de31221e6b105b7e0592f1a2b510eebde3e876432cedd33dd853b81` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@3x.png` | `b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0` | `432x576 RGB`, `212832 B` | single bounded Profile illustration |
| `assets/fitchef/portraits/assets_FITCHEF_PORTRAIT_HAPPY_V1.png` | `3f5cd3a5084f1b8f8e1cdec2e3ca2e492fd14cb03f97e45d0c2e6401c8033697` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@3x.png` | `a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445` | `576x576 RGB`, `264170 B` | regular-width free-ready Home hero |
| `assets/fitchef/portraits/assets_FITCHEF_PORTRAIT_ENCOURAGING_V1.png` | `e61dfecab8d092374d61ddfd535fec76d2d74652a2f3dac6194df44ae47ac9fb` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@3x.png` | `1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c` | `384x576 RGB`, `106863 B` | sole paid-ready Home hero; module cards remain system glyphs |
| `assets/fitchef/portraits/assets_FITCHEF_PORTRAIT_THINKING_V1.png` | `41f557ccf00663035551e9c0f5c535cd772c47e7c5efb1c81297435d076ff98e` | `ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@3x.png` | `66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c` | `384x576 RGB`, `135780 B` | BMI support medallion |
| `pr2-public-demo/daily-plate-a-salmon-1024.png` | `5bb635cdf4a86359d2763235dd31e7ef8f7d5b8c5776826823c5ff0a63806331` | `ios/PulsePlate/Resources/Images/photo-daily-plate-salmon-v1.jpg` | `666651b6caf3b2c4b3e3e6eda1243caf773ad97bdb2cb8a3de49251bdf4314e2` | `768x768 RGB`, `183118 B` | Today plate context |
| `pr2-public-demo/activity-palette/endurance.png` | `687a5a49c8fe321990f036cb6efdd1889bd08c5ff38983cf6eda94a3546bcda2` | `ios/PulsePlate/Resources/Images/photo-activity-endurance-v1.jpg` | `5108de91fce089419785fbb62c3318bb943ce3319b1f4bfd130baf3a99344cc9` | `640x800 RGB`, `196028 B` | regular-width Progress context |
| `pr2-public-demo/activity-palette/movement-everyday-fitness.png` | `d0b9be1359c0f56c6fd6dfffe849c4f6de2c699c8acfe8fb204f2a890e2ec1d5` | `ios/PulsePlate/Resources/Images/photo-activity-movement-everyday-fitness-v1.jpg` | `27b1c0beabdd428cb3651906ea45064c007562ba8d92f0b973d499a585183a25` | `640x800 RGB`, `208127 B` | BMI movement context |

The seven mascot runtime identities are the semantic catalog keys in the
taxonomy contract. The table above binds their approved 3x payloads. Each
bucket also contains the following 1x/2x rendition derived from that exact
3x payload, without cropping, compositing, or new visual content:

| Approved source identity | Source PNG SHA-256 | iOS runtime candidate | Output SHA-256 | Pixels / bytes | Bounded use |
| --- | --- | --- | --- | --- | --- |
| `FitChefOnboardingWelcome @3x` | `279081197210c7dc66c16234ce0eec6cf7f490a134176af894ab56f0cca67de5` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@1x.png` | `205cb0d86cbb5b2b2592a5997ea97b832267da637657cd51146f9e171f378813` | `128x192 RGB`, `29590 B` | 1x density; same approved owner/composition |
| `FitChefOnboardingWelcome @3x` | `279081197210c7dc66c16234ce0eec6cf7f490a134176af894ab56f0cca67de5` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingWelcome.imageset/fitchef-onboarding-welcome@2x.png` | `0cab5104573f747d30aa4e6442662fe5cb08d49df0550fc7f3cacbe8add3bae3` | `256x384 RGB`, `95092 B` | 2x density; same approved owner/composition |
| `FitChefActionProgressTracking @3x` | `8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a` | `ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@1x.png` | `32f1a4f09ed3f29d4b113dc11df586c3ee981c41ba43729f34b45057af5cf2f2` | `128x192 RGB`, `27791 B` | 1x density; same approved owner/composition |
| `FitChefActionProgressTracking @3x` | `8d26d8d8464fdaa764abe439694ecf9fd06c9f937d82a4a8d57f3ecaa02cf46a` | `ios/PulsePlate/Assets.xcassets/FitChefActionProgressTracking.imageset/FitChefActionProgressTracking@2x.png` | `26eb6b2be8023042fecf0b9c0c8ef2f2a594ac8867bb7e624fbb0397c3a08b1f` | `256x384 RGB`, `76438 B` | 2x density; same approved owner/composition |
| `FitChefActionNutritionPlate @3x` | `da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80` | `ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@1x.png` | `c3b40ff2117153a9edfd67d017c6e3cb9713fbe3e750cd38c1bedb79f146b5e6` | `128x192 RGB`, `24137 B` | 1x density; same approved owner/composition |
| `FitChefActionNutritionPlate @3x` | `da89403f0fec0a3c183cdd7218a1f37996365c6f6c35104ff1a528eb7bceab80` | `ios/PulsePlate/Assets.xcassets/FitChefActionNutritionPlate.imageset/FitChefActionNutritionPlate@2x.png` | `7dd2b312029b4abf87376774903fab95e3da7d839e640148ecc073edbe2b6fee` | `256x384 RGB`, `70316 B` | 2x density; same approved owner/composition |
| `FitChefOnboardingProfileSetup @3x` | `b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@1x.png` | `50bbe535174288033c40ccc40d6afc682ade57516df4ed861576830ea5e52810` | `144x192 RGB`, `28217 B` | 1x density; same approved owner/composition |
| `FitChefOnboardingProfileSetup @3x` | `b0e8f856e65c7c78d7f5ae000d30e3c56397d2bcf10ef6b3fda0e692f0d5fbd0` | `ios/PulsePlate/Assets.xcassets/FitChefOnboardingProfileSetup.imageset/FitChefOnboardingProfileSetup@2x.png` | `a7a0f18d110a69e519cf406b91c73ca034ac78741d0cf0aec71b1e21bb0d4278` | `288x384 RGB`, `106835 B` | 2x density; same approved owner/composition |
| `FitChefPortraitHappy @3x` | `a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@1x.png` | `3c319735caeb647c8cb9ae705f13f7d9fd3804afbcd4065f9a9ce4deef6efe05` | `192x192 RGB`, `42888 B` | 1x density; same approved owner/composition |
| `FitChefPortraitHappy @3x` | `a84aa312d47edf06316f0d47e60fefb99d12a4c5d6fad18595978a3eabf4c445` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitHappy.imageset/FitChefPortraitHappy@2x.png` | `e205fef40ce4a9842ae8556dcb7b1a559a299f938917592e676fefbe6bae4eac` | `384x384 RGB`, `139532 B` | 2x density; same approved owner/composition |
| `FitChefPortraitEncouraging @3x` | `1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@1x.png` | `ab8d924717dce3e23edd87083c81e50c1d21f57fd4330b7130a875e08b6a157d` | `128x192 RGB`, `22596 B` | 1x density; same approved owner/composition |
| `FitChefPortraitEncouraging @3x` | `1399e0735f523bd401f6bb96ecd3edf07c377abe3318c1aa06938b58b542c35c` | `ios/PulsePlate/Assets.xcassets/FitChefPortraitEncouraging.imageset/FitChefPortraitEncouraging@2x.png` | `94da68ed2a9ddd9d30affe276b55c57d6ef82a42bacf944a36067a6f81e734b9` | `256x384 RGB`, `62357 B` | 2x density; same approved owner/composition |
| `FitChefThinking @3x` | `66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c` | `ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@1x.png` | `76356ff16aa6f897ef90bfd5c1454eb1dd2df6d29647edc4bd3c597857bafad8` | `128x192 RGB`, `28992 B` | 1x density; same approved owner/composition |
| `FitChefThinking @3x` | `66d8d84e6b309beaba6fdac6c4b008a366c0aef9659c337ae3fabc80e0b1e33c` | `ios/PulsePlate/Assets.xcassets/FitChefThinking.imageset/fitchef-thinking@2x.png` | `2481c99f7a2e2258bba95742b39aaddf22d9dcf6f8b5c0cb39cbf57d40e856a1` | `256x384 RGB`, `79515 B` | 2x density; same approved owner/composition |

Deterministic derivative contract:

- Encoder: Pillow `12.3.0`, libjpeg `6.2`, zlib
  `1.3.1.zlib-ng`, `Image.Resampling.LANCZOS`.
- FitChef PNGs: apply EXIF orientation, require the exact source hash,
  dimensions, `RGB`, and no alpha, then use `ImageOps.contain` within
  `576x576`; save full-color PNG with `optimize=True` and
  `compress_level=9`. Portrait sources preserve their complete aspect ratio;
  no derivative-stage crop, padding, compositing, or palette quantization is
  permitted.
- Photographs: apply EXIF orientation and the same source admission, then use
  `ImageOps.fit` with `(0.42, 0.50)` for salmon, `(0.50, 0.36)` for endurance,
  and `(0.50, 0.42)` for movement; save baseline, non-progressive JPEG at
  `quality=92`, `subsampling=0`, and `optimize=True`.
- The catalog contains 21 PNGs for seven semantic variants; the three JPEGs
  remain unchanged. The 1x/2x PNGs are Lanczos downscales to one-third/two-thirds
  of the approved 3x geometry, using the same encoder and frozen ICC payload.
  The longest intrinsic dimension is 192 points at all three densities.
  No appearance-specific artwork is introduced; Light and Dark use the same
  original-color image. The seven former loose mascot files are removed from
  Resources/Images so there is no second runtime packaging owner.
- All 24 outputs embed only the frozen `588`-byte sRGB ICC payload with
  SHA-256
  `86453c6e1ee138f0be42c75ab37a6d73422df68e4767da1b1d3ae6c05aa20e39`.
  EXIF, XMP, IPTC, GPS, comments, textual PNG chunks, timestamps, and source
  DPI metadata are absent.
- Two clean generations on the recorded toolchain produced byte-identical
  output hashes. Every file is below the strict `512000 B` ceiling; aggregate
  candidate size is `2577437 B` across the 24 files.

Repository tests independently hash and inspect all 24 checked-in runtime
derivatives. They also verify all seven Contents.json inventories, semantic
bundle lookups at the native destination scale in Light/Dark, and absence of
loose mascot copies. Xcode may thin installed catalogs to the device scale;
repository checks cover all three densities independently of that thinning.
They verify the exact output bytes, decoded geometry/color, frozen
ICC payload, PNG/JPEG encoding structure, and forbidden-metadata absence. The
external Open Design/Public Demo source bytes remain in the immutable planning
archive: their hashes are provenance recorded here and verified during the
governed derivative-generation step, not a claim that those external originals
are checked into or re-hashed by the iOS unit-test bundle.

SwiftUI owns the V5 focal crop through bounded `scaledToFill` containers. The
files must not become tab icons, be tinted, stretched, or replace native SF
Symbols. F12 remains `REFERENCE_ONLY / NON-RUNTIME` and contributes no iOS
asset. The pack adds no App Icon, Fastlane, screenshot export, privacy,
entitlement, navigation-inventory, CTA, backend, OpenAPI, or token authority.
The same bounded parity fix removes the visible Profile API/paid-tier wording
from EN/RU/ES and uses the approved system glyphs for Language, Privacy, and
Legal without changing profile fields or persistence behavior.

Native iPad inspection also bounds the existing PlateSegments drawing canvas
to 280 points at its PlateView owner so the sectors and background stay
concentric. The ring's completion/VoiceOver keys exist in EN/RU/ES and inherit
the app-selected locale. These are presentation corrections, not new chart
data, nutrient calculations, shared primitives, or action behavior.

Native V1 Product Owner review on 2026-09-04 supersedes only the V5 Today
supporting sentence after the exact SwiftUI render exposed it as decorative and
non-actionable. The runtime copy is frozen as:

- EN: `Visualize your plate. Log a meal. Explore the breakdown.`
- RU: `Визуализируйте свою тарелку. Добавьте приём пищи. Посмотрите состав.`
- ES: `Visualiza tu plato. Registra una comida. Consulta la composición.`

The immutable V5 epoch remains unchanged. This bounded copy correction describes
the existing visualization, Add Meal, and View Details actions; it grants no
nutrition calculation, camera/CV, photo-generation, or client-authority change.

The same native review rejects `Segment balance` and `Segment progress` as
internal implementation vocabulary. The current chart renders vegetables,
protein, carbohydrates, and fats; it does not yet prove a micronutrient dataset.
Until a backend/OpenAPI contract adds that data, runtime wording stays factual:

- EN: `Track daily nutrition completion and nutrient balance.` /
  `Nutrient progress`
- RU: `Отслеживайте дневное питание и баланс питательных веществ.` /
  `Прогресс по питательным веществам`
- ES: `Sigue tu alimentación diaria y el equilibrio de nutrientes.` /
  `Progreso de nutrientes`

This wording must not be promoted to `micro- and macronutrient` until the
underlying canonical response actually carries both classes.
The Swift Charts semantic labels use localized `Nutrient category` and
`Completion` equivalents in EN/RU/ES, so VoiceOver does not reintroduce the
internal English `Segment` vocabulary after the visible copy is corrected.

These deterministic files are still candidates until exact-head Release bundle
lookup and native simulator review prove the Home, BMI, Today, Progress, and
Profile compositions. This record is neither Human V1 `GO` nor `SUBMIT_READY`.

## Public Web Hero Scenario v1

The public Web Hero uses a separate photographic situation from the static VIP
editorial. The Human Product Owner selected the gentle stretch composition on
2026-09-02 after reviewing actual `1440`, `768`, and `320` browser previews.
This choice keeps the Hero relevant to BMI and movement while avoiding a weight
number, body judgment, medical framing, or anthropomorphic exercise.

Identity and generation provenance:

- Approved real-cat identity reference SHA-256:
  `3c6a588b776c12fce79f7a6ba2552a6b5efec16e1ab6e0ccb64e052141c98990`.
- Selected identity-preserving source PNG SHA-256:
  `e1b1a062d9df2f40d74afd73faa404c2d8661bd288ed3034940e22523c1135c9`.
- The selected source was produced with the built-in image-generation tool from
  the approved identity reference and retained as gitignored design evidence.
- Open Design, iCloud, Figma, and the approved VIP source were not modified by
  this promotion.

Runtime contract:

| Runtime path | Selected source PNG SHA-256 | Runtime WebP SHA-256 | Pixels | Web delivery |
| --- | --- | --- | --- | --- |
| `frontend/src/assets/brand/fitchef-hero-stretch-v1.webp` | `e1b1a062d9df2f40d74afd73faa404c2d8661bd288ed3034940e22523c1135c9` | `7ff3adc9f4121112cf6edfc9b0b664acdb0fa83cc425645aa913a249c994660c` | `1122x1402 RGB` | Pillow 12.3.0, q96, method 6, 307676 B, PSNR 45.2109 dB, frozen 588-byte sRGB ICC |

Usage and authority:

- `editorial-real`: the public Web Hero may use the selected full-frame
  photographic scenario as static acquisition context.
- `ui-flat`: the Daily/Weekly interaction keeps the existing compact
  illustrated neutral guide; the photographic Hero does not enter the
  `FitChefMascot` variant enum.
- The existing VIP asset
  `vip/fitchef-vip-editorial-owner-approved-logo-v2.webp` remains unchanged and
  continues to own the Personal Nutrition Guide story.
- The Hero image is code-native content inside a semantic `figure`; it creates
  no route, calculation, API call, analytics event, payment action, live-AI
  behavior, or availability claim.
- Only the tracked WebP has Web runtime authority. The generated source and
  rejected scale alternative remain local design evidence.

### Frozen locale design authority

The first runtime promotion remains English-only because the complete marketing
landing is currently English-only. The following copy and its approved
`1440x1160` layouts are frozen authority for the existing full-landing
localization follow-up. RU/ES may not be independently redesigned when that
lane opens.

English:

- Daily: `See how FitChef helps you choose where to start`; `Ways to move`;
  `Endurance`; `Strength & Power`; `Team & Combat`;
  `Movement & Everyday Fitness`; `Goal`; `Reduce`; `Maintain`; `Gain`;
  `Where would you like to start?`;
  `FitChef shows both options. The choice is yours.`; `Today`;
  `Start with the plan for today.`; `This week`;
  `Look at the next seven days.`; `Confirm choice`; `Not now`; `Daily Plate`;
  `Weekly Planning`.
- Weekly: `A week that changes with you`; `Starting week`; `What changed`;
  `Your goal changes`; `A meal out`; `Use what’s at home`; `Updated week`.
- Food Context: `A food plan built around real life`; `Ingredients at home`;
  `Restaurant or chef`; `Shopping and stores`; `A food photo`;
  `One flexible plan`.
- VIP: `PulsePlate VIP`; `Your personal AI nutrition guide`;
  `Imagine PulsePlate VIP with FitChef connecting your measurements, goals and routines with everyday action: adapting menus as plans change and suggesting a practical next step when progress slows.`;
  `For everyday wellbeing, training, strength and muscle-building goals.`;
  `Support to keep you moving forward.`

Russian:

- Daily: `Как FitChef помогает выбрать, с чего начать`; `Варианты активности`;
  `Выносливость`; `Сила и мощность`; `Командные виды и единоборства`;
  `Движение и повседневная активность`; `Цель`; `Снижение веса`;
  `Поддержание веса`; `Набор веса`; `С чего хотите начать?`;
  `FitChef покажет оба варианта, а выбор останется за вами.`; `Сегодня`;
  `Сначала разобраться с планом на день.`; `Неделя`;
  `Сначала посмотреть на ближайшие семь дней.`; `Подтвердить выбор`;
  `Не сейчас`; `План питания на день`; `План на неделю`.
- Weekly: `Неделя, которая меняется вместе с вами`; `Начало недели`;
  `Что изменилось`; `Изменилась цель`; `Еда вне дома`;
  `Использовать продукты дома`; `Обновлённая неделя`.
- Food Context: `План питания для реальной жизни`; `Продукты дома`;
  `Ресторан или повар`; `Покупки и магазины`; `Фото блюда`;
  `Гибкий план питания`.
- VIP: `PulsePlate VIP`; `Ваш личный ИИ-помощник по питанию`;
  `Представьте PulsePlate VIP, где FitChef связывает ваши показатели, цели и привычки с повседневными действиями: адаптирует меню при изменении планов и предлагает разумный следующий шаг, если прогресс замедляется.`;
  `Для повседневного благополучия, тренировок, силы и набора мышечной массы.`;
  `Поддержка, чтобы продолжать двигаться вперёд.`

Spanish:

- Daily: `Cómo FitChef te ayuda a elegir por dónde empezar`; `Formas de moverte`;
  `Resistencia`; `Fuerza y potencia`; `Deportes de equipo y combate`;
  `Movimiento y actividad cotidiana`; `Objetivo`; `Reducir`; `Mantener`;
  `Aumentar`; `¿Por dónde quieres empezar?`;
  `FitChef te muestra ambas opciones. Tú eliges.`; `Hoy`;
  `Empezar por el plan de hoy.`; `Esta semana`;
  `Ver los próximos siete días.`; `Confirmar elección`; `Ahora no`;
  `Plan del día`; `Plan semanal`.
- Weekly: `Una semana que cambia contigo`; `Semana inicial`; `Qué cambió`;
  `Cambia tu objetivo`; `Una comida fuera`; `Usa lo que tienes en casa`;
  `Semana actualizada`.
- Food Context: `Un plan de alimentación para la vida real`;
  `Ingredientes en casa`; `Restaurante o chef`; `Compras y tiendas`;
  `Una foto de la comida`; `Un plan flexible`.
- VIP: `PulsePlate VIP`; `Tu guía personal de nutrición con IA`;
  `Imagina PulsePlate VIP con FitChef conectando tus indicadores, objetivos y rutinas con acciones cotidianas: adaptando los menús cuando cambien los planes y sugiriendo un próximo paso práctico cuando el progreso se ralentice.`;
  `Para el bienestar diario, el entrenamiento, la fuerza y los objetivos de ganancia muscular.`;
  `Apoyo para seguir avanzando.`

The public Web story remains a prepared, free acquisition/demo surface. It adds
no API call, live AI, auth, storage, analytics, navigation, payment, entitlement,
persistence, camera/upload, restaurant/store execution, or plan mutation.

## Candidate Intake 2026-04-28

The Figma board `FitChef Mascot Asset Inventory — Intake 2026-04-28`
(`1473:2`) tracks candidate/reference/rework assets only.

The approved seed pack listed in this document remains unchanged.
