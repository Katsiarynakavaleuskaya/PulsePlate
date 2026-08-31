# FitChef Mascot Asset Canon

Status: `Seed Pack v1 + Public Demo Pack v1`
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
| `activity-palette/endurance.webp` | `687a5a49c8fe321990f036cb6efdd1889bd08c5ff38983cf6eda94a3546bcda2` | `7e0b3d0aef31c1b4d2e3d23c43632b1f298d49b25d20db89e8d1958f9b522d96` | `1122x1402 RGB` | q96, 447238 B, PSNR 43.2483 dB, sRGB ICC |
| `activity-palette/movement-everyday-fitness.webp` | `d0b9be1359c0f56c6fd6dfffe849c4f6de2c699c8acfe8fb204f2a890e2ec1d5` | `24e316cc365ccd5da8235e0011cbc77e5f8ab0699c82c8a589c97e1e733736c8` | `1122x1402 RGB` | q95, 453154 B, PSNR 42.5998 dB, sRGB ICC |
| `activity-palette/strength-power.webp` | `0e04ea90a7d657c9c7ae03f793c2fb2da46ae418b682ed67e882401f0c08381c` | `e90019e23372c0ce6577468ebd5d0238a6e9f646e1eb21ba6cdca5deacdbcb08` | `1122x1402 RGB` | q96, 189792 B, PSNR 45.2864 dB, sRGB ICC |
| `activity-palette/team-combat.webp` | `389fba16715bd7b1e16650feb87ab7b274a6b5baebb57a18359e8dc0337440a7` | `13f50eb45192766b08fa5fefdd28f2347f9d8d45c324bb65501823566e4e760d` | `1122x1402 RGB` | q96, 366414 B, PSNR 44.5797 dB, sRGB ICC |
| `daily-plate-a-salmon-1024.webp` | `5bb635cdf4a86359d2763235dd31e7ef8f7d5b8c5776826823c5ff0a63806331` | `ae1410aeaabf59389ef244cab577ad9d7a82ef5ffc4338ac41f256a034be2149` | `1024x1024 RGB` | q96, 245002 B, PSNR 40.9164 dB, sRGB ICC |
| `food-context/food-context-ingredients-at-home.webp` | `69bdd1f50666964308e4a89494095dde5b86fd906b04c6824f02a9b7ebbe67b0` | `75bcaa6104a1c26a6560dfad7a8b5d9d78af618f3850cf289c94f80d9fb0cbd3` | `1122x1402 RGB` | q96, 273234 B, PSNR 44.5394 dB, sRGB ICC |
| `food-context/food-context-meal-photo.webp` | `12501b21584f9369574630268489b40430b643a97aa22d69fe61b4a16a7846ba` | `2e65391e5932aaf5ece8ea87293b0bd6967328022a4745a1c53c9ba549929b09` | `1122x1402 RGB` | q96, 337684 B, PSNR 44.4897 dB, sRGB ICC |
| `food-context/food-context-restaurant-chef.webp` | `ae932ce5aeb858cb86a9ed98694cd55292495f450ced6c60118c233da86adab4` | `b15b74a17dea9e4be67a930f3bac497ed601099c12f1efb148999ad396ddb158` | `1122x1402 RGB` | q96, 272400 B, PSNR 44.7366 dB, sRGB ICC |
| `food-context/food-context-shopping-stores.webp` | `2bd534f149fd0804986800ae939f3b7bdbf56ea52d2946f4a87c4a2d6ba113a5` | `bd241c8b0be6f1f76d3307d423e5cf3edfe8eb6b933a01ff1e764e112f585e4c` | `1122x1402 RGB` | q96, 423618 B, PSNR 42.1631 dB, sRGB ICC |
| `vip/fitchef-vip-editorial-owner-approved-logo-v2.webp` | `14223bd347c5b81f58a90da28fdf4a8243b90b9b0b156d8a6caa555144309d64` | `324d63729b745d17a0a7706a55bd74979a40a7db8820958a024e4ad73000d8f7` | `1122x1402 RGB` | q96, 368238 B, PSNR 44.5484 dB, sRGB ICC |
| `weekly-planning-a-meal-grid-1024.webp` | `d6cff5674fb8b74cbae348c88f6bf41682e0ea7a73c961d69cfadb76ec75a46a` | `678a55fd171bd40112377e160794019112dee3c1f8e6cb0d29c99f6058380d8a` | `1024x1024 RGB` | q96, 332828 B, PSNR 39.6382 dB, sRGB ICC |
| `weekly-planning-b-notebook-1024.webp` | `1943c4fd28fef04b697c243be450a3c0e74c2a8dd039b1828402394c14db0e40` | `8d8f4d53b3f55e323a346520313d5e98021aca94734117e855d1d9b4953fc73d` | `1024x1024 RGB` | q96, 376662 B, PSNR 39.1452 dB, sRGB ICC |

