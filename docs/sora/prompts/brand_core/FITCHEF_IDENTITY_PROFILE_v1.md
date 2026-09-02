# FitChef Identity Profile (v1.1)

Version: v1.1
Purpose: keep mascot continuity across generated images and animations
Source references: approved real-cat photos + current PulsePlate logo direction

## 1) Core Identity

- Species/look: friendly domestic tabby cat
- Must-have markers:
  - white chest
  - white paws ("socks")
  - warm amber/yellow eyes
  - pink nose with subtle darker outline
  - tabby stripe mask on forehead and cheeks
- Body language baseline: calm, curious, supportive

## 2) Style Modes

### `ui-flat` (product surfaces)

- Simplified geometry
- Strong silhouette at small sizes
- Low micro-detail
- Clean navy-first background

### `motion` (compact animated product states)

- Uses the same simplified identity as `ui-flat`
- Prefers small, purposeful movement over decorative looping
- Keeps frame-to-frame stripe, eye, chest, paw, collar, and medallion continuity
- Primarily serves iPhone product states unless a later platform review decides otherwise

### `marketing-hybrid` (campaign/social)

- Same morphology, richer texture depth
- Slightly more emotional expression
- Still restrained and premium-clean

### `editorial-real` (photographic product storytelling)

- Preserves the approved real-cat identity and natural feline anatomy
- Uses contextual, full-frame photography rather than a small UI-state icon
- Serves the public Web Hero and separately approved editorial placements
- May inform a future iPad composition only through its own reviewed carrier
- Does not enter the illustrated `FitChefMascot` variant enum

## 3) Platform Role Contract

- Public Web Hero: `editorial-real`
- Daily/Weekly compact interaction guide: `ui-flat`
- iPhone product states: primarily `ui-flat` or `motion`
- iPad photographic use: future design intent only, not current runtime authority
- VIP Personal Nutrition Guide: its existing approved photographic epoch remains unchanged
- All modes represent one FitChef identity and grant no different calculation,
  planning, AI, entitlement, or navigation capability

## 4) Non-Negotiables

- Preserve core facial proportions across all variants.
- Keep eye color inside the warm amber/yellow family.
- Retain white chest/paws identifiers in every output.
- Avoid clinical attire and medical symbolism.
- Keep mascot style serious and brand-consistent, not parody-like.

## 5) Forbidden Drift Patterns

- Neon/cyberpunk/purple-gold color drift
- Hyper-real gritty fur/noise for UI assets
- Humanized facial distortion (uncanny smile/teeth)
- Aggressive or fear-inducing expression
- Inconsistent stripe topology frame-to-frame in animation

## 6) Quick Likeness QA

- First-glance recognition should match the real prototype cat.
- Keep the silhouette compact and friendly in all variants.
- Ensure eye/nose/chest/paw markers remain intact.
- Fail if mascot can be mistaken for a different cat identity.
- Fail if style continuity breaks between image and animation packs.

## 7) Usage with Prompt Packs

- This profile is mandatory context for:
  - `FITCHEF_BRAND_CORE_PROMPT_PACK_v1.md`
- Add phrase in prompts when mascot appears:
  - `preserve FitChef identity profile v1.1`
  - `(tabby mask, white chest/paws, amber eyes, compact silhouette)`