All twelve runtime files preserve the source dimensions and carry an explicit
sRGB ICC profile. They use reviewed WebP quality 95-96, stay below the
repository's 500 KiB added-file limit, and reduce the complete Web pack from
24875178 to 4086264 bytes. The original PNG bytes and their source hashes remain
the Open Design and future iOS authority. The existing
`fitchef-portrait-neutral-v1.png` remains the neutral H1 mascot and is not a
thirteenth public-demo derivative.

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
  `Look at the next seven days.`; `Confirm choice`; `Not now`; `Daily Plate`.
- Weekly: `A week that changes with you`; `Starting week`; `What changed`;
  `Your goal changes`; `A meal out`; `Use what’s at home`; `Updated week`.
- Food Context: `A food plan built around real life`; `Ingredients at home`;
  `Restaurant or chef`; `Shopping and stores`; `A food photo`;
  `One flexible plan`.
- VIP: `PulsePlate VIP`; `Your personal AI nutrition guide`;
  `FitChef brings your measurements, goals and routines into everyday action: reshaping menus when plans change and finding a practical next step when progress slows.`;
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
  `Не сейчас`; `План питания на день`.
- Weekly: `Неделя, которая меняется вместе с вами`; `Начало недели`;
  `Что изменилось`; `Изменилась цель`; `Еда вне дома`;
  `Использовать продукты дома`; `Обновлённая неделя`.
- Food Context: `План питания для реальной жизни`; `Продукты дома`;
  `Ресторан или повар`; `Покупки и магазины`; `Фото блюда`;
  `Гибкий план питания`.
- VIP: `PulsePlate VIP`; `Ваш личный ИИ-помощник по питанию`;
  `FitChef помогает связывать ваши показатели, цели и привычки с ежедневными действиями: перестраивать меню, когда планы меняются, и находить разумный следующий шаг, если прогресс замедлился.`;
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
  `Plan del día`.
- Weekly: `Una semana que cambia contigo`; `Semana inicial`; `Qué cambió`;
  `Cambia tu objetivo`; `Una comida fuera`; `Usa lo que tienes en casa`;
  `Semana actualizada`.
- Food Context: `Un plan de alimentación para la vida real`;
  `Ingredientes en casa`; `Restaurante o chef`; `Compras y tiendas`;
  `Una foto de la comida`; `Un plan flexible`.
- VIP: `PulsePlate VIP`; `Tu guía personal de nutrición con IA`;
  `FitChef reúne tus indicadores, objetivos y rutinas en acciones cotidianas: adapta los menús cuando cambian los planes y te ayuda a elegir un próximo paso sensato cuando el progreso se ralentiza.`;
  `Para el bienestar diario, el entrenamiento, la fuerza y los objetivos de ganancia muscular.`;
  `Apoyo para seguir avanzando.`

The public Web story remains a prepared, free acquisition/demo surface. It adds
no API call, live AI, auth, storage, analytics, navigation, payment, entitlement,
persistence, camera/upload, restaurant/store execution, or plan mutation.

## Candidate Intake 2026-04-28

The Figma board `FitChef Mascot Asset Inventory — Intake 2026-04-28`
(`1473:2`) tracks candidate/reference/rework assets only.

The approved seed pack listed in this document remains unchanged.
